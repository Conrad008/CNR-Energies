from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from CNR_app.views import (CustomTokenObtainPairView, CurrentUserProfileView, UserListCreateView, UserDetailView,)

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me/', CurrentUserProfileView.as_view(), name='user_profile'),
    
    path('users/', UserListCreateView.as_view(), name='user_list_create'),
    path('users/<uuid:pk>/', UserDetailView.as_view(), name='user_detail'),
]