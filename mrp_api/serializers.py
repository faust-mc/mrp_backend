
from rest_framework import serializers
from .models import Area, ModulePermissions, Modules, Roles, Employee, Departments, AccessKey, EndingInventory, InventoryCode, BosItems, Forecast, DeliveryItems, DeliveryCode ,ByRequest, SalesReport, PosItems, BomMasterlist, InitialReplenishment, ByRequestItems
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



class InventoryCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCode
        fields = '__all__'



class ForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forecast
        fields = '__all__'


class PosItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosItems
        fields = ['menu_description', 'pos_item']


class BosItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BosItems
        fields = "__all__"  # This will return all fields of BosItems

class EndingInventorySerializer(serializers.ModelSerializer):
    bom_entry = BosItemsSerializer(read_only=True)  # Nesting BosItems details

    class Meta:
        model = EndingInventory
        fields = ["id", "inventory_code", "bom_entry", "actual_ending", "upcoming_delivery"]


class SalesReportSerializer(serializers.ModelSerializer):
    pos_item = PosItemSerializer(read_only=True)
    class Meta:
        model = SalesReport
        fields = "__all__"



class ByRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ByRequest
        fields = '__all__'


class BomMasterlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = BomMasterlist
        fields = ['item_description', 'pos_code', 'bos_code']



class InitialReplenishmentSerializer(serializers.ModelSerializer):

    bom_entry_pos_code = serializers.CharField(source='bom_entry.pos_code.pos_item', read_only=True)
    bom_entry_bos_code = serializers.CharField(source='bom_entry.bos_code.bos_code', read_only=True)
    bom_entry_item_description = serializers.CharField(source='bom_entry.item_description', read_only=True)

    class Meta:
        model = InitialReplenishment
        fields = '__all__'


class ByRequestItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ByRequestItems
        fields = "__all__"  # Ensure all fields are included

class ByRequestSerializerC(serializers.ModelSerializer):
    by_request_item = ByRequestItemsSerializer(read_only=True)  # Nested Serializer

    class Meta:
        model = ByRequest
        fields = "__all__"


class DeliveryItemsSerializer(serializers.ModelSerializer):
    bom_entry_id = serializers.IntegerField(write_only=True)
    inventory_code_id = serializers.IntegerField(write_only=True)
    first_adjustment = serializers.FloatField()
    first_final_delivery = serializers.FloatField()


    class Meta:
        model = DeliveryItems
        fields = ['bom_entry_id', 'inventory_code_id', 'first_adjustment','first_final_delivery']

    def validate_bom_entry_id(self, value):
        try:
            return BosItems.objects.get(id=value)
        except BosItems.DoesNotExist:
            raise serializers.ValidationError(f"BosItems with ID {value} does not exist.")

    def validate_inventory_code_id(self, value):
        try:
            return InventoryCode.objects.get(id=value)
        except InventoryCode.DoesNotExist:
            raise serializers.ValidationError(f"InventoryCode with ID {value} does not exist.")

    def create(self, validated_data):
        delivery_code, _ = DeliveryCode.objects.get_or_create(
            inventory_code=validated_data['inventory_code_id']
        )

        return DeliveryItems.objects.create(
            delivery_code=delivery_code,
            bom_entry=validated_data['bom_entry_id'],
            first_adjustment=validated_data['first_adjustment'],
            first_final_delivery=validated_data['first_final_delivery'],
        )
