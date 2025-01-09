
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
    department_id = serializers.PrimaryKeyRelatedField(source='department', read_only=True)
    role = serializers.StringRelatedField(many=True)
    superior = serializers.SerializerMethodField()
    access = serializers.SerializerMethodField()  # Combined access (modules and submodules)
    access_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'department', 'department_id', 'date_join', 'role',
            'locked', 'attempts', 'superior', 'cellphone_number', 'telephone_number', 'access',
            'access_permissions',
        ]

    def get_superior(self, obj):
        if obj.superior:
            return {
                "id": obj.superior.id,
                "username": obj.superior.user.username,
                "email": obj.superior.user.email,
                "full_name": f"{obj.superior.user.first_name} {obj.superior.user.last_name}",
            }
        return None

    def get_access_permissions(self, obj):
        # Get permissions directly assigned to the employee
        employee_permissions = obj.access_permissions.all()

        # Get permissions assigned through roles
        role_permissions = ModulePermissions.objects.filter(roles__in=obj.role.all())

        # Combine both sets of permissions and remove duplicates
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

    def get_access(self, obj):
        """
        Combine modules assigned directly to the employee and through roles,
        including only the submodules explicitly assigned to the user or their roles.
        """
        # Directly assigned modules
        employee_modules = obj.access.all()

        # Modules assigned through roles
        role_modules = Modules.objects.filter(roles__in=obj.role.all())

        # Combine both sets of modules and remove duplicates
        combined_modules = (employee_modules | role_modules).distinct()

        # Serialize modules with their associated submodules
        result = []
        for module in combined_modules:
            # Submodules directly assigned to the user or through roles
            employee_submodules = obj.access_submodules.filter(module=module)
            role_submodules = Submodules.objects.filter(
                module=module, roles__in=obj.role.all()
            )

            # Combine both sets of submodules and remove duplicates
            combined_submodules = (employee_submodules | role_submodules).distinct()

            # Add module with filtered submodules to the result
            result.append({
                "id": module.id,
                "module": module.module,
                "icon": module.icon,
                "slug": module.slug,
                "path": module.path,
                "components": module.components,
                "submodules": [
                    {
                        "id": submodule.id,
                        "submodule": submodule.submodule,
                        "slug": submodule.slug,
                        "components": submodule.components,
                    }
                    for submodule in combined_submodules
                ],
            })

        return result



  