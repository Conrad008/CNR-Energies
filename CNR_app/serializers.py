from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from CNR_app.models import User

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