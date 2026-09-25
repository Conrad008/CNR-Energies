from datetime import timedelta
from django.db.models import Sum, Count, Q
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
from CNR_app.models import Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle, Shift, PumpReading, Reconciliation, DipReading, Delivery, PumpReading, CreditCustomer, CreditPayment, CreditSale, AuditLog, MpesaTransaction
from CNR_app.serializers import (
    StationSerializer, FuelProductSerializer, FuelPriceHistorySerializer,
    TankSerializer, PumpSerializer, NozzleSerializer, ShiftSerializer, PumpReadingSerializer, 
    ReconciliationSerializer, DipReadingSerializer, DeliverySerializer,CreditCustomerSerializer, 
    CreditPaymentSerializer,AuditLogSerializer,MpesaTransactionSerializer
)
from CNR_app.permissions import IsManagerOrAdmin, IsSuperAdmin, IsAccountantOrAdmin, IsInventoryOfficerOrAdmin
from decimal import Decimal
from CNR_app.services.mpesa import stk_push, MpesaError
import re



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
            customer = CreditCustomer.objects.select_for_update().get(pk=pk)
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

class ExecutiveDashboardAnalyticsView(APIView):
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        reconciliations = Reconciliation.objects.filter(shift__start_time__gte=start_date)

        financial = reconciliations.aggregate(
            total_expected=Sum('expected_revenue'),
            total_cash=Sum('actual_cash'),
            total_mpesa=Sum('actual_mpesa'),
            total_card=Sum('actual_card'),
            total_credit=Sum('actual_credit'),
            total_variance=Sum('variance')
        )

        total_shifts = Shift.objects.filter(start_time__gte=start_date).count()
        completed_shifts = Shift.objects.filter(start_time__gte=start_date, status=Shift.Status.RECONCILED).count()

        return Response({
            "period_days": days,
            "total_shifts_logged": total_shifts,
            "completed_reconciled_shifts": completed_shifts,
            "revenue_summary": {
                "total_expected_revenue": financial['total_expected'] or Decimal('0.00'),
                "total_actual_collected": (
                    (financial['total_cash'] or Decimal('0.00')) +
                    (financial['total_mpesa'] or Decimal('0.00')) +
                    (financial['total_card'] or Decimal('0.00')) +
                    (financial['total_credit'] or Decimal('0.00'))
                ),
                "total_variance": financial['total_variance'] or Decimal('0.00')
            },
            "payment_channel_breakdown": {
                "cash": financial['total_cash'] or Decimal('0.00'),
                "mpesa": financial['total_mpesa'] or Decimal('0.00'),
                "card": financial['total_card'] or Decimal('0.00'),
                "b2b_credit": financial['total_credit'] or Decimal('0.00')
            }
        }, status=status.HTTP_200_OK)

class StockSummaryAnalyticsView(APIView):
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        tanks = Tank.objects.all()
        summary = []

        for tank in tanks:
            fill_percentage = round((tank.current_capacity_liters / tank.capacity_liters) * 100, 2) if tank.capacity_liters > 0 else 0
            summary.append({
                "tank_id": tank.id,
                "tank_name": tank.name,
                "station_name": tank.station.name,
                "fuel_product": tank.product.name,
                "capacity_liters": tank.capacity_liters,
                "current_capacity_liters": tank.current_capacity_liters,
                "remaining_ullage_liters": tank.capacity_liters - tank.current_capacity_liters,
                "fill_percentage": fill_percentage,
                "is_low_stock": fill_percentage < 20.0
            })

        return Response(summary, status=status.HTTP_200_OK)

class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperAdmin]


class InitiateSTKPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_phone = str(request.data.get('phone_number', ''))
        digits = re.sub(r'\D', '', raw_phone)
        if digits.startswith('0'):
            digits = '254' + digits[1:]
        elif digits.startswith('7') or digits.startswith('1'):
            digits = '254' + digits
        if not re.fullmatch(r'254(7|1)\d{8}', digits):
            return Response({"error": "Enter a valid Kenyan phone number, e.g. 0712345678."}, status=status.HTTP_400_BAD_REQUEST)

        amount = request.data.get('amount')
        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"error": "Please input a valid amount."}, status=status.HTTP_400_BAD_REQUEST)

        shift_id = request.data.get('shift')
        customer_id = request.data.get('credit_customer')
        reference = request.data.get('reference', 'CNR Energies')

        try:
            result = stk_push(digits, amount, reference, "Fuel payment")
        except MpesaError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        txn = MpesaTransaction.objects.create(
            shift_id=shift_id if shift_id else None,
            credit_customer_id=customer_id if customer_id else None,
            phone_number=digits,
            amount=amount,
            checkout_request_id=result['CheckoutRequestID'],
            merchant_request_id=result.get('MerchantRequestID', ''),
            initiated_by=request.user,
        )
        return Response(MpesaTransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class MpesaCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        body = request.data.get('Body', {}).get('stkCallback', {})
        checkout_id = body.get('CheckoutRequestID')
        result_code = body.get('ResultCode')
        result_desc = body.get('ResultDesc', '')

        try:
            txn = MpesaTransaction.objects.get(checkout_request_id=checkout_id)
        except MpesaTransaction.DoesNotExist:
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        txn.result_desc = result_desc
        txn.completed_at = timezone.now()

        if result_code == 0:
            items = {i['Name']: i.get('Value') for i in body.get('CallbackMetadata', {}).get('Item', [])}
            txn.status = MpesaTransaction.Status.SUCCESS
            txn.mpesa_receipt_number = items.get('MpesaReceiptNumber', '')
        elif result_code == 1032:
            txn.status = MpesaTransaction.Status.TIMEOUT
        else:
            txn.status = MpesaTransaction.Status.FAILED

        txn.save()
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})
