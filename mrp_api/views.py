from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q, Value
from .models import Area, Departments, ModulePermissions, Modules, Roles, Employee, Submodules
from .serializers import SubmoduleSerializer, ModuleSerializer, EmployeeSerializer, AreaSerializer, RoleSerializer, DepartmentsSerializer, ChangePasswordSerializer
from collections import defaultdict
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
import random
import string


class CustomTokenObtainPairView(TokenObtainPairView):

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        #check if the user exists
        user = User.objects.filter(username=username).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        #check if the user is associated with a CompanyUser instance
        try:
            employee = Employee.objects.get(user=user)
        except Employee.DoesNotExist:
            return Response({"error": "User not associated with a company"}, status=status.HTTP_400_BAD_REQUEST)

        #Check if the user is locked
        if employee.locked == 1:
            return Response({"error": "User is locked. Please contact administrator."},
                            status=status.HTTP_403_FORBIDDEN)

        #authenticate the user
        authenticated_user = authenticate(username=username, password=password)
        if authenticated_user:
            #reset attempts and generate JWT tokens if login is successful
            employee.attempts = 0
            employee.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        else:
            #increment login attempts if authentication fails
            employee.attempts += 1
            employee.save()

            #lock the user after 3 failed attempts
            if employee.attempts >= 3:
                employee.locked = 1
                employee.save()
                return Response({"error": "User is locked due to too many failed login attempts."},
                                status=status.HTTP_403_FORBIDDEN)

            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class ModuleListView(ListAPIView):
    
    def get(self, request):
        modules = Modules.objects.all()
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)


class EmployeeListView(ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def create(self, request, *args, **kwargs):
        data = request.data

        generated_password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))

        hashed_password = make_password(generated_password)


        user_data = {
            "username": data.get("first_name")+data.get("last_name"),
            "email": data.get("email"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "password": hashed_password,
        }
        user, created = User.objects.get_or_create(
            username=user_data["username"], defaults=user_data
        )
        if not created:
            return Response(
                {"error": "User with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # create the Employee
        try:
            employee = Employee.objects.create(
                user=user,
                department=Departments.objects.get(id=data["department"]),
                cellphone_number=data.get("mobile_number"),
                telephone_number=data.get("telephone_number"),
                superior=Employee.objects.filter(id=data.get("supervisor")).first(),
                added_by=request.user,
            )

            # assign roles
            if "role" in data:
                role = Roles.objects.get(id=data["role"])
                employee.role.add(role)

            # assign modules
            if "modules" in data:
                modules = Modules.objects.filter(id__in=data["modules"])
                employee.modules.add(*modules)

            # assign submodules
            if "submodules" in data:
                submodules = Submodules.objects.filter(id__in=data["submodules"])
                modules = set(submodule.module for submodule in submodules)
            for module in modules:
                employee.modules.add(module)
                employee.submodules.add(*submodules)
            # assign areas
            if "area" in data:
                areas = Area.objects.filter(location__in=data["area"])
                employee.area.add(*areas)

            # ssign module permissions
            if "permissions" in data:
                for module_name, actions in data["permissions"].items():
                    for action, has_permission in actions.items():
                        
                        if has_permission:
                            permission = ModulePermissions.objects.filter(
                                codename=action
                            ).first()
                            if permission:
                                employee.module_permissions.add(permission)

            employee.save()
            return_data = {"data": EmployeeSerializer(employee).data, "message": f"Default Password is {generated_password}. Please save it immediatly as this window will close in "}

            return Response(return_data, status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to create employee. Details: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            employee = user.employee
            serializer = EmployeeSerializer(employee)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        except Employee.DoesNotExist:
            return Response({"error": "Employee data not found for this user"}, status=404)



class CombinedModuleListView(APIView):
    def get(self, request):
        modules_with_no_submodules = Modules.objects.filter(submodules__isnull=True)
        submodules = Submodules.objects.all()
      
        modules = list(modules_with_no_submodules) + list(submodules)
       
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AreaListView(ListAPIView):

    def get(self, request):
        area = Area.objects.all()
        serializer = AreaSerializer(area, many=True)
        
        return Response(serializer.data)



class RoleListCreate(ListCreateAPIView):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Roles.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        

class CombinedDataView(APIView):
    
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        
        modules_with_no_submodules = Modules.objects.filter(submodules__isnull=True)
        submodules = Submodules.objects.all()
        modules = list(modules_with_no_submodules) + list(submodules)
        module_serializer = ModuleSerializer(modules, many=True)
        areas = Area.objects.values('location').distinct()  
        area_serializer = AreaSerializer(areas, many=True)
        departments = Departments.objects.all()
        dept_serializer = DepartmentsSerializer(departments, many=True)
        roles = Roles.objects.all()
        role_serializer = RoleSerializer(roles, many=True)

        supervisor_role = roles.filter(role='Supervisors').first()
        
        if supervisor_role:
            #get all employees under the supervisor role
            employees_under_supervisor_role = Employee.objects.filter(role=supervisor_role)
            supervisor_data = employees_under_supervisor_role.values('id', 'user__username', 'user__first_name', 'user__last_name')


        else:
            supervisor_data = []


        #combine all serialized data into single response
        response_data = {
            "modules": module_serializer.data,
            "areas": areas,
            "roles": role_serializer.data,
            "departments": dept_serializer.data,
            "supervisors": supervisor_data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  #save the role with the current user
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            if not user.check_password(old_password):
                return Response({"old_password": ["You entered wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)