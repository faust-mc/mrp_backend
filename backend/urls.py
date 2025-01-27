from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('adminlpre/', admin.site.urls),
    #path('mrp_api/token/', TokenObtainPairView.as_view()),
    path('mrp_api/token/refresh/', TokenRefreshView.as_view()),
    path('mrp/', include('mrp_api.urls'))
]





