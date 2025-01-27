
from rest_framework import serializers
from .models import Area, ModulePermissions, Modules, Submodules,Roles, Employee, Departments, AccessKey
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import password_validation
from rest_framework import serializers


class SubmoduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submodules
        fields = ['id', 'submodule', 'slug', 'components']


class AccessKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessKey
        fields = '__all__'


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
    area = AreaSerializer(many=True)  # Directly serialize the related Area model
    role = RoleSerializer(many=True)  # Use RoleSerializer for better structure
    superior = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()  # Combined access (modules and submodules)
    module_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'department', 'department_id', 'date_join', 'role',
            'locked', 'attempts', 'superior', 'cellphone_number', 'telephone_number',
            'modules', 'module_permissions', 'area',  # Include 'area' in the fields
        ]

    def get_superior(self, obj):

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




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):

        try:
            password_validation.validate_password(value)
            print("e")
        except serializers.ValidationError as e:
            print("er")


            raise serializers.ValidationError(e.messages)
        return value


class ModulePermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermissions
        fields = ['id', 'name', 'codename', 'content_type_id']






class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = ['id', 'department']  # Add necessary fields



class ModulesSerializerPlain(serializers.ModelSerializer):
    class Meta:
        model = Modules
        fields = ['id', 'module', 'icon', 'slug', 'path', 'components']





class RolesSerializerPlain(serializers.ModelSerializer):
    modules = ModulesSerializerPlain(many=True)  # Same as above, adjusting for relationships
    area = AreaSerializer(many=True)
    submodules = SubmoduleSerializer(many=True)
    permissions = ModulePermissionsSerializer(many=True)
    class Meta:
        model = Roles
        fields = ['id', 'role', 'area','permissions', 'modules', 'submodules']



class EmployeeSerializerPlain(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    role = RolesSerializerPlain(many=True, read_only=True)
    modules = ModulesSerializerPlain(many=True, read_only=True)
    module_permissions = ModulePermissionsSerializer(many=True, read_only=True)
    area = AreaSerializer(many=True, read_only=True)
    submodules = SubmoduleSerializer(many=True, read_only=True)
    superior = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)
    added_by = serializers.StringRelatedField(read_only=True)
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'department', 'date_join', 'role', 'modules',
            'module_permissions', 'area', 'submodules', 'locked', 'attempts',
            'cellphone_number', 'telephone_number', 'superior', 'added_by'
        ]


