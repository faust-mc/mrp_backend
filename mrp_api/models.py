from email.policy import default
from random import choices
from django.utils.timezone import now
from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Area(models.Model):
	location = models.CharField(max_length=250)
	province = models.CharField(max_length=50)
	branch_code = models.CharField(max_length=50, blank=True, null=True)
	

	def __str__(self):
		return self.location


class Branches(models.Model):
	area = models.ForeignKey(Area, on_delete=models.CASCADE)
	municipality = models.CharField(max_length=50)
	barangay = models.CharField(max_length=50)
	street = models.CharField(max_length=50)

	def __str__(self):
		return self.branch_code


class Departments(models.Model):
	department = models.CharField(max_length=100)

	def __str__(self):
		return self.department




class Modules(models.Model):
    # Choices for module icons
    MODULE_LOGO_CHOICES = [
        ("#home", "Home"),
        ("#speedometer2", "Speedometer"),
        ("#table", "Table"),
        ("#grid", "Grid"),
    ]

    module = models.CharField(max_length=100)
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=MODULE_LOGO_CHOICES,
        default="#table"
    )
    slug = models.CharField(max_length=20, blank=True, null=True)
    path = models.CharField(max_length=20, blank=True, null=True)
    components = models.CharField(max_length=20, blank=True, null=True)

    # Self-referential ForeignKey for parent-child relationship
    parent_module = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submodules'
    )

    def __str__(self):
        return self.module

class ModulePermissions(models.Model):
	name = models.CharField(max_length=50)
	codename = models.CharField(max_length=80)
	module = models.ForeignKey(Modules, on_delete=models.CASCADE, blank=True, null=True)

	def __str__(self):
		return self.name



class Roles(models.Model):
	role = models.CharField(max_length=20)
	permissions = models.ManyToManyField(ModulePermissions, blank=True)
	area = models.ManyToManyField(Area, blank=True)
	modules = models.ManyToManyField(Modules, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		 return self.role


class Employee(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	department = models.ForeignKey(Departments, on_delete=models.CASCADE, blank=True, null=True)
	date_join = models.DateTimeField(null=True, blank=True)
	role = models.ForeignKey(Roles,  on_delete = models.CASCADE,blank=True, null=True)
	modules = models.ManyToManyField(Modules)
	module_permissions = models.ManyToManyField(ModulePermissions, blank=True)
	area = models.ManyToManyField(Area, blank=True)
	locked = models.IntegerField(default=0)
	attempts = models.IntegerField(default=0)
	cellphone_number = models.CharField(max_length=20, blank=True, null=True)
	telephone_number = models.CharField(max_length=20, blank=True, null=True)
	superior = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
	added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees_added')
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		return self.user.username


class AccessKey(models.Model):
	access_key = models.CharField(max_length=15)
	access_name = models.CharField(max_length=30)
	access_description = models.TextField(max_length=100)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def __str__(self):
		return self.access_key



class UploadedFile(models.Model):
    file_hash = models.CharField(max_length=64, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)



class PosItems(models.Model):
	menu_description = models.CharField(max_length=12)
	pos_item = models.CharField(max_length=30, unique=True)


class Status(models.Model):
	status = models.IntegerField(default=0, null=True, blank=True)
	status_description = models.TextField(max_length=50, null=True, blank=True)



class BosItems(models.Model):
	bos_code = models.CharField(max_length=20,null=True, blank=True, unique=True)
	bos_material_description = models.TextField(max_length=150,null=True, blank=True)
	bos_uom = models.CharField(max_length=10,null=True, blank=True)
	category = models.CharField(max_length=8, null=True,blank=True)
	delivery_uom = models.CharField(max_length=10,null=True, blank=True)
	bundling_size = models.FloatField(null=True, blank=True)
	conversion_delivery_uom = models.FloatField(null=True, blank=True)



class BomMasterlist(models.Model):
	pos_code = models.ForeignKey(PosItems, to_field='pos_item',on_delete=models.CASCADE,null=True, blank=True)
	bos_code = models.ForeignKey(BosItems, to_field='bos_code',on_delete=models.CASCADE,null=True, blank=True)
	bom = models.FloatField(null=True, blank=True)
	uom = models.CharField(max_length=10,null=True, blank=True)
	category = models.CharField(max_length = 20,null=True, blank=True)
	item_description = models.TextField(max_length=150,null=True, blank=True)


class ByRequestItems(models.Model):
	bos_code = models.CharField(max_length=20,null=True, blank=True, unique=True)
	bos_material_description = models.TextField(max_length=150,null=True, blank=True)
	bos_uom = models.CharField(max_length=10,null=True, blank=True)
	category = models.CharField(max_length=8, null=True,blank=True)
	delivery_uom = models.CharField(max_length=10,null=True, blank=True)
	conversion = models.FloatField(null=True, blank=True)




class Sales(models.Model):
	ifs_code = models.CharField(max_length=10,null=True, blank=True)
	outlet = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
	or_number = models.CharField(max_length=12,null=True, blank=True)
	customer_name = models.CharField(max_length=50, blank=True, null=True)
	sku_code = models.ForeignKey(PosItems, on_delete=models.CASCADE,null=True, blank=True)
	quantity = models.IntegerField(null=True, blank=True)
	unit_price = models.FloatField(null=True, blank=True)
	gross_sales = models.FloatField(null=True, blank=True)
	type_of_discount = models.CharField(max_length=20, null	=True, blank=True)
	discount_amount = models.FloatField(null=True, blank=True)
	vat_deduct = models.FloatField(null=True, blank=True)
	net_sales = models.FloatField(null=True, blank=True)
	mode_of_payment = models.CharField(max_length=10,  null=True, blank=True)
	transaction_type = models.CharField(max_length=15)
	note = models.TextField(max_length=150, null=True, blank=True)
	remarks = models.TextField(max_length=150, null=True, blank=True)
	sales_date = models.DateField(null=True, blank=True)
	time = models.TimeField(null=True, blank=True)
	uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)




class SalesReport(models.Model):
	sales_report_name = models.CharField(max_length=50, null=True, blank=True)
	pos_item = models.ForeignKey(PosItems, on_delete=models.CASCADE,null=True, blank=True)
	sales_period = models.CharField(max_length=150, null=True, blank=True)
	dine_in_quantity = models.FloatField(null=True, blank=True)
	take_out_quantity = models.FloatField(null=True, blank=True)
	average_dine_in_sold = models.FloatField(null=True, blank=True)
	average_tako_out_sold = models.FloatField(null=True, blank=True)
	area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)


