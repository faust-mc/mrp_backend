from django.contrib import admin
from .models import Area, Departments, Modules, Roles, Employee,ModulePermissions, AccessKey


admin.site.register([Area, Departments, Modules, Roles, Employee, ModulePermissions,AccessKey])

