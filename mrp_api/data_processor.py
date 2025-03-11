from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta, datetime
import pandas as pd
from django.db.models import Sum, Max, Subquery, OuterRef, F
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor
from mrp_api.models import Area, Sales, PosItems, BomMasterlist, SalesReport, InitialReplenishment, EndingInventory, InventoryCode, BosItems, Forecast, ByRequestItems, Status, SalesReportExcel
import numpy as np
import os

scheduler = BackgroundScheduler()

# Constants
NO_OF_DAYS = 21
SEASONALITY_INDEX = 1.1
DAYS_BEFORE_DEL = 5


bos_items_data = list(
    BosItems.objects.values(
        "id",  # MASTERLIST_ID
        "delivery_uom",
        "bundling_size",
        "conversion_delivery_uom"
    )
)

bos_items_df = pd.DataFrame(bos_items_data)
bos_items_df.rename(columns={'id': 'bos_code_id'},inplace=True)
processed_status = Status.objects.get(id=2)

def process_item(item, sales_data, area):
    result = []
    sales = []

    item_sales = sales_data.get(item.id, {"DINE IN": 0, "TAKE OUT": 0})
    dine_in_quantity = item_sales["DINE IN"]
    take_out_quantity = item_sales["TAKE OUT"]

    average_dine_in_sold = (dine_in_quantity / NO_OF_DAYS) * SEASONALITY_INDEX
    average_take_out_sold = (take_out_quantity / NO_OF_DAYS) * SEASONALITY_INDEX

    bom_entries = BomMasterlist.objects.filter(pos_code=item)

    sales.append({
        "pos_item": item.pos_item,
        "AREA": area.location,
        "dine_in_quantity": dine_in_quantity,
        "take_out_quantity": take_out_quantity,
        "average_dine_in_sold": average_dine_in_sold,
        "average_take_out_sold": average_take_out_sold
    })


    for bom_entry in bom_entries:
        category = bom_entry.category.upper()
        average_daily_usage = (
            float(average_take_out_sold * bom_entry.bom) if "TAKE" in category else float(average_dine_in_sold * bom_entry.bom)
        )
        weekly_usage = float(8 * average_daily_usage)
        safety_stock = float(weekly_usage * 0.2)
        forecast_weekly_computation = weekly_usage + safety_stock

        result.append({
            "MASTERLIST_ID": bom_entry.bos_code.id,
            "MENU_DESCRIPTION": item.menu_description,
            "POS_CODE": item.pos_item,
            "BOS_CODE": bom_entry.bos_code.bos_code,
            "CATEGORY": category,
            "QTY_SOLD": take_out_quantity if ("TAKEOUT" in category or "TAKE OUT" in category) else dine_in_quantity,
            "AVERAGE_DAILY_SALES": round(average_take_out_sold, 4) if ("TAKEOUT" in category or "TAKE OUT" in category) else round(average_dine_in_sold, 4),
            "BOS_MATERIAL_DESCRIPTION": bom_entry.bos_code.bos_material_description,
            "AVERAGE_DAILY_USAGE": round(average_daily_usage, 4),
            "WEEKLY_USAGE": round(weekly_usage, 4),
            "SAFETY_STOCK": round(safety_stock, 4),
            "FORECAST_WEEKLY_CONSUMPTION": round(forecast_weekly_computation, 4)
        })

    return result, sales


def calculate_area_sales(area):
    start_date = datetime(2025, 1, 25).date()
    end_date = datetime(2025, 2, 9).date()