class InitialReplenishment(models.Model):
	sales_report = models.ForeignKey(SalesReport, on_delete=models.CASCADE, related_name="forecasts")
	bom_entry = models.ForeignKey(BomMasterlist, on_delete=models.CASCADE, related_name="bom_forecasts")
	daily_sales = models.FloatField(default=0)
	average_daily_usage = models.FloatField(default=0)
	weekly_usage = models.FloatField(default=0)
	safety_stock = models.FloatField(default=0)
	forecast_weekly_consumption = models.FloatField(default=0)



class InventoryCode(models.Model):
	area = models.ForeignKey(Area, on_delete=models.CASCADE, null=True, blank=True)
	status = models.ForeignKey(Status, on_delete=models.CASCADE, default=1,null=True, blank=True)
	inventory_code = models.CharField(max_length=100, null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

	def save(self, *args, **kwargs):
		if not self.inventory_code and self.area:
			date_str = now().strftime("%Y%m%d")
			self.inventory_code = f"{self.area.location.replace(' ', '_')}_{date_str}"
		super().save(*args, **kwargs)


class EndingInventory(models.Model):
	inventory_code = models.ForeignKey(InventoryCode, on_delete=models.CASCADE, null=True, blank=True)
	bom_entry = models.ForeignKey(BosItems, on_delete=models.CASCADE, related_name="bom_ending_inventory")
	actual_ending = models.FloatField(default=0)
	upcoming_delivery = models.FloatField(default=0, null=True, blank=True)



class Forecast(models.Model):
	inventory_code = models.ForeignKey(InventoryCode, on_delete=models.CASCADE, null=True, blank=True)
	bom_entry = models.ForeignKey(BosItems, on_delete=models.CASCADE, related_name="bom_ending_forecast")
	average_daily_usage = models.FloatField(default=0, null=True, blank=True)
	days_to_last = models.FloatField(default=0, null=True, blank=True)
	forecast_weekly_consumption = models.FloatField(default=0, null=True, blank=True)
	forecasted_ending_inventory = models.FloatField(default=0, null=True, blank=True)
	converted_ending_inventory = models.FloatField(default=0, null=True, blank=True)
	forecast = models.FloatField(default=0, null=True, blank=True)




class DeliveryCode(models.Model):
	inventory_code = models.ForeignKey(InventoryCode, on_delete=models.CASCADE, null=True, blank=True)
	status = models.ForeignKey(Status, on_delete=models.CASCADE, default=1,null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
	requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_by')
	approved_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_by')


class DeliveryItems(models.Model):
	delivery_code = models.ForeignKey(DeliveryCode, on_delete=models.CASCADE, null=True, blank=True)
	bom_entry = models.ForeignKey(BosItems, on_delete=models.CASCADE, related_name="bom_item_delivery")
	first_adjustment = models.FloatField(default=0, null=True, blank=True)
	second_adjustment = models.FloatField(default=0, null=True, blank=True)
	third_adjustment = models.FloatField(default=0, null=True, blank=True)
	first_final_delivery = models.FloatField(default=0, null=True, blank=True)
	second_final_delivery = models.FloatField(default=0, null=True, blank=True)
	third_final_delivery = models.FloatField(default=0, null=True, blank=True)
	first_qty_delivery = models.FloatField(default=0, null=True, blank=True)
	second_qty_delivery = models.FloatField(default=0, null=True, blank=True)
	third_qty_delivery = models.FloatField(default=0, null=True, blank=True)



class ByRequest(models.Model):
	delivery_code = models.ForeignKey(DeliveryCode, on_delete=models.CASCADE, null=True, blank=True)
	by_request_item = models.ForeignKey(ByRequestItems, on_delete=models.CASCADE, null=True, blank=True)
	total_weekly_request = models.FloatField(default=0, null=True, blank=True)
	first_delivery = models.FloatField(default=0, null=True, blank=True)
	second_delivery = models.FloatField(default=0, null=True, blank=True)
	third_delivery = models.FloatField(default=0, null=True, blank=True)
	first_final_delivery = models.FloatField(default=0, null=True, blank=True)
	second_final_delivery = models.FloatField(default=0, null=True, blank=True)
	third_final_delivery = models.FloatField(default=0, null=True, blank=True)
	first_qty_delivery = models.FloatField(default=0, null=True, blank=True)
	second_qty_delivery = models.FloatField(default=0, null=True, blank=True)
	third_qty_delivery = models.FloatField(default=0, null=True, blank=True)





