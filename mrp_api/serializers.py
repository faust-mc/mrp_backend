
from rest_framework import serializers
from .models import Area, Departments, ModulePermissions, Modules, Submodules,Roles, Employee
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class SubmoduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submodules
        fields = ['id', 'submodule', 'slug']

class ModuleSerializer(serializers.ModelSerializer):
    submodules = SubmoduleSerializer(many=True, read_only=True, source='submodules_set')
    
    class Meta:
        model = Modules
        fields = ['id', 'module', 'submodules', 'icon', 'slug']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ['id', 'role']  # Include only necessary fields

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'last_login']

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    area = serializers.StringRelatedField()  # Assuming Area has a meaningful __str__()
    area_id = serializers.PrimaryKeyRelatedField(source='area', read_only=True)
    department = serializers.StringRelatedField(allow_null=True)  # Same assumption
    department_id = serializers.PrimaryKeyRelatedField(source='department', read_only=True)
    role = RoleSerializer(many=True)  # For roles details
    superior = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'user', 'area', 'area_id', 'department', 'department_id', 'date_join', 'role', 'locked', 'attempts', 'superior', 'cellphone_number', 'telephone_number']


    def get_superior(self, obj):
        # If the supervisor exists, serialize their details
        if obj.superior:
            return {
                "id": obj.superior.id,
                "username": obj.superior.user.username,
                "email": obj.superior.user.email,
                "full_name": f"{obj.superior.user.first_name} {obj.superior.user.last_name}",
            }
        return None