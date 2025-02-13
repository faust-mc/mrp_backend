from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta, datetime
import pandas as pd
from django.db.models import Sum, Max, Subquery, OuterRef, F
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor
from mrp_api.models import Area, Sales, PosItems, BomMasterlist, SalesReport, InitialReplenishment, EndingInventory, InventoryCode

scheduler = BackgroundScheduler()

# Constants
NO_OF_DAYS = 21
SEASONALITY_INDEX = 1.1
DAYS_BEFORE_DEL = 5

def process_item(item, sales_data, area):
    result = []
    sales = []


    item_sales = sales_data.get(item.id, {"DINE IN": 0, "TAKE OUT": 0})
    dine_in_quantity = item_sales["DINE IN"]
    take_out_quantity = item_sales["TAKE OUT"]

    average_dine_in_sold = (dine_in_quantity / NO_OF_DAYS) * SEASONALITY_INDEX
    average_take_out_sold = (take_out_quantity / NO_OF_DAYS) * SEASONALITY_INDEX

    bom_entries = BomMasterlist.objects.filter(pos_code=item)


    # ✅ Move sales.append outside the loop
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
    start_date = datetime(2025, 1, 5).date()
    end_date = datetime(2025, 1, 25).date()

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

    # Step 1: Get the latest inventory code per area
    latest_inventory_code = InventoryCode.objects.filter(area=area).order_by('-created_at').first()

    if latest_inventory_code:
        latest_inventory = list(EndingInventory.objects.filter(inventory_code=latest_inventory_code).values(
            'bom_entry_id', 'actual_ending', 'upcoming_delivery'
        ))

        if latest_inventory:
            inventory_df = pd.DataFrame(latest_inventory)


            forecast_summary = forecast_df.groupby('BOS_CODE').agg({
                'MASTERLIST_ID': 'first',
                'AVERAGE_DAILY_USAGE': lambda x: round(x.sum() + 0.5),
                'FORECAST_WEEKLY_CONSUMPTION': lambda x: round(x.sum() + 0.5)
            }).reset_index()
            print(forecast_summary)
            print()
            print(inventory_df)
            print("-----1")

            forecast_summary.rename(columns={
                'AVERAGE_DAILY_USAGE': 'TOTAL_AVERAGE_DAILY_USAGE',
                'FORECAST_WEEKLY_CONSUMPTION': 'TOTAL_FORECAST_WEEKLY_CONSUMPTION',
                'actual_ending': 'TOTAL_ACTUAL_ENDING',
                'upcoming_delivery': 'TOTAL_UPCOMING_DELIVERY'
            }, inplace=True)
            forecast_summary = forecast_summary.merge(inventory_df, left_on='MASTERLIST_ID', right_on='bom_entry_id', how='left')
            forecast_summary['DAYS_TO_LAST'] = round(forecast_summary['actual_ending'] / forecast_summary['TOTAL_AVERAGE_DAILY_USAGE'].fillna(0), 2)
            forecast_summary['FORECASTED_ENDING_INVENTORY'] = (
                    (forecast_summary['actual_ending'] + forecast_summary['upcoming_delivery']) -
                    (forecast_summary['TOTAL_AVERAGE_DAILY_USAGE'] * DAYS_BEFORE_DEL))
            forecast_summary['FORECASTED_ENDING_INVENTORY'] = forecast_summary['FORECASTED_ENDING_INVENTORY'].apply(lambda x: x if x > 0 else 0)


        else:
            print(f"No ending inventory data found for area: {area.location}")
    else:
        print(f"No inventory code found for area: {area.location}")

    # Save to Excel
    file_name = f"{area.location}_sales_report.xlsx"
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        forecast_df.to_excel(writer, index=False, sheet_name="Initial Replenishment")
        forecast_summary.to_excel(writer, index=False, sheet_name="Forecast Summary")
        sales_df.to_excel(writer, index=False, sheet_name="Sales Data")

    print(f"Sales report generated: {file_name}")


def calculate_average_sales():
    areas = Area.objects.filter(location="CHOOKS EXP SM HYPERMARKET IMUS")
    #areas = Area.objects.all()
    with ThreadPoolExecutor() as executor:
        executor.map(calculate_area_sales, areas)

# Remove existing jobs before scheduling a new one
for job in scheduler.get_jobs():
    scheduler.remove_job(job.id)

scheduler.add_job(calculate_average_sales, 'interval', minutes=0.5)
print(scheduler.get_jobs())
scheduler.start()
