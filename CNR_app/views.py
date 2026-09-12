from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from CNR_app.models import User
from CNR_app.serializers import CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer
from CNR_app.permissions import IsSuperAdmin, IsManagerOrAdmin
from django.db import transaction
from django.utils import timezone
from CNR_app.models import Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle
from CNR_app.serializers import (
    StationSerializer, FuelProductSerializer, FuelPriceHistorySerializer,
    TankSerializer, PumpSerializer, NozzleSerializer
)
from CNR_app.permissions import IsManagerOrAdmin, IsSuperAdmin

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class CurrentUserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('-date_joined')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [IsManagerOrAdmin()]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]

class StationListCreateView(generics.ListCreateAPIView):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [permissions.IsAuthenticated()]

class FuelProductListCreateView(generics.ListCreateAPIView):
    queryset = FuelProduct.objects.all()
    serializer_class = FuelProductSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManagerOrAdmin()]
        return [permissions.IsAuthenticated()]