from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import TypeService, PackageEntity, PackageCampaign
from .serializers import TypeServiceSerializer, PackageSerializer, PackageCampaignSerializer
from enterprises.models import CampaignEntity
from base.permissions import IsServiceProvider, IsEnterpriseOwner, IsSubscriptionOwner, AdminAccessPermission
from rest_framework.permissions import IsAdminUser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.utils import create_permission_class_with_admin_override

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrServiceProvider = create_permission_class_with_admin_override(IsServiceProvider)
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)
AdminOrSubscriptionOwner = create_permission_class_with_admin_override(IsSubscriptionOwner)

# Create your views here.

# TypeService CRUD
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách các loại dịch vụ đang hoạt động",
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                'description': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            }
                        )
                    )
                }
            )
        )
    }
)
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

@swagger_auto_schema(
    method='get',
    operation_description="Lấy chi tiết loại dịch vụ theo ID",
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Type service not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    }
)
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

@swagger_auto_schema(
    method='post',
    operation_description="Tạo loại dịch vụ mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'description'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên loại dịch vụ"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'status': openapi.Schema(type=openapi.TYPE_STRING, description="Trạng thái", enum=['active', 'inactive']),
        }
    ),
    responses={
        201: openapi.Response(
            description="Type service created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminOrServiceProvider])
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

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật loại dịch vụ",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên loại dịch vụ"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'status': openapi.Schema(type=openapi.TYPE_STRING, description="Trạng thái", enum=['active', 'inactive']),
        }
    ),
    responses={
        200: openapi.Response(
            description="Type service updated successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, AdminOrServiceProvider])
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
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách gói dịch vụ",
    manual_parameters=[
        openapi.Parameter(
            'type_service_id', 
            openapi.IN_QUERY, 
            description="ID của loại dịch vụ để lọc", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    }
)
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

@swagger_auto_schema(
    method='post',
    operation_description="Tạo gói dịch vụ mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'type_service', 'price', 'days'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên gói dịch vụ"),
            'type_service': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của loại dịch vụ"),
            'price': openapi.Schema(type=openapi.TYPE_NUMBER, description="Giá gói dịch vụ"),
            'days': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ngày của gói dịch vụ"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'status': openapi.Schema(type=openapi.TYPE_STRING, description="Trạng thái", enum=['active', 'inactive']),
        }
    ),
    responses={
        201: openapi.Response(
            description="Package created successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminOrServiceProvider])
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
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách gói dịch vụ của chiến dịch",
    manual_parameters=[
        openapi.Parameter(
            'campaign_id', 
            openapi.IN_QUERY, 
            description="ID của chiến dịch để lọc", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def get_campaign_packages(request):
    print(request.user)
    print(request.user.is_staff)
    campaign_id = request.query_params.get('campaign_id')
    print(campaign_id)

    if campaign_id:
        campaign_packages = PackageCampaign.objects.filter(campaign_id=campaign_id)
    else:
        enterprise_campaigns = CampaignEntity.objects.filter(enterprise__user=request.user)
        campaign_packages = PackageCampaign.objects.filter(campaign__in=enterprise_campaigns)
    print(campaign_packages)
    print(PackageCampaign.objects.all().values('id'))
    serializer = PackageCampaignSerializer(campaign_packages, many=True)
    return Response({
        'message': 'Campaign packages retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    method='post',
    operation_description="Đăng ký gói dịch vụ cho chiến dịch",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['package', 'campaign'],
        properties={
            'package': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của gói dịch vụ"),
            'campaign': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của chiến dịch"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Package subscribed successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: openapi.Response(
            description="Bad request",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
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
