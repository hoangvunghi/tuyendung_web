from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from .serializers import UserSerializer

UserAccount = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'User registered successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Registration failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful',
            'status': status.HTTP_200_OK,
            'data': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Invalid credentials',
        'status': status.HTTP_400_BAD_REQUEST
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh = request.data.get('refresh')
    if refresh:
        refresh_token = RefreshToken(refresh)
        return Response({
            'message': 'Token refreshed successfully',
            'status': status.HTTP_200_OK,
            'data': {
                'access': str(refresh_token.access_token),
            }
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Refresh token is required',
        'status': status.HTTP_400_BAD_REQUEST
    }, status=status.HTTP_400_BAD_REQUEST)
