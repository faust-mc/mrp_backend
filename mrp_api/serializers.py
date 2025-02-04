
from rest_framework import serializers
from .models import Area, ModulePermissions, Modules, Roles, Employee, Departments, AccessKey
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import password_validation
from rest_framework import serializers





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
        fields = ['id', 'module', 'icon', 'slug', 'path', 'components', 'submodules']

    def get_submodules(self, obj):
        submodules = obj.submodules.all()
        return ModuleSerializer(submodules, many=True).data



class RoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Roles
        fields = ['id', 'role']



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'last_login']


class EmployeeMinimalSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = ['id', 'user']



class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    role = RoleSerializer()
    superior = EmployeeMinimalSerializer()
    class Meta:
        model = Employee
        fields = [
            'user',
            'id',
            'department',
            'date_join',
            'role',
            'modules',
            'area',
            'locked',
            'attempts',
            'cellphone_number',
            'telephone_number',
            'superior',
            'module_permissions'
        ]
        depth = 1  # Include nested details



class UserDetailSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField()
    accessible_modules = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'employee_details', 'accessible_modules']

    def get_employee_details(self, obj):
        try:
            employee = Employee.objects.get(user=obj)
            return EmployeeSerializer(employee).data
        except Employee.DoesNotExist:
            return None

    def get_accessible_modules(self, obj):
        try:
            employee = Employee.objects.get(user=obj)
            direct_modules = employee.modules.all()
            #recursively build the module hierarchy with their submodules
            def build_module_hierarchy(module):
                #find submodules that are linked to this module as parent
                submodules = Modules.objects.filter(parent_module=module, id__in=employee.modules.all())

                module_data = {
                    "id": module.id,
                    "module": module.module,
                    "icon": module.icon,
                    "slug": module.slug,
                    "path": module.path,
                    "components": module.components,
                    "submodules": [build_module_hierarchy(submodule) for submodule in submodules]
                }
                return module_data
            accessible_modules = []
            for module in direct_modules:
                #if the module has no parent, treat it as a root module and build its hierarchy
                if module.parent_module is None:
                    accessible_modules.append(build_module_hierarchy(module))

            return accessible_modules

        except Employee.DoesNotExist:
            return []


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):

        try:
            password_validation.validate_password(value)
        except serializers.ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class ModulePermissionsSerializer(serializers.ModelSerializer):
    module = ModuleSerializer()
    class Meta:
        model = ModulePermissions
        fields = ['id', 'name', 'codename', 'module']



class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = ['id', 'department']  # Add necessary fields



class ModulesSerializerPlain(serializers.ModelSerializer):
    class Meta:
        model = Modules
        fields = ['id', 'module', 'icon', 'slug', 'path', 'components', 'parent_module']


class ModulesSerializerParent(ModulesSerializerPlain):
    parent_module = serializers.SerializerMethodField()

    class Meta(ModulesSerializerPlain.Meta):
        fields = ModulesSerializerPlain.Meta.fields + ['parent_module']

    def get_parent_module(self, obj):
        if obj.parent_module:
            return {"id": obj.parent_module.id, "module": obj.parent_module.module}
        return None



class RolesSerializerPlain(serializers.ModelSerializer):
    modules = ModulesSerializerPlain(many=True)  # Same as above, adjusting for relationships
    area = AreaSerializer(many=True)

    permissions = ModulePermissionsSerializer(many=True)
    class Meta:
        model = Roles
        fields = ['id', 'role', 'area','permissions', 'modules']



class EmployeeSerializerPlain(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    role = RolesSerializerPlain()
    modules = ModulesSerializerPlain(many=True, read_only=True)
    module_permissions = ModulePermissionsSerializer(many=True, read_only=True)
    area = AreaSerializer(many=True, read_only=True)

    superior = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)
    added_by = serializers.StringRelatedField(read_only=True)
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'department', 'date_join', 'role', 'modules',
            'module_permissions', 'area', 'locked', 'attempts',
            'cellphone_number', 'telephone_number', 'superior', 'added_by'
        ]


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()