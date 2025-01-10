
from rest_framework import serializers
from .models import Area, Departments, ModulePermissions, Modules, Submodules,Roles, Employee
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class SubmoduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submodules
        fields = ['id', 'submodule', 'slug', 'components']


class DepartmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = '__all__'


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
   
    submodules = serializers.SerializerMethodField()

    class Meta:
        model = Modules
        fields = ['id', 'module', 'slug', 'icon', 'path', 'components', 'submodules']

    def get_submodules(self, obj):
        employee = self.context.get('employee')  # Get the Employee object from the context
        if employee:
            # Get the submodules that are linked to this employee's access_submodules for this module
            submodules = employee.access_submodules.filter(module=obj)
            return SubmoduleSerializer(submodules, many=True).data
        return []

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['id', 'role'] 

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'last_login']

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    department = serializers.StringRelatedField(allow_null=True)
    department_id = serializers.PrimaryKeyRelatedField(
        source='department', queryset=Departments.objects.all(), allow_null=True
    )
    role = RoleSerializer(many=True)  # Use RoleSerializer for better structure
    superior = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()  # Combined access (modules and submodules)
    module_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'department', 'department_id', 'date_join', 'role',
            'locked', 'attempts', 'superior', 'cellphone_number', 'telephone_number',
            'modules', 'module_permissions',
        ]

    def get_superior(self, obj):
        """Fetch superior details using a nested serializer instead of a manual dictionary."""
        if obj.superior:
            return UserSerializer(obj.superior.user).data
        return None

    def get_module_permissions(self, obj):
        """Fetch combined permissions from employee and roles."""
        employee_permissions = obj.module_permissions.all()
        role_permissions = ModulePermissions.objects.filter(roles__in=obj.role.all())
        combined_permissions = (employee_permissions | role_permissions).distinct()

        return [
            {
                "id": perm.id,
                "name": perm.name,
                "codename": perm.codename,
                "content_type_id": perm.content_type_id,
            }
            for perm in combined_permissions
        ]

    def get_modules(self, obj):
        """Combine modules from both employee and roles, including associated submodules."""
        employee_modules = obj.modules.all()
        role_modules = Modules.objects.filter(roles__in=obj.role.all())
        combined_modules = (employee_modules | role_modules).distinct()

        result = []
        for module in combined_modules:
            employee_submodules = obj.submodules.filter(module=module)
            role_submodules = Submodules.objects.filter(
                module=module, roles__in=obj.role.all()
            )
            combined_submodules = (employee_submodules | role_submodules).distinct()

            result.append({
                "id": module.id,
                "module": module.module,
                "icon": module.icon,
                "slug": module.slug,
                "path": module.path,
                "components": module.components,
                "submodules": SubmoduleSerializer(combined_submodules, many=True).data,
            })

        return result




  