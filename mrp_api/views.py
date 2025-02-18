from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, ListCreateAPIView ,RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status, viewsets
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q, Value
from django.db import connection, transaction
from .models import Area, Departments, ModulePermissions, Modules, Roles, Employee, AccessKey, BomMasterlist, PosItems, Sales, UploadedFile, InventoryCode, BosItems, EndingInventory, Forecast
from .serializers import ModuleSerializer, EmployeeSerializer, AreaSerializer, RoleSerializer, DepartmentsSerializer, ChangePasswordSerializer, EmployeeSerializerPlain, RolesSerializerPlain, AccessKeySerializer, UserDetailSerializer,  ModulesSerializerParent, FileUploadSerializer, InventoryCodeSerializer, ForecastSerializer, ForecastUpdateSerializer

from collections import defaultdict
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
import random
import string
from django.core.paginator import Paginator
import pandas as pd
import math
import numpy as np
import hashlib
from rapidfuzz import process


STRING_LIST = ["apple", "banana", "grape", "orange", "pineapple", "watermelon", "mango", "blueberry", "strawberry", "peach"]

def fuzzy_match(query, choices, limit=3, threshold=70):
    matches = process.extract(query, choices, limit=limit, score_cutoff=threshold)
    return [(match, score) for match, score, _ in matches]


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

        authenticated_user = authenticate(username=username, password=password)
        if authenticated_user:

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

    def get(self, request, *args, **kwargs):

        draw = int(request.GET.get('draw', 1))
        page = int(request.GET.get('page', 1))
        length = int(request.GET.get('pageSize', 10))
        search_value = request.GET.get('search', '')
        order_column = request.GET.get('sortColumnIndex', "user__first_name")
        order_direction = request.GET.get('sortDirection', 'asc')
        offset = (page - 1) * length

        if order_direction == 'desc':
            order_column = f"-{order_column}"

        queryset = self.queryset
        if search_value:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_value) |
                Q(user__last_name__icontains=search_value) |
                Q(user__email__icontains=search_value) |
                Q(user__employee__id__icontains=search_value) |

                Q(user__employee__superior__user__first_name__icontains=search_value) |
                Q(user__employee__superior__user__last_name__icontains=search_value) |
                Q(user__email__icontains=search_value) |
                Q(user__last_login__icontains=search_value) |
                Q(user__employee__cellphone_number__icontains=search_value) |
                Q(user__is_active__icontains=search_value)
            ).distinct()

        for_pagination = Paginator(queryset, length)
        queryset = queryset.order_by(order_column)[offset:offset + (length)]
        serializer = self.serializer_class(queryset, many=True)
        response_data = {
            "draw": draw,
            "recordsTotal": self.queryset.count(),
            "recordsFiltered": 1,
            "page_count": for_pagination.count,
            "page_num_pages": for_pagination.num_pages,
            "data": serializer.data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


    def create(self, request, *args, **kwargs):
        data = request.data

        try:
            generated_password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            hashed_password = make_password(generated_password)
            generated_username = f"{data.get('first_name')}{data.get('last_name')}"

            user_email = data.get("email")
            user_data = {
                "username": generated_username,
                "email": user_email,
                "first_name": data.get("first_name"),
                "last_name": data.get("last_name"),
                "password": hashed_password,
            }

            user, created = User.objects.get_or_create(username=user_data["username"], defaults=user_data)
            if not created:
                return Response({"error": "User with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

            employee = Employee.objects.create(
                user=user,
                department=Departments.objects.get(id=data["department"]),
                cellphone_number=data.get("mobile_number"),
                telephone_number=data.get("telephone_number"),
                superior=Employee.objects.filter(id=int(data.get("supervisor"))).first(),
                added_by=request.user,
            )

            if "role" in data:
                role = Roles.objects.get(id=int(data['role']))
                employee.role = role

            if "area" in data:
                areas = Area.objects.filter(location__in=[item['value'] for item in data['area']])
                employee.area.add(*areas)

            if "permissions" in data:
                permission_codenames = [actions for actions, has_permission in data["permissions"].items() if has_permission]

                permissions = ModulePermissions.objects.filter(codename__in=permission_codenames)
                employee.module_permissions.add(*permissions)


                def get_module_hierarchy(module):
                    hierarchy = []
                    current_module = module
                    while current_module:
                        hierarchy.append(current_module)
                        current_module = current_module.parent_module
                    return hierarchy

                modules_to_add = set()
                for permission in permissions:

                    module = permission.module
                    if module:
                        module_hierarchy = get_module_hierarchy(module)
                        modules_to_add.update(module_hierarchy)



                employee.modules.add(*modules_to_add)

            employee.save()

            # Email logic (optional - commented out)
            # send_mail(
            #     "New User",
            #     f"Hi. \nYour Password is {generated_password}",
            #     "your_email@example.com",
            #     [user_email],
            #     fail_silently=False,
            # )

            return_data = {
                "data": EmployeeSerializer(employee).data,
                "message": f"Default Password is {generated_password}. Please save it immediately as this window will close soon.",
            }
            return Response(return_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:

            user = User.objects.get(pk=pk)

            serializer = UserDetailSerializer(user)
            return Response(serializer.data)

        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)



class CombinedModuleListView(APIView):
    def get(self, request):
        modules_with_no_submodules = Modules.objects.filter(submodules__isnull=True)
        submodules = Modules.objects.all()
      
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
        role_instance = serializer.save()

        data = self.request.data
        if 'area' in data:
            areas = Area.objects.filter(location__in=[item['value'] for item in data['area']])
            role_instance.area.add(*areas)


        if "permissions" in data:
                permission_codenames = [actions for actions, has_permission in data["permissions"].items() if has_permission]
                permissions = ModulePermissions.objects.filter(codename__in=permission_codenames)
                role_instance.permissions.add(*permissions)

                def get_module_hierarchy(module):
                    hierarchy = []
                    current_module = module
                    while current_module:
                        hierarchy.append(current_module)
                        current_module = current_module.parent_module
                    return hierarchy

                modules_to_add = set()
                for permission in permissions:

                    module = permission.module
                    if module:
                        module_hierarchy = get_module_hierarchy(module)
                        modules_to_add.update(module_hierarchy)

                role_instance.modules.add(*modules_to_add)

        if 'copy_area' in data and data['copy_area']:
            for role_data in data['roles']:
                role = Roles.objects.get(id=role_data['id'])
                role.area.clear()
                role.area.add(*areas)

        if 'copy_permissions' in data and data['copy_permissions']:
            for role_data in data['roles']:
                role = Roles.objects.get(id=role_data['id'])
                role.permissions.clear()
                role.permissions.add(*permissions)

                modules_to_add_for_roles = set()
                for permission in permissions:
                    module = permission.module
                    if module:
                        module_hierarchy = get_module_hierarchy(module)
                        modules_to_add_for_roles.update(module_hierarchy)

                role.modules.clear()
                role.modules.add(*modules_to_add_for_roles)

        role_instance.save()



class EmployeeEditView(RetrieveUpdateAPIView):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    def update(self, request, *args, **kwargs):
        data = request.data

        try:

            employee = self.get_object()
            user = employee.user

            user.first_name = data.get("first_name", user.first_name)
            user.last_name = data.get("last_name", user.last_name)
            user.email = data.get("email", user.email)
            user.save()

            employee.department = Departments.objects.get(id=data.get("department", employee.department.id))
            employee.cellphone_number = data.get("mobile_number", employee.cellphone_number)
            employee.telephone_number = data.get("telephone_number", employee.telephone_number)
            employee.superior = Employee.objects.filter(id=data.get("supervisor", employee.superior.id)).first()

            if "role" in data:
                role_id = data["role"]
                role = Roles.objects.get(id=role_id)
                employee.role = role

            if "area" in data:
                area_instances = Area.objects.filter(location__in=[area["value"] for area in data["area"]])
                employee.area.set(area_instances)

            if "permissions" in data:

                employee.module_permissions.clear()

                modules_to_add = set()
                for action, has_permission in data['permissions'].items():
                    if has_permission:
                        permission = ModulePermissions.objects.filter(codename=action).first()
                        if permission:
                            employee.module_permissions.add(permission)

                            def get_module_hierarchy(module):
                                hierarchy = []
                                while module:
                                    hierarchy.append(module)
                                    module = module.parent_module
                                return hierarchy

                            module_hierarchy = get_module_hierarchy(permission.module)
                            modules_to_add.update(module_hierarchy)

                employee.modules.set(modules_to_add)

            employee.save()

            return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to update employee. Details: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RoleEditView(RetrieveUpdateAPIView):
    queryset = Roles.objects.all()
    serializer_class = RolesSerializerPlain

    def update(self, request, pk,*args, **kwargs):

        try:
            data = request.data
            role_instance = Roles.objects.get(id=pk)

            if "area" in data:
                role_instance.area.clear()
                areas = Area.objects.filter(location__in=[item['value'] for item in data['area']])
                role_instance.area.add(*areas)

            if "permissions" in data:
                role_instance.permissions.clear()

                modules_to_add = set()
                for action, has_permission in data['permissions'].items():

                    if has_permission:
                        permission = ModulePermissions.objects.filter(codename=action).first()
                        if permission:
                            role_instance.permissions.add(permission)

                            def get_module_hierarchy(module):
                                hierarchy = []
                                while module:
                                    hierarchy.append(module)
                                    module = module.parent_module

                                return hierarchy

                            module_hierarchy = get_module_hierarchy(permission.module)
                            modules_to_add.update(module_hierarchy)

                role_instance.modules.set(modules_to_add)

            role_instance.save()
            return Response(
                    RolesSerializerPlain(role_instance).data,
                    status=status.HTTP_200_OK
                )
        except Roles.DoesNotExist:
                return Response(
                    {"detail": "Role not found."},
                    status=status.HTTP_404_NOT_FOUND
                )


class CombinedDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules_with_no_submodules = Modules.objects.filter(submodules__isnull=True)
        module_serializer = ModulesSerializerParent(modules_with_no_submodules, many=True)

        areas = Area.objects.all().values()
        departments = Departments.objects.all()
        dept_serializer = DepartmentsSerializer(departments, many=True)
        roles = Roles.objects.all()
        role_serializer = RoleSerializer(roles, many=True)

        supervisor_role = roles.filter(role='Supervisors').first()
        if supervisor_role:
            employees_under_supervisor_role = Employee.objects.filter(role=supervisor_role)
            supervisor_data = employees_under_supervisor_role.values(
                'user__id', 'user__username', 'user__first_name', 'user__last_name'
            )
        else:
            supervisor_data = []
        response_data = {
            "modules": module_serializer.data,
            "areas": areas,
            "roles": role_serializer.data,
            "departments": dept_serializer.data,
            "supervisors": supervisor_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  # Save the role with the current user
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
                return Response({"new_password": ["You entered wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class EmployeeFlatDetailView(APIView):

    def get(self, request, pk):
        try:
            employee = Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = EmployeeSerializerPlain(employee)
        return Response(serializer.data)


class RoleFlatDetailView(APIView):

    def get(self, request, pk):
        try:
            role = Roles.objects.get(pk=pk)
        except Roles.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RolesSerializerPlain(role)
        return Response(serializer.data)


class AccessKeyView(ListAPIView):

    def get(self, request):
        access_key = AccessKey.objects.all()
        serialized_key = AccessKeySerializer(access_key, many=True)

        return Response(serialized_key.data)



"""Upload excel part. Start of process"""



class PosItemsUploadView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            try:
                df = pd.read_excel(file, engine='openpyxl')

                if 'POS CODE' not in df.columns or 'MENU - DESCRIPTION' not in df.columns:
                    return Response({"error": "Missing 'sku_code' or 'sku_description' columns."}, status=status.HTTP_400_BAD_REQUEST)

                distinct_skus = df[['POS CODE', 'MENU - DESCRIPTION']].drop_duplicates(subset='POS CODE')

                pos_items = [
                    PosItems(menu_description=row['MENU - DESCRIPTION'], pos_item=row['POS CODE'])
                    for _, row in distinct_skus.iterrows()
                ]

                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_positems DISABLE KEYS;')

                    PosItems.objects.bulk_create(pos_items, batch_size=1000)

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_positems ENABLE KEYS;')

                return Response({"message": "✅ POS Items imported successfully!"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadBOMMasterlist(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            try:
                df = pd.read_excel(file, engine='openpyxl')

                required_columns = [
                    'POS CODE', 'CATEGORY', 'PD ITEM DESCRIPTION', 'BOM', 'UOM',
                    'BOS CODE', 'BOS MATERIAL DESCRIPTION', 'BOS MATERIAL UOM'
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return Response({"error": f"Missing columns: {', '.join(missing_columns)}"}, status=status.HTTP_400_BAD_REQUEST)

                df = df.where(pd.notna(df), None)

                pos_codes = df['POS CODE'].unique()
                bos_codes = df['BOS CODE'].unique()

                pos_items_map = {item.pos_item: item for item in PosItems.objects.filter(pos_item__in=pos_codes)}
                bos_items_map = {item.bos_code: item for item in BosItems.objects.filter(bos_code__in=bos_codes)}

                chunk_size = 1000
                num_chunks = int(np.ceil(len(df) / chunk_size))
                chunks = np.array_split(df, num_chunks)

                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_bommasterlist DISABLE KEYS;')

                    for chunk in chunks:
                        bom_objects = []
                        for _, row in chunk.iterrows():
                            pos_item = pos_items_map.get(str(row['POS CODE']))
                            bos_item = bos_items_map.get(str(row['BOS CODE']))

                            if pos_item or bos_item:
                                bom_objects.append(
                                    BomMasterlist(
                                        pos_code=pos_item,
                                        bos_code=bos_item,  # Assign the instance, NOT a raw string
                                        category=row['CATEGORY'],
                                        item_description=row['PD ITEM DESCRIPTION'],
                                        bom=row['BOM'],
                                        uom=row['UOM'],
                                    )
                                )
                        BomMasterlist.objects.bulk_create(bom_objects, batch_size=1000)

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_bommasterlist ENABLE KEYS;')

                return Response({"message": "✅ Data imported successfully!"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# orig 294933
# Last Row 386070
# 335874

class SalesUploadView(APIView):
    def get_file_hash(self, file):
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']

            file_hash = self.get_file_hash(file)
            if UploadedFile.objects.filter(file_hash=file_hash).exists():
                return Response({"error": "🚫 This file has already been uploaded."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                df = pd.read_excel(file, engine='openpyxl')
                df.columns = df.columns.str.upper()


                required_columns = [
                    'IFS CODE', 'NAME OF OUTLET', 'OR NO.', 'CUSTOMER NAME', 'SKU CODE',
                    'QTY', 'UNIT PRICE', 'GROSS SALES', 'TYPE OF DISCOUNT', 'DISC AMOUNT',
                    'VAT DEDUCT', 'NET SALES', 'MODE OF PAYMENT','TRANSACTION TYPE', 'NOTE', 'REMARKS', 'SALES DATE', 'TIME'
                ]

                if not all(col.upper() in df.columns for col in required_columns):

                    return Response({"error": "Missing required columns."}, status=status.HTTP_400_BAD_REQUEST)


                existing_or_numbers = set(Sales.objects.filter(or_number__in=df['OR NO.']).values_list('or_number', flat=True))

                new_rows = df[~df['OR NO.'].isin(existing_or_numbers)]

                if new_rows.empty:
                    return Response({"error": "No new OR numbers to insert."}, status=status.HTTP_400_BAD_REQUEST)

                sales_objects = []
                for _, row in new_rows.iterrows():
                    try:

                        outlet = Area.objects.get(location=row['NAME OF OUTLET'])

                        pos_item = PosItems.objects.get(pos_item=row['SKU CODE'])


                        sales_objects.append(
                            Sales(
                                ifs_code=row['IFS CODE'],
                                outlet=outlet,
                                or_number=row['OR NO.'],
                                customer_name=row.get('CUSTOMER NAME'),
                                sku_code=pos_item,
                                quantity=row['QTY'],
                                unit_price=row['UNIT PRICE'],
                                gross_sales=row['GROSS SALES'],
                                type_of_discount=row.get('TYPE OF DISCOUNT'),
                                discount_amount=row['DISC AMOUNT'],
                                vat_deduct=row['VAT DEDUCT'],
                                net_sales=row['NET SALES'],
                                mode_of_payment=row.get('MODE OF PAYMENT'),
                                transaction_type=row['TRANSACTION TYPE'],
                                note=row.get('NOTE'),
                                remarks=row.get('REMARKS'),
                                sales_date=row['SALES DATE'],
                                time=row['TIME']
                            )
                        )
                    except (Area.DoesNotExist, PosItems.DoesNotExist):
                        continue

                with transaction.atomic():

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_sales DISABLE KEYS;')

                    Sales.objects.bulk_create(sales_objects, batch_size=1000)

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_sales ENABLE KEYS;')

                    UploadedFile.objects.create(file_hash=file_hash)

                return Response({"message": "✅ Sales data imported successfully!"}, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class EndingInventoryUploadView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            area_id = request.data.get('area_id')

            if not area_id:
                return Response({"error": "Missing 'area_id' in request."}, status=status.HTTP_400_BAD_REQUEST)

            area = Area.objects.filter(id=area_id).first()
            if not area:
                return Response({"error": f"Area ID {area_id} not found."}, status=status.HTTP_400_BAD_REQUEST)

            inventory_code = InventoryCode.objects.create(area=area)

            try:
                df = pd.read_excel(file, engine='openpyxl')

                required_columns = ["BOS MATCODE", "BOS MATERIAL DESCRIPTION", "QTY", "COLD/DRY/FOR PR"]
                if not all(col in df.columns for col in required_columns):
                    return Response({"error": "Missing required columns."}, status=status.HTTP_400_BAD_REQUEST)

                distinct_entries = df[["BOS MATCODE", "BOS MATERIAL DESCRIPTION", "QTY", "COLD/DRY/FOR PR"]].drop_duplicates(subset="BOS MATCODE")

                inventory_items = []

                for _, row in distinct_entries.iterrows():
                    try:
                        bom_entry = BosItems.objects.filter(bos_code=row["BOS MATCODE"]).first()

                        if not bom_entry:
                            bom_entry = BosItems.objects.create(
                                bos_code=row["BOS MATCODE"],
                                bos_material_description=row["BOS MATERIAL DESCRIPTION"]
                            )

                        inventory_items.append(EndingInventory(
                            inventory_code=inventory_code,
                            bom_entry=bom_entry,

                            actual_ending=row["QTY"] if pd.notna(row["QTY"]) else 0
                        ))

                    except Exception as e:
                        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_endinginventory DISABLE KEYS;')

                    EndingInventory.objects.bulk_create(inventory_items, batch_size=1000)

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_endinginventory ENABLE KEYS;')

                return Response({"message": "✅ Ending Inventory imported successfully!"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BosItemsUploadView(APIView):
    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            try:
                df = pd.read_excel(file, engine='openpyxl')

                required_columns = {
                    "BOS MATCODE": "bos_code",
                    "BOS MATERIAL DESCRIPTION": "bos_material_description",
                    "BOS UOM": "bos_uom",
                    "DELIVERY UOM": "delivery_uom",
                    "BUNDLING SIZE": "bundling_size",
                    "CONVERSION DELIVERY UOM": "conversion_delivery_uom",
                    "COLD/DRY/FOR PR": "category",
                }

                missing_columns = [col for col in required_columns.keys() if col not in df.columns]
                if missing_columns:
                    return Response({"error": f"Missing columns: {', '.join(missing_columns)}"}, status=status.HTTP_400_BAD_REQUEST)


                df.rename(columns=required_columns, inplace=True)
                df.drop_duplicates(subset=['bos_code'], inplace=True)
                df = df.where(pd.notna(df), None)

                #prepare for bulk insert data
                bos_items = [
                    BosItems(
                        bos_code=row['bos_code'],
                        bos_material_description=row['bos_material_description'],
                        bos_uom=row['bos_uom'],
                        delivery_uom=row['delivery_uom'],
                        bundling_size=row['bundling_size'],
                        conversion_delivery_uom=row['conversion_delivery_uom'],
                        category=row['category'],
                    ) for _, row in df.iterrows()
                ]

                #use bulk_create for efficient inserts
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_bositems DISABLE KEYS;')

                    BosItems.objects.bulk_create(bos_items, batch_size=1000)

                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE mrp_api_bositems ENABLE KEYS;')

                return Response({"message": "✅ BOS Items imported successfully!"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class InventoryCodeByAreaView(APIView):
    def get(self, request, pk):
        try:
            area = Area.objects.get(id=pk)
            inventory_codes = InventoryCode.objects.filter(area=area)
            serializer = InventoryCodeSerializer(inventory_codes, many=True)
            return Response(serializer.data)
        except Area.DoesNotExist:
            return Response({"detail": "Area not found"}, status=status.HTTP_404_NOT_FOUND)


class ForecastByInventoryCodeView(APIView):
    def get(self, request, pk):
        try:
            inventory_code = InventoryCode.objects.get(id=pk)
            forecasts = Forecast.objects.filter(inventory_code=inventory_code)
            serializer = ForecastSerializer(forecasts, many=True)
            return Response(serializer.data)
        except InventoryCode.DoesNotExist:
            return Response({"detail": "Inventory code not found"}, status=status.HTTP_404_NOT_FOUND)



class UpdateForecastView(APIView):
    def patch(self, request, pk):
        forecasts_data = request.data
        updated_forecasts = []
        for forecast_data in forecasts_data['updated_forecasts']:
            bom_entry_id = forecast_data.get('bom_entry_id')
            try:
                inventory_code = InventoryCode.objects.get(id=pk)

            except InventoryCode.DoesNotExist:
                return Response({"detail": f"InventoryCode with ID {pk} not found."}, status=status.HTTP_404_NOT_FOUND)

            try:
                bom_entry = BosItems.objects.get(id=bom_entry_id)

            except BosItems.DoesNotExist:
                return Response({"detail": f"BosItems with ID {bom_entry_id} not found."}, status=status.HTTP_404_NOT_FOUND)

            try:

                forecast = Forecast.objects.get(inventory_code=inventory_code, bom_entry=bom_entry)

                forecast_data['for_final_delivery'] = max(0, math.ceil((forecast.forecast + forecast_data['adjustment']) / forecast.bom_entry.bundling_size) * forecast.bom_entry.bundling_size)

            except Forecast.DoesNotExist:
                return Response({"detail": f"Forecast with ID {pk} for InventoryCode ID {pk} and BosItems ID {bom_entry_id} not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = ForecastUpdateSerializer(forecast, data=forecast_data, partial=True)

            if serializer.is_valid():
                updated_forecasts.append(serializer.save())
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"updated_forecasts": ForecastUpdateSerializer(updated_forecasts, many=True).data}, status=status.HTTP_200_OK)
