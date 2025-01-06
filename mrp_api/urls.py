# urls.py
from django.urls import path
from .views import CustomTokenObtainPairView, ModuleListView, EmployeeListView

urlpatterns = [
    path('mrp_api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('modules/', ModuleListView.as_view(), name='module-list'),
    path('employees/', EmployeeListView.as_view(), name='employee-list'),
    
]

#path('searchlist/', SearchList.as_view(), name='searchlist'),
# path('get_user/', GetUser.as_view(), name='get_user'),
# path('update-ticket/<int:pk>/', UpdateTicketView.as_view(),
#      name='update-ticket-status'),
#
# path('store-token/', ExchangeTokenView.as_view(), name='store_token'),
# path('get_plate_no/', PlateNumberView.as_view(), name='get_plate_no'),
# path('change-password/', ChangePasswordView.as_view(), name='change-password'),