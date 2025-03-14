from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import CustomTokenObtainPairView, ModuleListView, EmployeeListView, EmployeeDetailView, CombinedModuleListView, AreaListView, RoleListCreate, CombinedDataView, ChangePasswordView, EmployeeFlatDetailView, EmployeeEditView, RoleFlatDetailView, RoleEditView, AccessKeyView, UploadBOMMasterlist, PosItemsUploadView, SalesUploadView, EndingInventoryUploadView, BosItemsUploadView, InventoryCodeByAreaView, ForecastByInventoryCodeView, InsertDeliveryItemsView, UploadByRequest, DeleteDeliveryItemsView,UpdateDeliveryItemsView, UserAreasView, EndingInventoryListView, SalesReportListView, InitialReplenishmentListView, ForecastListView, ByRequestItemsListView, InventoryCodeDetailView, SubmitInventoryView, approve_mrp, ammend_mrp, SalesReportListViewDL, UserDefinedVariablesListCreateView, UserDefinedVariablesDetailView, ConsolidatedItemsView


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
    path('accesskey-list/', AccessKeyView.as_view(), name='accesskey-list'),
    path('for-forms/', CombinedDataView.as_view(), name='for-forms'),
    path('get-area-option/<int:pk>/', UserAreasView.as_view(), name='get-area-option'),
    path('get-area-option/<int:pk>/', UserAreasView.as_view(), name='get-area-option'),
    path('get-inventory-items/<int:pk>/', EndingInventoryListView.as_view(), name='get-inventory-items'),
    path('get-inventory-code/<int:pk>/', InventoryCodeDetailView.as_view(), name='get-inventory-code'),
    path('sales-report/<int:inventory_id>/', SalesReportListView.as_view(), name='sales-report-list'),
    path('get-initial-replenishment/<int:inventory_id>/', InitialReplenishmentListView.as_view(), name='sales-report-list'),
    path('forecast/<int:inventory_code_id>/', ForecastListView.as_view(), name='forecast-list'),
    path('by_request_items/<int:inventory_id>/', ByRequestItemsListView.as_view(), name='by-request-list'),
    path('submit/<int:idofinventory>/', SubmitInventoryView.as_view(), name='submit'),
    path('approve/<int:idofinventory>/', approve_mrp, name='approve'),
    path('ammend/<int:idofinventory>/', ammend_mrp, name='ammend'),
    path('consolidated/<int:inventory_id>/', ConsolidatedItemsView.as_view(), name='consolidated-order-list'),
    path('user-defined-variables/', UserDefinedVariablesListCreateView.as_view(), name='user-defined-variables-list'),
    path('user-defined-variables/<int:pk>/', UserDefinedVariablesDetailView.as_view(), name='user-defined-variables-detail'),

    path('sales-report/<int:inventory_id>/', SalesReportListViewDL.as_view(), name='sales-report-dl'),

    path('areainventory/<int:area_id>/', InventoryCodeByAreaView.as_view(), name='area-inventory'),
    #path('forecast/<int:pk>/', ForecastByInventoryCodeView.as_view(), name='forecast'),
    path('request/<int:pk>/', InsertDeliveryItemsView.as_view(), name='update-forecast'),
    path('update-request/<int:pk>/', UpdateDeliveryItemsView.as_view(), name='delete-request'),
    path('delete-request/<int:pk>/', DeleteDeliveryItemsView.as_view(), name='delete-request'),

#481405

    #uploads
    path('master-data-upload/', UploadBOMMasterlist.as_view(), name='file-upload'),
    path('pos-item-upload/', PosItemsUploadView.as_view(), name='post_item-upload'),
    path('bom-item-upload/', BosItemsUploadView.as_view(), name='bom_item-upload'),
    path('by-request-item-upload/', UploadByRequest.as_view(), name='by-request-item-upload'),
    path('sales-upload/', SalesUploadView.as_view(), name='sales-upload'),
    path('ending-inventory-upload/', EndingInventoryUploadView.as_view(), name='ending-inventory-upload'),

    # change password
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    
]

if settings.DEBUG:
    urlpatterns += static(settings.SALES_FILES_URL, document_root=settings.SALES_FILES_ROOT)

#path('searchlist/', SearchList.as_view(), name='searchlist'),
# path('get_user/', GetUser.as_view(), name='get_user'),
# path('update-ticket/<int:pk>/', UpdateTicketView.as_view(),
#      name='update-ticket-status'),
#
# path('store-token/', ExchangeTokenView.as_view(), name='store_token'),
# path('get_plate_no/', PlateNumberView.as_view(), name='get_plate_no'),
# path('change-password/', ChangePasswordView.as_view(), name='change-password'),
#
# queryset = queryset.order_by(order_column)
#
#         # Paginate queryset
#         paginator = Paginator(queryset, length)
#
#         page_number = (start // length) + 1
#
#         try:
#             page = paginator.page(page_number)
#
