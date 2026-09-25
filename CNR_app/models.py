from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        MANAGER = 'MANAGER', 'Station Manager'
        ATTENDANT = 'ATTENDANT', 'Pump Attendant'
        ACCOUNTANT = 'ACCOUNTANT', 'Accountant'
        INVENTORY_OFFICER = 'INVENTORY_OFFICER', 'Inventory Officer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ATTENDANT)
    phone_number = models.CharField(max_length=10, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

class Station(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class FuelProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50) 
    code = models.CharField(max_length=10, unique=True)  
    current_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.name} @ KSh {self.current_price}"

class FuelPriceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(FuelProduct, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateTimeField(default=timezone.now)
    effective_to = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-effective_from']

class Tank(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='tanks')
    product = models.ForeignKey(FuelProduct, on_delete=models.PROTECT, related_name='tanks')
    name = models.CharField(max_length=50)  
    capacity_liters = models.DecimalField(max_digits=12, decimal_places=2)
    current_capacity_liters = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.product.name}) - {self.current_capacity_liters}L"

class Pump(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='pumps')
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.station.name} - {self.name}"

class Nozzle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pump = models.ForeignKey(Pump, on_delete=models.CASCADE, related_name='nozzles')
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE, related_name='nozzles')
    product = models.ForeignKey(FuelProduct, on_delete=models.PROTECT)
    name = models.CharField(max_length=20)  # e.g., Nozzle 1 (Petrol)

    def __str__(self):
        return f"{self.pump.name} - {self.name} ({self.product.name})"

class Shift(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        ACTIVE = 'ACTIVE', 'Active'
        PENDING_RECONCILIATION = 'PENDING_RECONCILIATION', 'Pending Reconciliation'
        RECONCILED = 'RECONCILED', 'Reconciled'
        CLOSED = 'CLOSED', 'Closed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='shifts')
    attendant = models.ForeignKey(User, on_delete=models.PROTECT, related_name='shifts')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    opening_cash_float = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Shift {self.id} - {self.attendant.email} ({self.status})"

class PumpReading(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='pump_readings')
    nozzle = models.ForeignKey(Nozzle, on_delete=models.PROTECT)
    opening_meter = models.DecimalField(max_digits=12, decimal_places=2)
    closing_meter = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def liters_sold(self):
        if self.closing_meter is not None:
            return self.closing_meter - self.opening_meter
        return Decimal('0.00')

    @property
    def expected_revenue(self):
        return self.liters_sold * self.unit_price

class Reconciliation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.OneToOneField(Shift, on_delete=models.CASCADE, related_name='reconciliation')
    
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    actual_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_mpesa = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_card = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    actual_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    variance = models.DecimalField(max_digits=12, decimal_places=2)  # Actual Total - Expected
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reconciliations')
    created_at = models.DateTimeField(auto_now_add=True)

class DipReading(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE, related_name='dip_readings')
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    dip_depth_cm = models.DecimalField(max_digits=8, decimal_places=2)
    physical_liters = models.DecimalField(max_digits=12, decimal_places=2)
    expected_liters = models.DecimalField(max_digits=12, decimal_places=2)
    variance_liters = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

class Delivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tank = models.ForeignKey(Tank, on_delete=models.CASCADE, related_name='deliveries')
    supplier = models.CharField(max_length=100)
    invoice_number = models.CharField(max_length=50)
    quantity_liters = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT)
    received_at = models.DateTimeField(default=timezone.now)


class CreditCustomer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def available_credit(self):
        return self.credit_limit - self.current_balance

    def __str__(self):
        return f"{self.name} ({self.company_name or 'Individual'})"

class CreditSale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(CreditCustomer, on_delete=models.PROTECT, related_name='credit_sales')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_sales')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_credit_sales')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - KES {self.amount} sale"
    
class CreditPayment(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        MPESA = 'MPESA', 'M-Pesa'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(CreditCustomer, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    reference_number = models.CharField(max_length=100, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_credit_payments')
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - KES {self.amount} ({self.payment_method})"

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

class MpesaTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        TIMEOUT = 'TIMEOUT', 'Timeout'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, blank=True, related_name='mpesa_transactions')
    credit_customer = models.ForeignKey(CreditCustomer, on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.phone_number} - KES {self.amount} ({self.status})"