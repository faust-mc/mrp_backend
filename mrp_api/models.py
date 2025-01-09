from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Area(models.Model):
	location = models.CharField(max_length=250)
	province = models.CharField(max_length=50)
	municipality = models.CharField(max_length=50)

	def __str__(self):
		return self.municipality

class Departments(models.Model):
	department = models.CharField(max_length=100)

	def __str__(self):
		return self.department


class ModulePermissions(models.Model):
	name = models.CharField(max_length=50)
	codename = models.CharField(max_length=80)
	content_type_id = models.IntegerField()

	def __str__(self):
		return self.name


class Modules(models.Model):
	module = models.CharField(max_length=100)
	icon = models.CharField(max_length = 100, blank= True, null = True)
	slug = models.CharField(max_length = 20, blank=True, null=True)
	path = models.CharField(max_length=20, blank=True, null=True)
	components = models.CharField(max_length = 20, blank=True, null=True)

	def __str__(self):
		return self.module


class Submodules(models.Model):
	module = models.ForeignKey(Modules, on_delete=models.CASCADE)
	submodule = models.CharField(max_length = 100)
	slug = models.CharField(max_length = 20, blank=True, null=True)
	components = models.CharField(max_length = 20, blank=True, null=True)


	def __str__(self):
		return f'{self.submodule}-{self.module}'



class Roles(models.Model):
    role = models.CharField(max_length=20)
    permissions = models.ManyToManyField(ModulePermissions, blank=True)
    modules = models.ManyToManyField(Modules, blank=True)
    submodules = models.ManyToManyField(Submodules, blank=True)

    def __str__(self):
        return self.role


class Employee(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)

	department = models.ForeignKey(Departments, on_delete=models.CASCADE, blank=True, null=True)
	date_join = models.DateTimeField(null=True, blank=True)
	role = models.ManyToManyField(Roles)
	modules = models.ManyToManyField(Modules)
	module_permissions = models.ManyToManyField(ModulePermissions, null=True, blank=True)
	area = models.ManyToManyField(Area, null=True, blank=True)
	submodules = models.ManyToManyField(Submodules,blank=True, null=True)
	locked = models.IntegerField(default=0)
	attempts = models.IntegerField(default=0)
	cellphone_number = models.CharField(max_length=20, blank=True, null=True)
	telephone_number = models.CharField(max_length=20, blank=True, null=True)
	superior = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')


	def __str__(self):
		return self.user.username