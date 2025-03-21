from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import EnterpriseEntity, CampaignEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from .serializers import (
    EnterpriseSerializer, CampaignSerializer, PostSerializer,
    FieldSerializer, PositionSerializer, CriteriaSerializer
)
from profiles.models import Cv
from profiles.serializers import CvSerializer, CvStatusSerializer
from base.permissions import (
    IsEnterpriseOwner, IsPostOwner, IsCampaignOwner,
    IsFieldManager, IsPositionManager, IsCriteriaOwner,
    AdminAccessPermission
)
from base.utils import create_permission_class_with_admin_override
from notifications.services import NotificationService
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)
AdminOrPostOwner = create_permission_class_with_admin_override(IsPostOwner)
AdminOrCampaignOwner = create_permission_class_with_admin_override(IsCampaignOwner)
AdminOrFieldManager = create_permission_class_with_admin_override(IsFieldManager)
AdminOrPositionManager = create_permission_class_with_admin_override(IsPositionManager)
AdminOrCriteriaOwner = create_permission_class_with_admin_override(IsCriteriaOwner)

# Create your views here.

# Enterprise CRUD
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách doanh nghiệp đang hoạt động",
    manual_parameters=[
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng doanh nghiệp mỗi trang", 
            type=openapi.TYPE_INTEGER
        ),
        openapi.Parameter(
            'sort_by', openapi.IN_QUERY, 
            description="Trường sắp xếp (ví dụ: company_name, created_at)", 
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'sort_order', openapi.IN_QUERY, 
            description="Thứ tự sắp xếp (asc/desc)", 
            type=openapi.TYPE_STRING,
            enum=['asc', 'desc']
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'company_name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'address': openapi.Schema(type=openapi.TYPE_STRING),
                                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        'email_company': openapi.Schema(type=openapi.TYPE_STRING),
                                        'field_of_activity': openapi.Schema(type=openapi.TYPE_STRING),
                                        'link_web_site': openapi.Schema(type=openapi.TYPE_STRING),
                                        'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                        'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'scale': openapi.Schema(type=openapi.TYPE_STRING),
                                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_enterprises(request):
    enterprises = EnterpriseEntity.objects.filter(is_active=True)
    
    # Sắp xếp
    sort_by = request.query_params.get('sort_by', 'company_name')
    sort_order = request.query_params.get('sort_order', 'asc')
    
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    enterprises = enterprises.order_by(sort_by)
    
    # Khởi tạo paginator
    paginator = CustomPagination()
    paginated_enterprises = paginator.paginate_queryset(enterprises, request)
    
    serializer = EnterpriseSerializer(paginated_enterprises, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy chi tiết doanh nghiệp theo ID",
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
                            'company_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'address': openapi.Schema(type=openapi.TYPE_STRING),
                            'business_certificate': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'email_company': openapi.Schema(type=openapi.TYPE_STRING),
                            'field_of_activity': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'link_web_site': openapi.Schema(type=openapi.TYPE_STRING),
                            'logo': openapi.Schema(type=openapi.TYPE_STRING),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                            'scale': openapi.Schema(type=openapi.TYPE_STRING),
                            'tax': openapi.Schema(type=openapi.TYPE_STRING),
                            'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'city': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Enterprise not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_enterprise_detail(request, pk):
    enterprise = get_object_or_404(EnterpriseEntity, pk=pk, is_active=True)
    serializer = EnterpriseSerializer(enterprise)
    return Response({
        'message': 'Enterprise details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    method='post',
    operation_description="Tạo doanh nghiệp mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['company_name', 'address', 'business_certificate', 'field_of_activity'],
        properties={
            'company_name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên công ty"),
            'address': openapi.Schema(type=openapi.TYPE_STRING, description="Địa chỉ"),
            'business_certificate': openapi.Schema(type=openapi.TYPE_STRING, description="Giấy phép kinh doanh"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'email_company': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Email công ty"),
            'field_of_activity': openapi.Schema(type=openapi.TYPE_STRING, description="Lĩnh vực hoạt động"),
            'link_web_site': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI, description="Website"),
            'logo': openapi.Schema(type=openapi.TYPE_FILE, description="Logo"),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Số điện thoại"),
            'scale': openapi.Schema(type=openapi.TYPE_STRING, description="Quy mô"),
            'tax': openapi.Schema(type=openapi.TYPE_STRING, description="Mã số thuế"),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description="Thành phố"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Enterprise created successfully",
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
            description="Invalid input",
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
@permission_classes([IsAuthenticated, AdminAccessPermission])
def create_enterprise(request):
    serializer = EnterpriseSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'Enterprise created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Enterprise creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin doanh nghiệp",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'company_name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên doanh nghiệp"),
            'address': openapi.Schema(type=openapi.TYPE_STRING, description="Địa chỉ"),
            'business_certificate': openapi.Schema(type=openapi.TYPE_STRING, description="Giấy phép kinh doanh"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'email_company': openapi.Schema(type=openapi.TYPE_STRING, description="Email công ty"),
            'field_of_activity': openapi.Schema(type=openapi.TYPE_STRING, description="Lĩnh vực hoạt động"),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Trạng thái hoạt động"),
            'link_web_site': openapi.Schema(type=openapi.TYPE_STRING, description="Đường link website"),
            'logo': openapi.Schema(type=openapi.TYPE_STRING, description="Logo"),
            'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description="Số điện thoại"),
            'scale': openapi.Schema(type=openapi.TYPE_STRING, description="Quy mô"),
            'tax': openapi.Schema(type=openapi.TYPE_STRING, description="Mã số thuế"),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description="Thành phố")
        }
    ),
    responses={
        200: openapi.Response(
            description="Enterprise updated successfully",
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
            description="Invalid input",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="Enterprise not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def update_enterprise(request):
    enterprise = get_object_or_404(EnterpriseEntity, user=request.user)
    serializer = EnterpriseSerializer(enterprise, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Enterprise updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Enterprise update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa (vô hiệu hóa) doanh nghiệp",
    responses={
        200: openapi.Response(
            description="Enterprise deleted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Enterprise not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def delete_enterprise(request):
    enterprise = get_object_or_404(EnterpriseEntity, user=request.user)
    enterprise.delete()
    return Response({
        'message': 'Enterprise deleted successfully',
        'status': status.HTTP_200_OK
    })

# Campaign CRUD
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách các chiến dịch tuyển dụng",
    manual_parameters=[
        openapi.Parameter(
            'enterprise_id', 
            openapi.IN_QUERY, 
            description="ID của doanh nghiệp để lọc chiến dịch", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page', 
            openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', 
            openapi.IN_QUERY, 
            description="Số lượng chiến dịch mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'sort_by', 
            openapi.IN_QUERY, 
            description="Trường sắp xếp", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'sort_order', 
            openapi.IN_QUERY, 
            description="Thứ tự sắp xếp (asc/desc)", 
            type=openapi.TYPE_STRING,
            enum=['asc', 'desc'],
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'enterprise': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrCampaignOwner])
def get_campaigns(request):
    campaigns = CampaignEntity.objects.filter(enterprise__user=request.user)
    paginator = CustomPagination()
    paginated_campaigns = paginator.paginate_queryset(campaigns, request)
    serializer = CampaignSerializer(paginated_campaigns, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo chiến dịch tuyển dụng mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name', 'enterprise'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên chiến dịch"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả chiến dịch"),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Trạng thái hoạt động của chiến dịch"),
            'enterprise': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của doanh nghiệp"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Campaign created successfully",
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
        ),
        404: openapi.Response(
            description="Enterprise not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def create_campaign(request):
    serializer = CampaignSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(enterprise=request.user.enterprise)
        return Response({
            'message': 'Campaign created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Campaign creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# Post CRUD
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm",
    manual_parameters=[
        openapi.Parameter(
            'campaign_id', 
            openapi.IN_QUERY, 
            description="ID của chiến dịch để lọc bài đăng", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page', 
            openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', 
            openapi.IN_QUERY, 
            description="Số lượng bài đăng mỗi trang", 
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_OBJECT)
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrPostOwner])
def get_posts(request):
    campaigns = CampaignEntity.objects.filter(enterprise__user=request.user)
    campaign_id = request.query_params.get('campaign_id')
    if campaign_id:
        posts = PostEntity.objects.filter(campaign__in=campaigns, campaign_id=campaign_id)
    else:
        posts = PostEntity.objects.filter(campaign__in=campaigns)
    
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostSerializer(paginated_posts, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo bài đăng việc làm mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'campaign', 'position', 'city', 'experience', 'type_working'],
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Tiêu đề bài đăng"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả công việc"),
            'required': openapi.Schema(type=openapi.TYPE_STRING, description="Yêu cầu công việc"),
            'benefit': openapi.Schema(type=openapi.TYPE_STRING, description="Quyền lợi"),
            'experience': openapi.Schema(type=openapi.TYPE_STRING, description="Kinh nghiệm yêu cầu"),
            'type_working': openapi.Schema(type=openapi.TYPE_STRING, description="Loại hình công việc"),
            'salary_range': openapi.Schema(type=openapi.TYPE_STRING, description="Khoảng lương"),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số lượng cần tuyển"),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description="Thành phố"),
            'position': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của vị trí"),
            'campaign': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của chiến dịch"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Post created successfully",
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
        ),
        404: openapi.Response(
            description="Campaign not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def create_post(request):
    serializer = PostSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(campaign=request.user.enterprise.campaign_set.get(id=request.data['campaign']))
        return Response({
            'message': 'Post created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Post creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# Field Management (Admin only)
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách lĩnh vực hoạt động",
    manual_parameters=[
        openapi.Parameter(
            'page', 
            openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', 
            openapi.IN_QUERY, 
            description="Số lượng lĩnh vực mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'sort_by', 
            openapi.IN_QUERY, 
            description="Trường sắp xếp", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'sort_order', 
            openapi.IN_QUERY, 
            description="Thứ tự sắp xếp (asc/desc)", 
            type=openapi.TYPE_STRING,
            enum=['asc', 'desc'],
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_fields(request):
    fields = FieldEntity.objects.filter(status='active')
    
    # Sắp xếp
    sort_by = request.query_params.get('sort_by', 'name')
    sort_order = request.query_params.get('sort_order', 'asc')
    
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    fields = fields.order_by(sort_by)
    
    # Phân trang
    paginator = CustomPagination()
    paginated_fields = paginator.paginate_queryset(fields, request)
    
    serializer = FieldSerializer(paginated_fields, many=True)
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo lĩnh vực hoạt động mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['name'],
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên lĩnh vực"),
            'status': openapi.Schema(type=openapi.TYPE_STRING, description="Trạng thái", enum=['active', 'inactive']),
        }
    ),
    responses={
        201: openapi.Response(
            description="Field created successfully",
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
@permission_classes([IsAuthenticated, AdminOrFieldManager])
def create_field(request):
    serializer = FieldSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Field created successfully',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Field creation failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# Enterprise Search & Filter
@swagger_auto_schema(
    method='get',
    operation_description="Tìm kiếm và lọc doanh nghiệp",
    manual_parameters=[
        openapi.Parameter(
            'q', openapi.IN_QUERY, 
            description="Từ khóa tìm kiếm", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'city', openapi.IN_QUERY, 
            description="Thành phố", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'field', openapi.IN_QUERY, 
            description="Lĩnh vực hoạt động", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'scale', openapi.IN_QUERY, 
            description="Quy mô doanh nghiệp", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng doanh nghiệp mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'sort_by', openapi.IN_QUERY, 
            description="Trường sắp xếp", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'sort_order', openapi.IN_QUERY, 
            description="Thứ tự sắp xếp (asc/desc)", 
            type=openapi.TYPE_STRING,
            enum=['asc', 'desc'],
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_OBJECT)
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_enterprises(request):
    query = request.query_params.get('q', '')
    city = request.query_params.get('city', '')
    field = request.query_params.get('field', '')
    scale = request.query_params.get('scale', '')
    
    enterprises = EnterpriseEntity.objects.filter(is_active=True)
    
    if query:
        enterprises = enterprises.filter(
            Q(company_name__icontains=query) |
            Q(description__icontains=query) |
            Q(field_of_activity__icontains=query)
        )
    
    if city:
        enterprises = enterprises.filter(city__iexact=city)
    
    if field:
        enterprises = enterprises.filter(field_of_activity__icontains=field)
        
    if scale:
        enterprises = enterprises.filter(scale__iexact=scale)
    
    # Sắp xếp kết quả
    sort_by = request.query_params.get('sort_by', 'company_name')
    sort_order = request.query_params.get('sort_order', 'asc')
    
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    enterprises = enterprises.order_by(sort_by)
    
    paginator = CustomPagination()
    paginated_enterprises = paginator.paginate_queryset(enterprises, request)
    
    serializer = EnterpriseSerializer(paginated_enterprises, many=True)
    return paginator.get_paginated_response(serializer.data)

# Post Search & Filter
@swagger_auto_schema(
    method='get',
    operation_description="""
    Tìm kiếm và lọc bài đăng việc làm.
    API này cho phép tìm kiếm bài đăng theo từ khóa, vị trí địa lý, vị trí công việc, kinh nghiệm, loại công việc và khoảng lương.
    Kết quả được phân trang và có thể sắp xếp theo các tiêu chí khác nhau.
    """,
    manual_parameters=[
        openapi.Parameter(
            'q', openapi.IN_QUERY, 
            description="Từ khóa tìm kiếm (tìm trong tiêu đề, mô tả, yêu cầu, tên công ty)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'city', openapi.IN_QUERY, 
            description="Thành phố", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'position', openapi.IN_QUERY, 
            description="Vị trí công việc", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'experience', openapi.IN_QUERY, 
            description="Kinh nghiệm (ví dụ: 'Không yêu cầu', '1-2 năm', '3-5 năm')", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'type_working', openapi.IN_QUERY, 
            description="Loại công việc (ví dụ: 'Full-time', 'Part-time', 'Remote')", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'salary_min', openapi.IN_QUERY, 
            description="Lương tối thiểu", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'salary_max', openapi.IN_QUERY, 
            description="Lương tối đa", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page', openapi.IN_QUERY, 
            description="Số trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'page_size', openapi.IN_QUERY, 
            description="Số lượng bài đăng mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'sort_by', openapi.IN_QUERY, 
            description="Trường sắp xếp (ví dụ: 'created_at', 'salary_range')", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'sort_order', openapi.IN_QUERY, 
            description="Thứ tự sắp xếp", 
            type=openapi.TYPE_STRING,
            enum=['asc', 'desc'],
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
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'links': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'next': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'previous': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                }
                            ),
                            'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'page_size': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'results': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                                        'description': openapi.Schema(type=openapi.TYPE_STRING),
                                        'required': openapi.Schema(type=openapi.TYPE_STRING),
                                        'benefit': openapi.Schema(type=openapi.TYPE_STRING),
                                        'experience': openapi.Schema(type=openapi.TYPE_STRING),
                                        'type_working': openapi.Schema(type=openapi.TYPE_STRING),
                                        'salary_range': openapi.Schema(type=openapi.TYPE_STRING),
                                        'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                                        'position': openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                        ),
                                        'campaign': openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                'enterprise': openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                        'company_name': openapi.Schema(type=openapi.TYPE_STRING),
                                                        'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                                    }
                                                ),
                                            }
                                        ),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    }
                                )
                            ),
                        }
                    )
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_posts(request):
    query = request.query_params.get('q', '')
    city = request.query_params.get('city', '')
    position = request.query_params.get('position', '')
    experience = request.query_params.get('experience', '')
    type_working = request.query_params.get('type_working', '')
    salary_min = request.query_params.get('salary_min')
    salary_max = request.query_params.get('salary_max')
    
    posts = PostEntity.objects.filter(campaign__is_active=True)
    
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(required__icontains=query) |
            Q(campaign__enterprise__company_name__icontains=query)
        )
    
    if city:
        posts = posts.filter(city__iexact=city)
        
    if position:
        posts = posts.filter(position__name__iexact=position)
        
    if experience:
        posts = posts.filter(experience__iexact=experience)
        
    if type_working:
        posts = posts.filter(type_working__iexact=type_working)
    
    if salary_min and salary_max:
        posts = posts.filter(
            Q(salary_range__regex=fr'^{salary_min}-{salary_max}$') |
            Q(salary_range__regex=fr'^(\d+)-(\d+)$',
              salary_range__gte=salary_min,
              salary_range__lte=salary_max)
        )
    
    # Sắp xếp kết quả
    sort_by = request.query_params.get('sort_by', '-created_at')  # Mặc định sắp xếp theo thời gian tạo mới nhất
    sort_order = request.query_params.get('sort_order', 'desc')
    
    if sort_order == 'desc' and not sort_by.startswith('-'):
        sort_by = f'-{sort_by}'
    posts = posts.order_by(sort_by)
    
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostSerializer(paginated_posts, many=True)
    return paginator.get_paginated_response(serializer.data)

# Get Distinct Values for Filters
@api_view(['GET'])
@permission_classes([AllowAny])
def get_filter_options(request):
    # Lấy danh sách các giá trị duy nhất cho các trường lọc
    cities = PostEntity.objects.values_list('city', flat=True).distinct()
    experiences = PostEntity.objects.values_list('experience', flat=True).distinct()
    type_workings = PostEntity.objects.values_list('type_working', flat=True).distinct()
    enterprise_scales = EnterpriseEntity.objects.values_list('scale', flat=True).distinct()
    fields = FieldEntity.objects.filter(status='active').values('id', 'name')
    positions = PositionEntity.objects.filter(status='active').values('id', 'name')
    
    return Response({
        'message': 'Filter options retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': {
            'cities': list(cities),
            'experiences': list(experiences),
            'type_workings': list(type_workings),
            'enterprise_scales': list(enterprise_scales),
            'fields': list(fields),
            'positions': list(positions)
        }
    })

# Get Recommended Posts
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommended_posts(request):
    try:
        criteria = CriteriaEntity.objects.get(user=request.user)
        
        posts = PostEntity.objects.filter(
            Q(city__iexact=criteria.city) |
            Q(experience__iexact=criteria.experience) |
            Q(type_working__iexact=criteria.type_working) |
            Q(campaign__enterprise__scale__iexact=criteria.scales) |
            Q(position=criteria.position) |
            Q(campaign__enterprise__field_of_activity__icontains=criteria.field.name)
        ).distinct()
        
        # Sắp xếp theo độ phù hợp (có thể thêm logic tính điểm phù hợp ở đây)
        posts = posts.order_by('-created_at')
        
        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)
        
        serializer = PostSerializer(paginated_posts, many=True)
        return paginator.get_paginated_response(serializer.data)
        
    except CriteriaEntity.DoesNotExist:
        return Response({
            'message': 'No criteria found for user',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

# Get Enterprise Statistics
@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin thống kê về doanh nghiệp",
    responses={
        200: openapi.Response(
            description="Enterprise statistics retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'total_campaigns': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số chiến dịch"),
                            'total_posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số bài đăng"),
                            'cv_statistics': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'pending': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số CV đang chờ xử lý"),
                                    'approved': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số CV đã duyệt"),
                                    'rejected': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số CV đã từ chối"),
                                }
                            )
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Enterprise not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def get_enterprise_stats(request, pk):
    """Lấy thống kê về doanh nghiệp: số lượng CV theo trạng thái, số chiến dịch, số bài đăng"""
    enterprise = get_object_or_404(EnterpriseEntity, pk=pk, user=request.user)
    
    # Tổng số chiến dịch
    total_campaigns = CampaignEntity.objects.filter(enterprise=enterprise).count()
    
    # Tổng số bài đăng
    total_posts = PostEntity.objects.filter(campaign__enterprise=enterprise).count()
    
    # Số lượng CV theo trạng thái
    cv_stats = {}
    posts = PostEntity.objects.filter(campaign__enterprise=enterprise)
    for status_choice in ['pending', 'approved', 'rejected']:
        cv_count = Cv.objects.filter(post__in=posts, status=status_choice).count()
        cv_stats[status_choice] = cv_count
    
    return Response({
        'message': 'Enterprise statistics retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': {
            'total_campaigns': total_campaigns,
            'total_posts': total_posts,
            'cv_statistics': cv_stats
        }
    })

# enterprises/views.py

@swagger_auto_schema(
    method='get',
    operation_description="Xem chi tiết CV đã nộp",
    responses={
        200: openapi.Response(
            description="CV retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'post': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'cv_file': openapi.Schema(type=openapi.TYPE_STRING),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def view_cv(request, cv_id):
    cv = get_object_or_404(Cv, id=cv_id)
    
    # Tạo notification khi CV được xem
    NotificationService.notify_cv_viewed(cv)
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV retrieved successfully',
        'data': serializer.data
    })

@swagger_auto_schema(
    method='post',
    operation_description="Cập nhật trạng thái CV (phê duyệt hoặc từ chối)",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['status'],
        properties={
            'status': openapi.Schema(
                type=openapi.TYPE_STRING, 
                description="Trạng thái CV",
                enum=['pending', 'approved', 'rejected']
            ),
        }
    ),
    responses={
        200: openapi.Response(
            description="CV status updated successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            description="Invalid status",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            description="CV not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def update_cv_status(request, cv_id):
    cv = get_object_or_404(Cv, id=cv_id)
    old_status = cv.status
    
    serializer = CvStatusSerializer(cv, data=request.data)
    if serializer.is_valid():
        cv = serializer.save()
        
        # Tạo notification khi status thay đổi
        NotificationService.notify_cv_status_changed(
            cv, 
            old_status, 
            cv.status
        )
        
        return Response({
            'message': 'CV status updated successfully',
            'data': serializer.data
        })

# enterprises/views.py
@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin chi tiết chiến dịch tuyển dụng",
    responses={
        200: openapi.Response(
            description="Campaign details retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            'enterprise': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Campaign not found",
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
def get_campaign_detail(request, pk):
    """Chi tiết chiến dịch"""
    campaign = get_object_or_404(CampaignEntity, pk=pk)
    serializer = CampaignSerializer(campaign)
    return Response({
        'message': 'Campaign details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin chiến dịch tuyển dụng",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'name': openapi.Schema(type=openapi.TYPE_STRING, description="Tên chiến dịch"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả chiến dịch"),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Trạng thái hoạt động của chiến dịch"),
            'enterprise': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của doanh nghiệp"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Campaign updated successfully",
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
        ),
        404: openapi.Response(
            description="Campaign not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def update_campaign(request, pk):
    campaign = get_object_or_404(CampaignEntity, pk=pk, enterprise__user=request.user)
    serializer = CampaignSerializer(campaign, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Campaign updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Campaign update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description="Vô hiệu hóa (xóa) chiến dịch tuyển dụng",
    responses={
        200: openapi.Response(
            description="Campaign deleted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Campaign not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def delete_campaign(request, pk):
    campaign = get_object_or_404(CampaignEntity, pk=pk, enterprise__user=request.user)
    campaign.delete()
    return Response({
        'message': 'Campaign deleted successfully',
        'status': status.HTTP_200_OK
    })

# update_post
@swagger_auto_schema(
    method='put',
    operation_description="Cập nhật thông tin bài đăng việc làm",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="Tiêu đề bài đăng"),
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả công việc"),
            'required': openapi.Schema(type=openapi.TYPE_STRING, description="Yêu cầu công việc"),
            'benefit': openapi.Schema(type=openapi.TYPE_STRING, description="Quyền lợi"),
            'experience': openapi.Schema(type=openapi.TYPE_STRING, description="Kinh nghiệm yêu cầu"),
            'type_working': openapi.Schema(type=openapi.TYPE_STRING, description="Loại hình công việc"),
            'salary_range': openapi.Schema(type=openapi.TYPE_STRING, description="Khoảng lương"),
            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số lượng cần tuyển"),
            'city': openapi.Schema(type=openapi.TYPE_STRING, description="Thành phố"),
            'position': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của vị trí"),
            'campaign': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của chiến dịch"),
        }
    ),
    responses={
        200: openapi.Response(
            description="Post updated successfully",
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
        ),
        404: openapi.Response(
            description="Post not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, AdminOrPostOwner])
def update_post(request, pk):
    post = get_object_or_404(PostEntity, id=pk, campaign__enterprise__user=request.user)
    serializer = PostSerializer(post, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Post updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        })
    return Response({
        'message': 'Post update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# delete_post
@swagger_auto_schema(
    method='delete',
    operation_description="Vô hiệu hóa (xóa) bài đăng việc làm",
    responses={
        200: openapi.Response(
            description="Post deleted successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Post not found",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'detail': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, AdminOrPostOwner])
def delete_post(request, pk):
    post = get_object_or_404(PostEntity, id=pk, campaign__enterprise__user=request.user)
    post.delete()
    return Response({
        'message': 'Post deleted successfully',
        'status': status.HTTP_200_OK
    })

@swagger_auto_schema(
    method='get',
    operation_description="Lấy thông tin chi tiết bài đăng tuyển dụng",
    responses={
        200: openapi.Response(
            description="Post details retrieved successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'title': openapi.Schema(type=openapi.TYPE_STRING),
                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                            'required': openapi.Schema(type=openapi.TYPE_STRING),
                            'benefit': openapi.Schema(type=openapi.TYPE_STRING),
                            'experience': openapi.Schema(type=openapi.TYPE_STRING),
                            'type_working': openapi.Schema(type=openapi.TYPE_STRING),
                            'salary_range': openapi.Schema(type=openapi.TYPE_STRING),
                            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'city': openapi.Schema(type=openapi.TYPE_STRING),
                            'position': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                }
                            ),
                            'campaign': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'enterprise': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'company_name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                        }
                                    ),
                                }
                            ),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            description="Post not found",
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
def get_post_detail(request, pk):
    """Chi tiết bài đăng"""
    post = get_object_or_404(PostEntity, pk=pk)
    serializer = PostSerializer(post)
    return Response({
        'message': 'Post details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })
