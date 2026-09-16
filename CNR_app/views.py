from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from CNR_app.models import User
from CNR_app.serializers import CreditSaleSerializer, CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer
from CNR_app.permissions import IsSuperAdmin, IsManagerOrAdmin
from django.db import transaction
from django.utils import timezone
from CNR_app.models import Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle, Shift, PumpReading, Reconciliation, DipReading, Delivery, Tank, PumpReading, CreditCustomer, CreditPayment, CreditSale
from CNR_app.serializers import (
    StationSerializer, FuelProductSerializer, FuelPriceHistorySerializer,
    TankSerializer, PumpSerializer, NozzleSerializer, ShiftSerializer, PumpReadingSerializer, 
    ReconciliationSerializer, DipReadingSerializer, DeliverySerializer,CreditCustomerSerializer, 
    CreditPaymentSerializer
)
from CNR_app.permissions import IsManagerOrAdmin, IsSuperAdmin, IsAccountantOrAdmin, IsInventoryOfficerOrAdmin
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

        if not station_id:
            return Response({"error": "Station ID is required in the request body."}, status=status.HTTP_400_BAD_REQUEST)

        if Shift.objects.filter(attendant=request.user, status__in=[Shift.Status.OPEN, Shift.Status.ACTIVE]).exists():
            return Response({"error": "You already have an active shift open."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            station = Station.objects.get(id=station_id)
        except (Station.DoesNotExist, ValueError):
            return Response({"error": f"Station with ID '{station_id}' was not found or is an invalid UUID."}, status=status.HTTP_404_NOT_FOUND)

        nozzles = Nozzle.objects.filter(pump__station=station)
        if not nozzles.exists():
            return Response({"error": "No nozzles found for this station. Please seed hardware data first."}, status=status.HTTP_400_BAD_REQUEST)

        shift = Shift.objects.create(
            station=station,
            attendant=request.user,
            opening_cash_float=opening_float,
            status=Shift.Status.ACTIVE
        )

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
    
class RecordClosingMetersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            shift = Shift.objects.get(pk=pk, attendant=request.user)
        except Shift.DoesNotExist:
            return Response({"error": "Active shift not found."}, status=status.HTTP_404_NOT_FOUND)

        readings_data = request.data.get('readings', [])
        for item in readings_data:
            try:
                reading = PumpReading.objects.get(shift=shift, nozzle_id=item['nozzle_id'])
                closing_val = Decimal(str(item['closing_meter']))

                if closing_val < reading.opening_meter:
                    return Response({"error": f"Closing meter for nozzle {item['nozzle_id']} cannot be lower than opening meter."}, status=status.HTTP_400_BAD_REQUEST)

                reading.closing_meter = closing_val
                reading.save()
            except PumpReading.DoesNotExist:
                continue

        shift.status = Shift.Status.PENDING_RECONCILIATION
        shift.save()

        return Response(ShiftSerializer(shift).data, status=status.HTTP_200_OK)

class ReconcileShiftView(APIView):
    permission_classes = [IsAccountantOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            shift = Shift.objects.get(pk=pk)
        except Shift.DoesNotExist:
            return Response({"error": "Shift not found."}, status=status.HTTP_404_NOT_FOUND)

        actual_cash = Decimal(str(request.data.get('actual_cash', '0.00')))
        actual_mpesa = Decimal(str(request.data.get('actual_mpesa', '0.00')))
        actual_card = Decimal(str(request.data.get('actual_card', '0.00')))
        actual_credit = Decimal(str(request.data.get('actual_credit', '0.00')))

        expected_total = Decimal('0.00')
        for reading in shift.pump_readings.all():
            expected_total += reading.expected_revenue

        actual_total = actual_cash + actual_mpesa + actual_card + actual_credit
        variance = actual_total - expected_total

        reconciliation, _ = Reconciliation.objects.update_or_create(
            shift=shift,
            defaults={
                'expected_revenue': expected_total,
                'actual_cash': actual_cash,
                'actual_mpesa': actual_mpesa,
                'actual_card': actual_card,
                'actual_credit': actual_credit,
                'variance': variance,
                'approved_by': request.user if request.user.role in [User.Role.SUPER_ADMIN, User.Role.MANAGER] else None,
                'is_approved': True if request.user.role in [User.Role.SUPER_ADMIN, User.Role.MANAGER] else False
            }
        )

        shift.status = Shift.Status.RECONCILED
        shift.end_time = timezone.now()
        shift.save()

        return Response(ReconciliationSerializer(reconciliation).data, status=status.HTTP_200_OK)

class ShiftListView(generics.ListAPIView):
    queryset = Shift.objects.all().order_by('-start_time')
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecordDipReadingView(APIView):
    permission_classes = [IsInventoryOfficerOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            tank = Tank.objects.get(pk=pk)
        except Tank.DoesNotExist:
            return Response({"error": "Tank not found."}, status=status.HTTP_404_NOT_FOUND)

        dip_depth_cm = request.data.get('dip_level_cm')
        physical_liters = request.data.get('dip_liters')

        if not physical_liters or Decimal(str(physical_liters)) < 0:
            return Response({"error": "Invalid dip volume in liters."}, status=status.HTTP_400_BAD_REQUEST)

        physical_liters_dec = Decimal(str(physical_liters))

        if physical_liters_dec > tank.capacity_liters:
            return Response(
                {"error": f"Dip reading ({physical_liters_dec}L) exceeds tank capacity ({tank.capacity_liters}L)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        expected_liters = tank.current_capacity_liters
        variance_liters = physical_liters_dec - expected_liters

        reading = DipReading.objects.create(
            tank=tank,
            dip_depth_cm=dip_depth_cm,
            physical_liters=physical_liters_dec,
            expected_liters=expected_liters,
            variance_liters=variance_liters,
            recorded_by=request.user
        )

        tank.current_capacity_liters = physical_liters_dec
        tank.save()

        return Response(DipReadingSerializer(reading).data, status=status.HTTP_201_CREATED)

class RecordDeliveryView(APIView):
    permission_classes = [IsInventoryOfficerOrAdmin]

    @transaction.atomic
    def post(self, request):
        tank_id = request.data.get('tank')
        invoice = request.data.get('invoice_number')
        supplier = request.data.get('supplier_name')  # incoming payload key, fine to keep as-is
        quantity = Decimal(str(request.data.get('quantity_liters', '0.00')))
        unit_cost = Decimal(str(request.data.get('unit_cost', '0.00')))

        try:
            tank = Tank.objects.get(pk=tank_id)
        except Tank.DoesNotExist:
            return Response({"error": "Tank not found."}, status=status.HTTP_404_NOT_FOUND)

        new_volume = tank.current_capacity_liters + quantity
        if new_volume > tank.capacity_liters:
            return Response(
                {"error": f"Delivery of {quantity}L exceeds available tank ullage ({tank.capacity_liters - tank.current_capacity_liters}L)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_cost = quantity * unit_cost

        delivery = Delivery.objects.create(
            tank=tank,
            invoice_number=invoice,
            supplier=supplier,          
            quantity_liters=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            received_by=request.user
        )

        tank.current_capacity_liters = new_volume
        tank.save()

        return Response(DeliverySerializer(delivery).data, status=status.HTTP_201_CREATED)

class TankStockVarianceView(APIView):
    permission_classes = [IsManagerOrAdmin]

    def get(self, request, pk):
        try:
            tank = Tank.objects.get(pk=pk)
        except Tank.DoesNotExist:
            return Response({"error": "Tank not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_dip = DipReading.objects.filter(tank=tank).order_by('-recorded_at').first()
        physical_liters = latest_dip.physical_liters if latest_dip else tank.current_capacity_liters

        return Response({
            "tank_id": tank.id,
            "tank_name": tank.name,
            "product": tank.product.name,
            "capacity_liters": tank.capacity_liters,
            "current_recorded_liters": tank.current_capacity_liters,
            "last_physical_dip_liters": physical_liters,
            "last_dip_recorded_at": latest_dip.recorded_at if latest_dip else None
        }, status=status.HTTP_200_OK)

class CreditCustomerListCreateView(generics.ListCreateAPIView):
    queryset = CreditCustomer.objects.all().order_by('-created_at')
    serializer_class = CreditCustomerSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsManagerOrAdmin()]
        return [permissions.IsAuthenticated()]

class CreditCustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CreditCustomer.objects.all()
    serializer_class = CreditCustomerSerializer
    permission_classes = [IsManagerOrAdmin]

class RecordCreditPaymentView(APIView):
    permission_classes = [IsAccountantOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            customer = CreditCustomer.objects.get(pk=pk)
        except CreditCustomer.DoesNotExist:
            return Response({"error": "Credit customer not found."}, status=status.HTTP_404_NOT_FOUND)

        amount = Decimal(str(request.data.get('amount', '0.00')))
        payment_method = request.data.get('payment_method', 'BANK_TRANSFER')
        ref_number = request.data.get('reference_number', '')

        if amount <= 0:
            return Response({"error": "Payment amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        if amount > customer.current_balance:
            return Response({"error": f"Payment of KES {amount} exceeds current outstanding balance of KES {customer.current_balance}."}, status=status.HTTP_400_BAD_REQUEST)

        payment = CreditPayment.objects.create(
            customer=customer,
            amount=amount,
            payment_method=payment_method,
            reference_number=ref_number,
            recorded_by=request.user
        )

        customer.current_balance -= amount
        customer.save()

        return Response(CreditPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

class RecordCreditSaleView(APIView):
    permission_classes = [IsAccountantOrAdmin]

    @transaction.atomic
    def post(self, request, pk):
        try:
            customer = CreditCustomer.objects.select_for_update().get(pk=pk)
        except CreditCustomer.DoesNotExist:
            return Response({"error": "Credit customer not found."}, status=status.HTTP_404_NOT_FOUND)

        if not customer.is_active:
            return Response({"error": "This customer's credit account is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        amount = Decimal(str(request.data.get('amount', '0.00')))
        if amount <= 0:
            return Response({"error": "Sale amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        if customer.current_balance + amount > customer.credit_limit:
            return Response({
                "error": f"Sale of KES {amount} would exceed credit limit. Available credit: KES {customer.available_credit}."
            }, status=status.HTTP_400_BAD_REQUEST)

        shift_id = request.data.get('shift')
        shift = None
        if shift_id:
            try:
                shift = Shift.objects.get(pk=shift_id)
            except Shift.DoesNotExist:
                return Response({"error": "Shift not found."}, status=status.HTTP_404_NOT_FOUND)

        sale = CreditSale.objects.create(
            customer=customer,
            shift=shift,
            amount=amount,
            description=request.data.get('description', ''),
            recorded_by=request.user
        )

        customer.current_balance += amount
        customer.save()

        return Response(CreditSaleSerializer(sale).data, status=status.HTTP_201_CREATED)