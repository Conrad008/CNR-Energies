from django.contrib import admin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from CNR_app.models import (
    User, Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle,
    Shift, PumpReading, Reconciliation, DipReading, Delivery,
    CreditCustomer, CreditPayment, CreditSale, AuditLog, MpesaTransaction
)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Role & permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2', 'role')}),
    )

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'created_at')
    search_fields = ('name', 'location')

@admin.register(FuelProduct)
class FuelProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'current_price')

@admin.register(FuelPriceHistory)
class FuelPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'effective_from', 'effective_to', 'updated_by')
    list_filter = ('product',)

@admin.register(Tank)
class TankAdmin(admin.ModelAdmin):
    list_display = ('name', 'station', 'product', 'capacity_liters', 'current_capacity_liters')
    list_filter = ('station', 'product')

@admin.register(Pump)
class PumpAdmin(admin.ModelAdmin):
    list_display = ('name', 'station')
    list_filter = ('station',)

@admin.register(Nozzle)
class NozzleAdmin(admin.ModelAdmin):
    list_display = ('name', 'pump', 'tank', 'product')
    list_filter = ('pump__station', 'product')

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('id', 'station', 'attendant', 'status', 'start_time', 'end_time')
    list_filter = ('status', 'station')

@admin.register(PumpReading)
class PumpReadingAdmin(admin.ModelAdmin):
    list_display = ('shift', 'nozzle', 'opening_meter', 'closing_meter', 'unit_price')

@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = ('shift', 'expected_revenue', 'variance', 'is_approved', 'created_at')

@admin.register(DipReading)
class DipReadingAdmin(admin.ModelAdmin):
    list_display = ('tank', 'physical_liters', 'expected_liters', 'variance_liters', 'recorded_at')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('tank', 'supplier', 'invoice_number', 'quantity_liters', 'total_cost', 'received_at')

@admin.register(CreditCustomer)
class CreditCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_name', 'credit_limit', 'current_balance', 'is_active')
    search_fields = ('name', 'company_name', 'phone')

@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'payment_method', 'payment_date')

@admin.register(CreditSale)
class CreditSaleAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'shift', 'created_at')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'timestamp')
    list_filter = ('action', 'model_name')

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'amount', 'status', 'checkout_request_id', 'created_at')
    list_filter = ('status',)