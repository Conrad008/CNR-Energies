from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from CNR_app.views import (CustomTokenObtainPairView, CurrentUserProfileView, UserListCreateView, UserDetailView,)