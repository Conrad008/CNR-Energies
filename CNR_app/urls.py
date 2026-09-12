from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from CNR_app.views import (
    CustomTokenObtainPairView,
    CurrentUserProfileView,
    UserListCreateView,
    UserDetailView,
    StationListCreateView,
    FuelProductListCreateView,
    FuelPriceUpdateView,
    TankListCreateView,
    PumpListCreateView,
    NozzleListCreateView,
)
urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me/', CurrentUserProfileView.as_view(), name='user_profile'),
    path('users/', UserListCreateView.as_view(), name='user_list_create'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('stations/', StationListCreateView.as_view(), name='station_list_create'),
    path('fuel-products/', FuelProductListCreateView.as_view(), name='fuel_product_list_create'),
    path('fuel-products/<uuid:pk>/update-price/', FuelPriceUpdateView.as_view(), name='fuel_price_update'),
    path('tanks/', TankListCreateView.as_view(), name='tank_list_create'),
    path('pumps/', PumpListCreateView.as_view(), name='pump_list_create'),
    path('nozzles/', NozzleListCreateView.as_view(), name='nozzle_list_create'),
]