#     end_date = datetime.today().date()
#     # Get the start of the current week (assuming the week starts on Monday)
#     start_of_this_week = end_date - timedelta(days=end_date.weekday() + 1)  # Adjust so the week starts on Sunday
#
# # Subtract 3 weeks from the start of the current week
#     start_date = start_of_this_week - timedelta(weeks=3)
#
#     print(f"Start date: {start_date}")
#     print(f"End date: {start_of_this_week}")

    pos_items = PosItems.objects.all()
    sales_data = Sales.objects.filter(
        outlet=area, sales_date__range=(start_date, end_date)
    ).values("sku_code_id", "transaction_type").annotate(total_quantity=Sum("quantity"))

    sales_dict = {}
    for sale in sales_data:
        sku_id = sale["sku_code_id"]
        transaction_type = sale["transaction_type"].upper()
        if sku_id not in sales_dict:
            sales_dict[sku_id] = {"DINE IN": 0, "TAKE OUT": 0}
        sales_dict[sku_id][transaction_type] = sale["total_quantity"] or 0
    #pos_items = PosItems.objects.filter(id__in=sales_dict.keys())
    forecast_result, sales_result = [], []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_item, item, sales_dict, area) for item in pos_items]
        seen_sales = set()
        for future in futures:
            forecast_data, sales_data = future.result()
            forecast_result.extend(forecast_data)
            for data in sales_data:
                sales_key = (data["pos_item"], data["AREA"])
                if sales_key not in seen_sales:
                    sales_result.append(data)
                    seen_sales.add(sales_key)

    forecast_df = pd.DataFrame(forecast_result).sort_values(by='MASTERLIST_ID', ascending=True)
    sales_df = pd.DataFrame(sales_result)




    latest_inventory_code = InventoryCode.objects.filter(area=area, status__status=1).order_by('-created_at').first()

    if latest_inventory_code:

        sales_entries = [
        SalesReport(
            inventory_code=latest_inventory_code,
            sales_report_name=f"{area.location} - {data['pos_item']}",
            pos_item=PosItems.objects.get(pos_item=data["pos_item"]),  # Ensure valid foreign key
            dine_in_quantity=data["dine_in_quantity"],
            sales_period = f'{start_date} to {end_date}',
            take_out_quantity=data["take_out_quantity"],
            average_dine_in_sold=round(data["average_dine_in_sold"],4),
            average_tako_out_sold=round(data["average_take_out_sold"],4),
            area=area
        )
            for data in sales_result  # Removed the condition
        ]

        with transaction.atomic():
            SalesReport.objects.bulk_create(sales_entries)
            print(f"Saved {area} into the Sales Report")



        initial_replenishment_entries = []

        for _, row in forecast_df.iterrows():
            try:

                sales_report = SalesReport.objects.filter(pos_item__pos_item=row['POS_CODE'], area=area).first()

                bom_entry = BomMasterlist.objects.filter(bos_code_id=row['BOS_CODE'], pos_code_id=row['POS_CODE']).first()

                if sales_report and bom_entry:
                    initial_replenishment_entries.append(
                        InitialReplenishment(
                            sales_report=sales_report,
                            bom_entry=bom_entry,
                            inventory_code=latest_inventory_code,
                            daily_sales=row['AVERAGE_DAILY_SALES'],
                            average_daily_usage=row['AVERAGE_DAILY_USAGE'],
                            weekly_usage=row['WEEKLY_USAGE'],
                            safety_stock=row['SAFETY_STOCK'],
                            forecast_weekly_consumption=row['FORECAST_WEEKLY_CONSUMPTION']
                        )
                    )
            except Exception as e:
                print(f"Error processing BOS_CODE {row['BOS_CODE']}: {e}")


        if initial_replenishment_entries:
            with transaction.atomic():
                InitialReplenishment.objects.bulk_create(initial_replenishment_entries)
        print(f"saved {area} into InitialReplenishment")
        print(f"Saved {len(initial_replenishment_entries)} records to InitialReplenishment.")




        latest_inventory = list(EndingInventory.objects.filter(inventory_code=latest_inventory_code).values(
            'id','bom_entry_id', 'actual_ending', 'upcoming_delivery'
        ))

        if latest_inventory:
            inventory_df = pd.DataFrame(latest_inventory)


            forecast_summary = forecast_df.groupby('BOS_CODE').agg({
                'MASTERLIST_ID': 'first',
                'AVERAGE_DAILY_USAGE': lambda x: round(x.sum() + 0.5),
                'FORECAST_WEEKLY_CONSUMPTION': lambda x: round(x.sum() + 0.5)
            }).reset_index()


            forecast_summary.rename(columns={
                'AVERAGE_DAILY_USAGE': 'TOTAL_AVERAGE_DAILY_USAGE',
                'FORECAST_WEEKLY_CONSUMPTION': 'TOTAL_FORECAST_WEEKLY_CONSUMPTION',
                'actual_ending': 'TOTAL_ACTUAL_ENDING',
                'upcoming_delivery': 'TOTAL_UPCOMING_DELIVERY'
            }, inplace=True)
            forecast_summary = forecast_summary.merge(inventory_df, left_on='MASTERLIST_ID', right_on='bom_entry_id', how='left')
            forecast_summary = forecast_summary.merge(bos_items_df, left_on='MASTERLIST_ID', right_on='bos_code_id', how='left')
            forecast_summary['DAYS_TO_LAST'] = np.where(forecast_summary['TOTAL_AVERAGE_DAILY_USAGE'] > 0,np.ceil(forecast_summary['actual_ending'] / forecast_summary['TOTAL_AVERAGE_DAILY_USAGE'] * 100) / 100,0)


            forecast_summary['FORECASTED_ENDING_INVENTORY'] = ((forecast_summary['actual_ending'].fillna(0) + forecast_summary['upcoming_delivery'].fillna(0)) - (forecast_summary['TOTAL_AVERAGE_DAILY_USAGE'].fillna(0) * DAYS_BEFORE_DEL)).clip(lower=0)
            forecast_summary['forecast'] = (forecast_summary['TOTAL_FORECAST_WEEKLY_CONSUMPTION'].fillna(0) - forecast_summary['FORECASTED_ENDING_INVENTORY']).clip(lower=0)

            forecast_summary['converted_ending_inventory'] = (
                np.ceil(forecast_summary['forecast'].fillna(0) / forecast_summary['conversion_delivery_uom'].replace(0, np.nan))
            ).replace([np.nan, np.inf, -np.inf], 0).astype(int)

            bos_items = {obj.id: obj for obj in BosItems.objects.all()}
            forecast_objects = []
            for _, row in forecast_summary.iterrows():

                bom_entry = bos_items.get(int(row["MASTERLIST_ID"])) if not pd.isna(row["MASTERLIST_ID"]) else None

                if bom_entry:
                    forecast_objects.append(
                        Forecast(
                            inventory_code=latest_inventory_code,  # Assign latest inventory_code
                            bom_entry=bom_entry,
                            average_daily_usage=row.get("TOTAL_AVERAGE_DAILY_USAGE", 0),
                            days_to_last=row.get("DAYS_TO_LAST", 0),
                            forecast_weekly_consumption=row.get("TOTAL_FORECAST_WEEKLY_CONSUMPTION", 0),
                             forecasted_ending_inventory=row.get("FORECASTED_ENDING_INVENTORY", 0),
                            forecast=row.get("forecast", 0),
                            converted_ending_inventory=row.get("converted_ending_inventory", 0)
                        )
                    )


            if forecast_objects:
                with transaction.atomic():
                    Forecast.objects.bulk_create(forecast_objects, batch_size=1000)
                print(f"✅ {len(forecast_objects)} Forecast records inserted successfully!")
            else:
                print("⚠️ No valid forecast records to insert.")

        else:
            print(f"No ending inventory data found for area: {area.location}")

        latest_inventory_code.status_id = processed_status.id
        latest_inventory_code.save()

    else:
        print(f"No inventory code found for area: {area.location}")


    inventory_code_name = latest_inventory_code.inventory_code
    reports_folder = "media/sales"

    os.makedirs(reports_folder, exist_ok=True)

    file_name = f"{inventory_code_name}_sales_report.xlsx"
    save_filename = SalesReportExcel(inventory_code=latest_inventory_code,report_file=file_name)
    save_filename.save()
    file_path = os.path.join(reports_folder, file_name)
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        forecast_df.to_excel(writer, index=False, sheet_name="Initial Replenishment")
        forecast_summary.to_excel(writer, index=False, sheet_name="Forecast Summary")
        sales_df.to_excel(writer, index=False, sheet_name="Sales Data")

    print(f"Sales report generated: {file_name}")


def calculate_average_sales():
    print("Starting to process report")
    areas = Area.objects.filter(location="CHOOKS FARMERS PLAZA")
    #areas = Area.objects.all()
    with ThreadPoolExecutor() as executor:
        executor.map(calculate_area_sales, areas)

    print("Done generating reports.")

for job in scheduler.get_jobs():
    scheduler.remove_job(job.id)

scheduler.add_job(calculate_average_sales, 'interval', minutes=1)
#scheduler.add_job(calculate_average_sales, 'cron', day_of_week='wed', hour=5, minute=0)
scheduler.start()
