from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import TypeService, PackageEntity, PackageCampaign
from .serializers import TypeServiceSerializer, PackageSerializer, PackageCampaignSerializer
from enterprises.models import CampaignEntity
from base.permissions import IsServiceProvider, IsEnterpriseOwner, IsSubscriptionOwner

# Create your views here.

# TypeService CRUD
@api_view(['GET'])
@permission_classes([AllowAny])
def get_type_services(request):
    type_services = TypeService.objects.filter(status='active')
    serializer = TypeServiceSerializer(type_services, many=True)
    return Response({
        'message': 'Type services retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_type_service_detail(request, pk):
    type_service = get_object_or_404(TypeService, pk=pk)
    serializer = TypeServiceSerializer(type_service)
    return Response({
        'message': 'Type service details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsServiceProvider])
def create_type_service(request):
    serializer = TypeServiceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Type service created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Type service creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsServiceProvider])
def update_type_service(request, pk):
    type_service = get_object_or_404(TypeService, pk=pk)
    serializer = TypeServiceSerializer(type_service, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Type service updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Type service update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# Package CRUD
@api_view(['GET'])
@permission_classes([AllowAny])
def get_packages(request):
    type_service_id = request.query_params.get('type_service_id')
    if type_service_id:
        packages = PackageEntity.objects.filter(type_service_id=type_service_id, status='active')
    else:
        packages = PackageEntity.objects.filter(status='active')
    serializer = PackageSerializer(packages, many=True)
    return Response({
        'message': 'Packages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsServiceProvider])
def create_package(request):
    serializer = PackageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Package created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Package creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# PackageCampaign CRUD
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_campaign_packages(request):
    campaign_id = request.query_params.get('campaign_id')
    if campaign_id:
        campaign = get_object_or_404(CampaignEntity, id=campaign_id, enterprise__user=request.user)
        campaign_packages = PackageCampaign.objects.filter(campaign=campaign)
    else:
        campaign_packages = PackageCampaign.objects.filter(campaign__enterprise__user=request.user)
    serializer = PackageCampaignSerializer(campaign_packages, many=True)
    return Response({
        'message': 'Campaign packages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe_package(request):
    serializer = PackageCampaignSerializer(data=request.data)
    if serializer.is_valid():
        # Kiểm tra quyền với campaign
        campaign = get_object_or_404(CampaignEntity, 
                                   id=request.data.get('campaign'),
                                   enterprise__user=request.user)
        serializer.save()
        return Response({
            'message': 'Package subscribed successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Package subscription failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)
