# urls.py
from django.urls import path
from .views import CustomTokenObtainPairView, ModuleListView, EmployeeListView, EmployeeDetailView, CombinedModuleListView, AreaListView, RoleListCreate, CombinedDataView, ChangePasswordView, EmployeeFlatDetailView, EmployeeEditView, RoleFlatDetailView, RoleEditView

urlpatterns = [
    path('mrp_api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('modules/', ModuleListView.as_view(), name='module-list'),

    path('roles/', RoleListCreate.as_view(), name='roles-list'),
    path('area-list/', AreaListView.as_view(), name='area-list'),
    path('combined-modules/', CombinedModuleListView.as_view(), name='combined-module-list'),
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'),
    path('employee/edit/<int:pk>/', EmployeeEditView.as_view(), name='employee-edit'),
    path('role/edit/<int:pk>/', RoleEditView.as_view(), name='role-edit'),
    path('employeesplain/<int:pk>/', EmployeeFlatDetailView.as_view(), name='employeesplain'),
    path('roleplain/<int:pk>/', RoleFlatDetailView.as_view(), name='roleplain'),
    path('for-forms/', CombinedDataView.as_view(), name='for-forms'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
]

#path('searchlist/', SearchList.as_view(), name='searchlist'),
# path('get_user/', GetUser.as_view(), name='get_user'),
# path('update-ticket/<int:pk>/', UpdateTicketView.as_view(),
#      name='update-ticket-status'),
#
# path('store-token/', ExchangeTokenView.as_view(), name='store_token'),
# path('get_plate_no/', PlateNumberView.as_view(), name='get_plate_no'),
# path('change-password/', ChangePasswordView.as_view(), name='change-password'),