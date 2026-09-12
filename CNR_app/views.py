from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairSerializer, TokenObtainPairView
from CNR_app.models import User
from CNR_app.serializers import CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer
from CNR_app.permissions import IsSuperAdmin, IsManagerOrAdmin