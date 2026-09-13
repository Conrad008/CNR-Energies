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
from CNR_app.models import Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle, Shift, PumpReading, Reconciliation
from CNR_app.serializers import (
    StationSerializer, FuelProductSerializer, FuelPriceHistorySerializer,
    TankSerializer, PumpSerializer, NozzleSerializer, ShiftSerializer, PumpReadingSerializer, 
    ReconciliationSerializer
)
from CNR_app.permissions import IsManagerOrAdmin, IsSuperAdmin, IsAccountantOrAdmin
from decimal import Decimal

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

class FuelPriceUpdateView(APIView):
    permission_classes = [IsManagerOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            product = FuelProduct.objects.get(pk=pk)
        except FuelProduct.DoesNotExist:
            return Response({"error": "Fuel product not found"}, status=status.HTTP_404_NOT_FOUND)

        new_price = request.data.get('price')
        if not new_price or float(new_price) <= 0:
            return Response({"error": "Invalid price"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        FuelPriceHistory.objects.filter(product=product, effective_to__isnull=True).update(effective_to=now)

        FuelPriceHistory.objects.create(
            product=product,
            price=new_price,
            effective_from=now,
            updated_by=request.user
        )
        product.current_price = new_price
        product.save()

        return Response(FuelProductSerializer(product).data, status=status.HTTP_200_OK)

class TankListCreateView(generics.ListCreateAPIView):
    queryset = Tank.objects.all()
    serializer_class = TankSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

class PumpListCreateView(generics.ListCreateAPIView):
    queryset = Pump.objects.all()
    serializer_class = PumpSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManagerOrAdmin()]
        return [permissions.IsAuthenticated()]


class NozzleListCreateView(generics.ListCreateAPIView):
    queryset = Nozzle.objects.all()
    serializer_class = NozzleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

class StartShiftView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        station_id = request.data.get('station')
        opening_float = request.data.get('opening_cash_float', 0.00)

        if Shift.objects.filter(attendant=request.user, status__in=[Shift.Status.OPEN, Shift.Status.ACTIVE]).exists():
            return Response({"error": "You already have an active shift open."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            station = Station.objects.get(id=station_id)
        except Station.DoesNotExist:
            return Response({"error": "Station not found."}, status=status.HTTP_404_NOT_FOUND)

        shift = Shift.objects.create(
            station=station,
            attendant=request.user,
            opening_cash_float=opening_float,
            status=Shift.Status.ACTIVE
        )

        nozzles = Nozzle.objects.filter(pump__station=station)
        for nozzle in nozzles:
            last_reading = PumpReading.objects.filter(nozzle=nozzle).exclude(closing_meter__isnull=True).order_by('-shift__start_time').first()
            opening_meter = last_reading.closing_meter if last_reading else Decimal('0.00')

            PumpReading.objects.create(
                shift=shift,
                nozzle=nozzle,
                opening_meter=opening_meter,
                unit_price=nozzle.product.current_price
            )

        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)