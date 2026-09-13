from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from CNR_app.models import User, Station, FuelProduct, FuelPriceHistory, Tank, Pump, Nozzle, Shift, PumpReading, Reconciliation

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Include user details in the login response body
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'role': self.user.role,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined', 'role', 'is_active']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number']

    def validate_role(self, value):
        request = self.context.get('request')
        if (
            value == User.Role.SUPER_ADMIN
            and not (request and request.user.is_authenticated and request.user.role == User.Role.SUPER_ADMIN)
        ):
            raise serializers.ValidationError("You do not have permission to assign this role.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = '__all__'

class FuelPriceHistorySerializer(serializers.ModelSerializer):
    updated_by_email = serializers.ReadOnlyField(source='updated_by.email')

    class Meta:
        model = FuelPriceHistory
        fields = ['id', 'product', 'price', 'effective_from', 'effective_to', 'updated_by', 'updated_by_email']
        read_only_fields = ['id', 'effective_from', 'updated_by']

class FuelProductSerializer(serializers.ModelSerializer):
    price_history = FuelPriceHistorySerializer(many=True, read_only=True)

    class Meta:
        model = FuelProduct
        fields = ['id', 'name', 'code', 'current_price', 'price_history']

class TankSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = Tank
        fields = ['id', 'station', 'product', 'product_name', 'name', 'capacity_liters', 'current_capacity_liters']

class NozzleSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = Nozzle
        fields = ['id', 'pump', 'tank', 'product', 'product_name', 'name']

class PumpSerializer(serializers.ModelSerializer):
    nozzles = NozzleSerializer(many=True, read_only=True)

    class Meta:
        model = Pump
        fields = ['id', 'station', 'name', 'nozzles']

class PumpReadingSerializer(serializers.ModelSerializer):
    nozzle_name = serializers.ReadOnlyField(source='nozzle.name')
    product_name = serializers.ReadOnlyField(source='nozzle.product.name')
    liters_sold = serializers.ReadOnlyField()
    expected_revenue = serializers.ReadOnlyField()

    class Meta:
        model = PumpReading
        fields = [
            'id', 'shift', 'nozzle', 'nozzle_name', 'product_name',
            'opening_meter', 'closing_meter', 'unit_price',
            'liters_sold', 'expected_revenue'
        ]
        read_only_fields = ['id', 'unit_price']

class ShiftSerializer(serializers.ModelSerializer):
    attendant_email = serializers.ReadOnlyField(source='attendant.email')
    pump_readings = PumpReadingSerializer(many=True, read_only=True)

    class Meta:
        model = Shift
        fields = [
            'id', 'station', 'attendant', 'attendant_email', 'status',
            'opening_cash_float', 'start_time', 'end_time', 'pump_readings'
        ]
        read_only_fields = ['id', 'attendant', 'status', 'start_time', 'end_time']