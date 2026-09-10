from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.utils import timezone

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