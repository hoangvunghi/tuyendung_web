from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timezone
from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from django.db.models import Q, Count, Case, When, Value, IntegerField, OuterRef, Subquery, F, Sum
from django.db.models.functions import Coalesce
from django.db.models.fields import Field
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from transactions.models import PremiumHistory
from .models import (
    EnterpriseEntity,
    PostEntity,
    FieldEntity,
    PositionEntity,
    CriteriaEntity,
    SavedPostEntity
)
from .serializers import (
    EnterpriseDetailSerializer, EnterprisePostDetailSerializer, EnterpriseSerializer, PostDetailSerializer, PostEnterpriseSerializer, PostSerializer,
    FieldSerializer, PositionSerializer, CriteriaSerializer,
    PostUpdateSerializer, PostEnterpriseForEmployerSerializer, SavedPostSerializer, PostListSerializer
)
from profiles.models import Cv
from profiles.serializers import CvSerializer, CvStatusSerializer
from base.permissions import (
    IsEnterpriseOwner, IsPostOwner,
    IsFieldManager, IsPositionManager, IsCriteriaOwner,
    AdminAccessPermission,
)
from base.utils import create_permission_class_with_admin_override
from base.aws_utils import upload_to_s3
from notifications.services import NotificationService
from base.pagination import CustomPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from base.cloudinary_utils import delete_image_from_cloudinary, upload_image_to_cloudinary
from django.utils.http import urlencode
import os
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Tạo các lớp quyền kết hợp với quyền admin
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)
AdminOrPostOwner = create_permission_class_with_admin_override(IsPostOwner)
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

# lấy doanh nghiệp của nhà tuyển dụng đang đăng nhập
@swagger_auto_schema(
    method='get',
    operation_description="Lấy doanh nghiệp của nhà tuyển dụng đang đăng nhập",
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
                            'modified_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                }
            )
        )
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_enterprises_by_user(request):
    enterprises = EnterpriseEntity.objects.filter(user=request.user)
    if not enterprises:
        return Response({
            'message': 'No enterprises found',
            'status': status.HTTP_404_NOT_FOUND,
        }, status=status.HTTP_404_NOT_FOUND)
    serializer = EnterpriseSerializer(enterprises, many=True)
    return Response({
        'message': 'Enterprise details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

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
    serializer = EnterpriseDetailSerializer(enterprise)
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
            'background_image': openapi.Schema(type=openapi.TYPE_FILE, description="Ảnh nền"),
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
@permission_classes([IsAuthenticated])
def create_enterprise(request):
    user = request.user
    if user.get_role() != 'employer':
        return Response({
            'message': 'You are not a employer',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)

    data = request.data.copy()
    # xóa hết comment của hàm này
    def upload_to_s3_handler(file, prefix):
        username = request.user.username
        file_extension = os.path.splitext(file.name)[1]
        new_filename = f"{username}_{prefix}{file_extension}"
        
        temp_path = f"temp_{new_filename}"
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        try:
            url = upload_to_s3(temp_path, new_filename)
            os.remove(temp_path)
            return url
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def upload_to_cloudinary_handler(file, folder):
        result = upload_image_to_cloudinary(file, folder)
        return result

    upload_tasks = []
    
    if 'business_certificate' in request.FILES:
        upload_tasks.append(('business_certificate', 'business_certificate', 's3'))
    
    if 'logo' in request.FILES:
        upload_tasks.append(('logo', 'enterprise_logos', 'cloudinary'))
    if 'background_image' in request.FILES:
        upload_tasks.append(('background_image', 'enterprise_backgrounds', 'cloudinary'))

    with ThreadPoolExecutor() as executor:
        futures = []
        for key, folder, service in upload_tasks:
            file = request.FILES[key]
            if service == 's3':
                futures.append(executor.submit(upload_to_s3_handler, file, key))
            else:
                futures.append(executor.submit(upload_to_cloudinary_handler, file, folder))

        for i, future in enumerate(futures):
            key, folder, service = upload_tasks[i]
            try:
                result = future.result()
                if service == 's3':
                    data[f'{key}_url'] = result
                else:
                    data[f'{key}_url'] = result['secure_url']
                    data[f'{key}_public_id'] = result['public_id']
            except Exception as e:
                return Response({
                    'message': f'Lỗi khi upload {key}: {str(e)}',
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = EnterpriseSerializer(data=data)
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
            'description': openapi.Schema(type=openapi.TYPE_STRING, description="Mô tả"),
            'email_company': openapi.Schema(type=openapi.TYPE_STRING, description="Email công ty"),
            'field_of_activity': openapi.Schema(type=openapi.TYPE_STRING, description="Lĩnh vực hoạt động"),
            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Trạng thái hoạt động"),
            'link_web_site': openapi.Schema(type=openapi.TYPE_STRING, description="Đường link website"),
            'logo': openapi.Schema(type=openapi.TYPE_FILE, description="Logo mới"),
            'background_image': openapi.Schema(type=openapi.TYPE_FILE, description="Ảnh nền mới"),
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
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_enterprise(request):
    enterprise = get_object_or_404(EnterpriseEntity, user=request.user)
    data = request.data.copy()

    data['is_active'] = enterprise.is_active

    def upload_to_s3_handler(file, prefix):
        username = request.user.username
        file_extension = os.path.splitext(file.name)[1]
        new_filename = f"{username}_{prefix}{file_extension}"
        
        temp_path = f"temp_{new_filename}"
        with open(temp_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        try:
            url = upload_to_s3(temp_path, new_filename)
            os.remove(temp_path)
            return url
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    def upload_to_cloudinary_handler(file, folder, old_public_id=None):
        if old_public_id:
            delete_image_from_cloudinary(old_public_id)
        result = upload_image_to_cloudinary(file, folder)
        return result

    upload_tasks = []
    
    if not enterprise.is_active and 'business_certificate' in request.FILES:
        upload_tasks.append(('business_certificate', 'business_certificate', 's3'))
    else:
        data['business_certificate_url'] = enterprise.business_certificate_url
    
    if 'logo' in request.FILES:
        upload_tasks.append(('logo', 'enterprise_logos', 'cloudinary', enterprise.logo_public_id))
    else:
        data['logo_url'] = enterprise.logo_url
        data['logo_public_id'] = enterprise.logo_public_id

    if 'background_image' in request.FILES:
        upload_tasks.append(('background_image', 'enterprise_backgrounds', 'cloudinary', enterprise.background_image_public_id))
    else:
        data['background_image_url'] = enterprise.background_image_url
        data['background_image_public_id'] = enterprise.background_image_public_id

    with ThreadPoolExecutor() as executor:
        futures = []
        for task in upload_tasks:
            key, folder, service = task[:3]
            file = request.FILES[key]
            if service == 's3':
                futures.append(executor.submit(upload_to_s3_handler, file, key))
            else:
                old_public_id = task[3] if len(task) > 3 else None
                futures.append(executor.submit(upload_to_cloudinary_handler, file, folder, old_public_id))

        for i, future in enumerate(futures):
            key, folder, service = upload_tasks[i][:3]
            try:
                result = future.result()
                if service == 's3':
                    data[f'{key}_url'] = result
                else:
                    data[f'{key}_url'] = result['secure_url']
                    data[f'{key}_public_id'] = result['public_id']
            except Exception as e:
                return Response({
                    'message': f'Lỗi khi upload {key}: {str(e)}',
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = EnterpriseSerializer(enterprise, data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Enterprise updated successfully',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Enterprise update failed',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa doanh nghiệp",
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
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, AdminAccessPermission])
def delete_enterprise(request):
    enterprise = get_object_or_404(EnterpriseEntity, user=request.user)
    if enterprise.business_certificate_public_id:
        delete_image_from_cloudinary(enterprise.business_certificate_public_id)

    if enterprise.logo_public_id:
        delete_image_from_cloudinary(enterprise.logo_public_id)
    
    if enterprise.background_image_public_id:
        delete_image_from_cloudinary(enterprise.background_image_public_id)
    
    enterprise.delete()
    return Response({
        'message': 'Enterprise deleted successfully',
        'status': status.HTTP_200_OK
    })

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách doanh nghiệp premium",
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
            description="Số lượng doanh nghiệp trên mỗi trang", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
    ],  
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT)
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_enterprise_premium(request):
    time_start = datetime.now()
    
    # Lấy tất cả doanh nghiệp có user premium
    enterprises = EnterpriseEntity.objects.filter(user__is_premium=True)
    
    # Import for premium sorting
    from transactions.models import PremiumHistory
    from django.utils import timezone
    
    # Lấy danh sách user_ids từ các doanh nghiệp premium
    user_ids = [e.user_id for e in enterprises]
    
    # Lấy premium histories
    premium_histories = PremiumHistory.objects.filter(
        user_id__in=user_ids,
        is_active=True,
        is_cancelled=False,
        end_date__gt=timezone.now()
    ).select_related('package')
    
    # Map user_id to premium_history
    user_premiums = {}
    for ph in premium_histories:
        if ph.user_id not in user_premiums:
            user_premiums[ph.user_id] = ph
    
    # Tính hệ số ưu tiên cho mỗi doanh nghiệp
    priority_coefficients = {}
    for enterprise in enterprises:
        premium = user_premiums.get(enterprise.user_id)
        if premium and premium.package:
            priority_coefficients[enterprise.id] = premium.package.priority_coefficient
        else:
            priority_coefficients[enterprise.id] = 999
    
    # Tạo list tuple (enterprise, priority) để sắp xếp
    enterprise_priority_pairs = [(enterprise, priority_coefficients.get(enterprise.id, 999)) for enterprise in enterprises]
    
    # Sắp xếp theo hệ số ưu tiên (thấp -> cao) và thời gian tạo (mới -> cũ)
    enterprise_priority_pairs.sort(key=lambda pair: (
        pair[1],  # Sắp xếp theo hệ số ưu tiên 
        -(pair[0].created_at.timestamp() if hasattr(pair[0], 'created_at') and pair[0].created_at else 0)
    ))
    
    # Lấy doanh nghiệp đã sắp xếp
    sorted_enterprises = [pair[0] for pair in enterprise_priority_pairs]
    
    # Phân trang
    paginator = CustomPagination()
    paginated_enterprise = paginator.paginate_queryset(sorted_enterprises, request)
    serializer = EnterpriseSerializer(paginated_enterprise, many=True)
    
    time_end = datetime.now()
    print(f"Time taken: {time_end - time_start} seconds")
    
    return paginator.get_paginated_response(serializer.data)

# Post CRUD
@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm",
    manual_parameters=[
        openapi.Parameter(
            'sort', 
            openapi.IN_QUERY, 
            description="Sắp xếp theo (-created_at, -salary_min, -salary_max)", 
            type=openapi.TYPE_STRING,
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
                    'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_posts(request):
    time_start = datetime.now()
    sort = request.query_params.get('sort', '-created_at')
    
    # Tạo cache key dựa trên tham số sắp xếp và trang hiện tại
    page = request.query_params.get('page', '1')
    page_size = request.query_params.get('page_size', '10')
    
    posts = PostEntity.objects.filter(
        is_active=True, 
        is_remove_by_admin=False,
        deadline__gt=datetime.now()
    ).select_related(
        'position', 
        'enterprise', 
        'field'
    )
        # Sắp xếp cơ bản theo tham số
    if (sort == '-salary-max'):
        posts = posts.order_by('-salary_max')
    elif (sort == '-salary-min'):
        posts = posts.order_by('-salary_min')
    elif (sort == '-created_at'):
        posts = posts.order_by('-created_at')
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    response_data = paginator.get_paginated_response(serializer.data).data
    return Response(response_data)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm của doanh nghiệp vai trò user là employer",
    responses={
        200: openapi.Response(description="Successful operation")
    }
)


@api_view(['GET'])
@permission_classes([IsEnterpriseOwner])
def get_post_for_enterprise(request):
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    posts = PostEntity.objects.filter(enterprise=enterprise)
    posts = posts.annotate(
        total_cvs=Count('cvs', distinct=True)
    )
    posts = posts.order_by('-created_at')
    
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostEnterpriseForEmployerSerializer(paginated_posts, many=True)
    return paginator.get_paginated_response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm của doanh nghiệp cho trang chi tiết",
    responses={
        200: openapi.Response(description="Successful operation")
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_posts_for_enterprise_detail(request, pk):
    posts = PostEntity.objects.filter(enterprise=pk)
    posts = posts.order_by('-created_at')
    serializer = PostSerializer(posts, many=True, context={'request': request})
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm của doanh nghiệp vai trò user là người dùng",
    responses={
        200: openapi.Response(description="Successful operation")
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_post_of_user(request):
    # lấy enterprise của user
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    posts = PostEntity.objects.filter(enterprise=enterprise)
    # phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng việc làm",
    responses={
        200: openapi.Response(
            description="Successful operation",
            schema=openapi.Schema(type=openapi.TYPE_OBJECT)
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_posts(request):
    posts = PostEntity.objects.filter(is_active=True, is_remove_by_admin=False, deadline__gt=datetime.now())
    
    # Phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)

@swagger_auto_schema(
    method='post',
    operation_description="Tạo bài đăng việc làm mới",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['title', 'position', 'city', 'experience', 'type_working'],
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
            description="lỗi",
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
@permission_classes([IsAuthenticated])
def create_post(request):
    # Admin có thể tạo post cho bất kỳ doanh nghiệp nào
    if request.user.is_superuser:
        enterprise_id = request.data.get('enterprise')
        try:
            enterprise = EnterpriseEntity.objects.get(id=enterprise_id)
        except EnterpriseEntity.DoesNotExist:
            return Response({
                'message': 'Doanh nghiệp không tồn tại',
                'status': status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        # Employer chỉ tạo được post cho doanh nghiệp mình
        enterprise = request.user.get_enterprise()
        print("ALO", enterprise)
        if not enterprise:
            return Response({
                'message': 'Bạn không phải là nhà tuyển dụng',
                'status': status.HTTP_403_FORBIDDEN
            }, status=status.HTTP_403_FORBIDDEN)
    enterprise_active = enterprise.is_active
    if not enterprise_active:
        return Response({
            'message': 'Doanh nghiệp đang trong thời gian xét duyệt',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    # Thêm enterprise vào data
    if not request.user.can_post_job():
        # Lấy thông tin về giới hạn đăng bài
        premium_package = request.user.get_premium_package()
        max_posts = 3  # Giới hạn mặc định
        if premium_package:
            max_posts = premium_package.max_job_posts
        
        return Response({
            'code': 403,
            'message': f'Đã đạt giới hạn đăng bài ({request.user.post_count}/{max_posts}). Vui lòng nâng cấp gói Premium để đăng thêm.',
            'current_posts': request.user.post_count,
            'max_posts': max_posts
        }, status=status.HTTP_403_FORBIDDEN)
    data = request.data.copy()
    data['enterprise'] = enterprise.id
    # Đảm bảo is_remove_by_admin là False
    data['is_remove_by_admin'] = False
    
    serializer = PostSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Tạo bài đăng thành công',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Tạo bài đăng thất bại',
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

    params = {
        'q': request.query_params.get('q', ''),
        'city': request.query_params.get('city', ''),
        'field': request.query_params.get('field', ''),
        'scale': request.query_params.get('scale', ''),
        'sort_by': request.query_params.get('sort_by', 'company_name'),
        'sort_order': request.query_params.get('sort_order', 'asc'),
        'page': request.query_params.get('page', '1'),
        'page_size': request.query_params.get('page_size', '10')
    }
    cache_key = f'enterprises_search_{urlencode(params)}'
    
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        return Response(cached_response)
    
    # Nếu không có trong cache, thực hiện tìm kiếm
    enterprises = EnterpriseEntity.objects.filter(is_active=True)
    
    if params['q']:
        enterprises = enterprises.filter(
            Q(company_name__icontains=params['q']) |
            Q(description__icontains=params['q']) |
            Q(field_of_activity__icontains=params['q'])
        )
    
    if params['city']:
        enterprises = enterprises.filter(city__iexact=params['city'])
    
    if params['field']:
        enterprises = enterprises.filter(field_of_activity__icontains=params['field'])
        
    if params['scale']:
        enterprises = enterprises.filter(scale__iexact=params['scale'])
    
    # Sắp xếp kết quả
    sort_by = params['sort_by']
    if params['sort_order'] == 'desc':
        sort_by = f'-{sort_by}'
    enterprises = enterprises.order_by(sort_by)
    
    paginator = CustomPagination()
    paginated_enterprises = paginator.paginate_queryset(enterprises, request)
    
    serializer = EnterpriseSerializer(paginated_enterprises, many=True)
    response_data = paginator.get_paginated_response(serializer.data).data
    
    cache.set(cache_key, response_data, 60)
    
    return Response(response_data)

# Post Search & Filter
@swagger_auto_schema(
    method='get',
    operation_description="""
    Tìm kiếm và lọc bài đăng việc làm.
    API này cho phép tìm kiếm bài đăng theo từ khóa, vị trí địa lý, vị trí công việc, kinh nghiệm, loại công việc và khoảng lương.
    Kết quả được phân trang và có thể sắp xếp theo các tiêu chí khác nhau.
    
    Lưu ý về lọc lương:
    - Nếu chỉ cung cấp salary_min: lọc các bài đăng có lương tối thiểu >= salary_min
    - Nếu chỉ cung cấp salary_max: lọc các bài đăng có lương tối đa <= salary_max
    - Nếu cung cấp cả salary_min và salary_max: lọc các bài đăng có khoảng lương nằm trong khoảng [salary_min, salary_max]
    - Nếu negotiable=true: lọc các bài đăng có lương thỏa thuận
    - Có thể kết hợp các điều kiện lọc lương với nhau
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
            description="Vị trí công việc (ID hoặc tên)", 
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
            'scales', openapi.IN_QUERY, 
            description="Quy mô công ty (ví dụ: '1-50', '51-150', '151-300')", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'field', openapi.IN_QUERY, 
            description="Lĩnh vực (ID hoặc tên)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'salary_min', openapi.IN_QUERY, 
            description="Lương tối thiểu (triệu đồng)", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'salary_max', openapi.IN_QUERY, 
            description="Lương tối đa (triệu đồng)", 
            type=openapi.TYPE_INTEGER,
            required=False
        ),
        openapi.Parameter(
            'negotiable', openapi.IN_QUERY, 
            description="Lọc bài đăng có lương thỏa thuận. Giá trị: 'true' hoặc 'false'. Có thể kết hợp với salary_min và salary_max", 
            type=openapi.TYPE_STRING,
            enum=['true', 'false'],
            required=False
        ),
        openapi.Parameter(
            'all', openapi.IN_QUERY, 
            description="Hiển thị tất cả bài đăng (true) hay chỉ hiển thị bài đăng phù hợp tiêu chí (false). Mặc định là true", 
            type=openapi.TYPE_STRING,
            enum=['true', 'false'],
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
            description="Trường sắp xếp (ví dụ: 'created_at', 'salary_min', 'salary_max')", 
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
                                        'salary_min': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'salary_max': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'is_salary_negotiable': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                        'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'city': openapi.Schema(type=openapi.TYPE_STRING),
                                        'position': openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                        ),
                                        'field': openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            },
                                            nullable=True
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
    time_start = datetime.now()
    params = {}
    for key in ['q', 'city', 'position', 'experience', 'type_working', 'scales', 'field', 'salary_min', 'salary_max', 'negotiable', 'all']:
        value = request.query_params.get(key, '')
        if value:
            params[key] = value
            
    params['sort_by'] = request.query_params.get('sort_by', 'created_at')
    params['sort_order'] = request.query_params.get('sort_order', 'desc')
    params['page'] = request.query_params.get('page', '1')
    params['page_size'] = request.query_params.get('page_size', '10')
    
    # Mặc định all=true
    if 'all' not in params:
        params['all'] = 'true'
    
    cache_key = f"search_posts_results_{hash(frozenset(params.items()))}"
    
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return Response(cached_data)
    query = PostEntity.objects.filter(
        is_active=True,
        is_remove_by_admin=False,
        deadline__gte=datetime.now()
    )
    
    # Áp dụng bộ lọc tìm kiếm từ params nếu có (chưa thực thi truy vấn)
    if params.get("q") != None:
        if len(params.get('q')) > 0:
            search_term = params.get('q')
            query = query.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(required__icontains=search_term) |
                Q(enterprise__company_name__icontains=search_term)
            )

    if params.get("city"):
        if len(params.get('city')) > 0:
            query = query.filter(city__icontains=params.get('city'))
    if params.get("experience"):
        if len(params.get('experience')) > 0:
            query = query.filter(experience__iexact=params.get('experience'))
    if params.get("type_working"):
        if len(params.get('type_working')) > 0:
            query = query.filter(type_working__iexact=params.get('type_working'))
    if params.get("scales"):
        if len(params.get('scales')) > 0:
            query = query.filter(enterprise__scale__iexact=params.get('scales'))
    if params.get("position"):
        if len(params.get('position')) > 0:
            position_param = params.get('position')
            if position_param.isdigit():
                query = query.filter(position__id=int(position_param))
            else:
                query = query.filter(position__name__icontains=position_param)
    if params.get("field"):
        if len(params.get('field')) > 0:
            field_param = params.get('field')
            if field_param.isdigit():
                query = query.filter(
                Q(field__id=int(field_param)) |
                Q(position__field__id=int(field_param))
            )
            else:
                query = query.filter(
                    Q(field__name__icontains=field_param) |
                    Q(position__field__name__icontains=field_param)
                )
    if params.get("salary_min"):
        if len(params.get('salary_min')) > 0:
            query = query.filter(salary_min__gte=int(params.get('salary_min')))
    if params.get("salary_max"):
        if len(params.get('salary_max')) > 0:
            query = query.filter(salary_max__lte=int(params.get('salary_max')))
    if params.get("negotiable"):
        if len(params.get('negotiable')) > 0:
            query = query.filter(is_salary_negotiable=True)
    time_query_build = datetime.now()
    
    # Cải thiện hiệu suất bằng select_related trước khi thực hiện truy vấn
    filtered_query = query.select_related(
        'position', 
        'field', 
        'enterprise'
    )
    # Chỉ lấy các trường cần thiết cho việc tính điểm và sắp xếp
    # Dùng values() để chuyển đổi QuerySet sang dictionary để xử lý nhanh hơn
    post_data = list(filtered_query.values(
        'id', 'title', 'city', 'experience', 'type_working', 
        'salary_min', 'salary_max', 'is_salary_negotiable', 'created_at',
        'enterprise_id', 'position_id', 'field_id',
        'enterprise__scale', 'position__field_id'
    ))

    time_initial_query = datetime.now()
    # Nếu không có kết quả lọc và all=true, lấy tất cả bài đăng
    if len(post_data) == 0:
        if params.get('q') != None:
            if len(params.get('q')) !=0:
                return Response({
                    'message': 'Data retrieved successfully',
                    'status': status.HTTP_200_OK,
                    'data': {
                        'links': {
                            'next': None,
                            'previous': None,
                        },
                        'total': 0,
                        'page': int(params.get('page', 1)),
                        'total_pages': 0,
                        'page_size': int(params.get('page_size', 10)),
                        'results': []
                    }
                })
        # Thực hiện query lại để lấy tất cả bài đăng active
        if params.get('all') == 'true':
            post_data = list(PostEntity.objects.filter(
                is_active=True,
                deadline__gte=datetime.now()
            ).values(
                'id', 'title', 'city', 'experience', 'type_working', 
                'salary_min', 'salary_max', 'is_salary_negotiable', 'created_at',
                'enterprise_id', 'position_id', 'field_id',
                'enterprise__scale', 'position__field_id'
            ))
    
    # Lấy thông tin user criteria nếu đã đăng nhập (cần thiết cho việc tính điểm)
    user = request.user
    user_criteria = None
    if user.is_authenticated:
        try:
            user_criteria = CriteriaEntity.objects.select_related('field', 'position').get(user=user)
        except CriteriaEntity.DoesNotExist:
            pass
    # Tối ưu thông tin premium cho các doanh nghiệp
    enterprise_ids = {post['enterprise_id'] for post in post_data if post['enterprise_id'] is not None}
    
    # Cache thông tin hệ số ưu tiên
    priority_cache_key = 'enterprise_priority_coefficients'
    enterprise_premium_coefficients = cache.get(priority_cache_key, {})
    
    # Chỉ truy vấn enterprise và premium cho các doanh nghiệp chưa có trong cache
    missing_enterprise_ids = [eid for eid in enterprise_ids if eid not in enterprise_premium_coefficients]
    
    if missing_enterprise_ids:
        # Truy vấn hiệu quả: chỉ lấy enterprise.user_id
        enterprise_users = {}
        for item in EnterpriseEntity.objects.filter(id__in=missing_enterprise_ids).values('id', 'user_id'):
            enterprise_users[item['id']] = item['user_id']
        
        if enterprise_users:
            # Lấy premium histories hiệu quả với một truy vấn
            user_ids = list(enterprise_users.values())
            
            # Tạo map user_id -> priority_coefficient
            user_premium_coefficients = {}
            
            for ph in PremiumHistory.objects.filter(
                user_id__in=user_ids,
                is_active=True,
                is_cancelled=False,
                end_date__gt=timezone.now()
            ).select_related('package').values('user_id', 'package__priority_coefficient'):
                user_premium_coefficients[ph['user_id']] = ph['package__priority_coefficient']
            
            # Tính toán priority coefficients cho các doanh nghiệp thiếu
            for enterprise_id, user_id in enterprise_users.items():
                coefficient = user_premium_coefficients.get(user_id)
                enterprise_premium_coefficients[enterprise_id] = coefficient if coefficient else 999
            
            # Lưu vào cache trong 1 giờ
            cache.set(priority_cache_key, enterprise_premium_coefficients, 60 * 60)
    
    time_premium_fetch = datetime.now()
    print(f"Premium data fetch time: {time_premium_fetch - time_initial_query} seconds")
    
    # Tính điểm và priority cho mỗi post
    scored_posts = []
    for post in post_data:
        score = 0
        post_obj = {**post}  # Tạo copy để không ảnh hưởng đến dữ liệu gốc
        
        # Tính điểm dựa trên criteria của user (nếu có)
        if user_criteria:
            # City (4 điểm)
            if user_criteria.city and post['city'] and post['city'].lower() == user_criteria.city.lower():
                score += 4
            
            # Experience (3 điểm)
            if user_criteria.experience and post['experience'] and post['experience'].lower() == user_criteria.experience.lower():
                score += 3
            
            # Type of working (3 điểm)
            if user_criteria.type_working and post['type_working'] and post['type_working'].lower() == user_criteria.type_working.lower():
                score += 3
            
            # Scales (2 điểm)
            if user_criteria.scales and post['enterprise__scale'] and post['enterprise__scale'].lower() == user_criteria.scales.lower():
                score += 2
            
            # Field (5 điểm)
            if user_criteria.field:
                if (post['field_id'] and post['field_id'] == user_criteria.field.id) or \
                   (post['position__field_id'] and post['position__field_id'] == user_criteria.field.id):
                    score += 5
            
            # Position (5 điểm)
            if user_criteria.position and post['position_id'] and post['position_id'] == user_criteria.position.id:
                score += 5
            
            # Salary (3 điểm)
            if user_criteria.salary_min and post['salary_min'] and post['salary_min'] >= user_criteria.salary_min:
                score += 3
        
        # Tính điể''m dựa trên các tham số tìm kiếm
        if params.get('city') and post['city'] and post['city'].lower() == params.get('city').lower():
            score += 4
        
        if params.get('experience') and post['experience'] and post['experience'].lower() == params.get('experience').lower():
            score += 3
        
        if params.get('type_working') and post['type_working'] and post['type_working'].lower() == params.get('type_working').lower():
            score += 3
        
        if params.get('scales') and post['enterprise__scale'] and post['enterprise__scale'].lower() == params.get('scales').lower():
            score += 2
        
        # Lưu điểm và đánh dấu matches_criteria
        post_obj['match_score'] = score
        post_obj['matches_criteria'] = score >= 7
        post_obj['priority_coefficient'] = enterprise_premium_coefficients.get(post['enterprise_id'], 999)
        post_obj['is_enterprise_premium'] = post_obj['priority_coefficient'] < 999
        
        scored_posts.append(post_obj)
    
    time_scoring = datetime.now()
    print(f"Post scoring time: {time_scoring - time_premium_fetch} seconds")
    
    # Lọc và sắp xếp posts theo tiêu chí
    if params.get('all') == 'false':
        # Nếu all=false, chỉ giữ lại những bài đăng phù hợp với tiêu chí
        filtered_posts = [post for post in scored_posts if post['matches_criteria']]
    else:
        # all=true: Sắp xếp posts theo matches_criteria rồi đến hệ số ưu tiên và thời gian tạo
        filtered_posts = sorted(
            scored_posts,
            key=lambda p: (
                not p['matches_criteria'], 
                p['priority_coefficient'], 
                -(p['created_at'].timestamp() if isinstance(p['created_at'], datetime) else 0)
            )
        )
    
    time_sorting = datetime.now()
    print(f"Sorting time: {time_sorting - time_scoring} seconds")
    
    # Lấy danh sách ID đã sắp xếp
    sorted_post_ids = [post['id'] for post in filtered_posts]
    
    # Nếu không có kết quả, trả về rỗng
    if not sorted_post_ids:
        # Trả về response rỗng với định dạng phân trang
        empty_data = {
            'message': 'Data retrieved successfully',
            'status': status.HTTP_200_OK,
            'data': {
                'links': {
                    'next': None,
                    'previous': None,
                },
                'total': 0,
                'page': int(params.get('page', 1)),
                'total_pages': 0,
                'page_size': int(params.get('page_size', 10)),
                'results': []
            }
        }
        cache.set(cache_key, empty_data, 60 * 5)
        return Response(empty_data)
    
    # Tạo bản đồ thông tin post để sử dụng sau
    post_info_map = {post['id']: post for post in filtered_posts}
    
    # Tạo paginator instance và tính toán pagination
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 10))
    
    # Tính toán phân trang thủ công
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(sorted_post_ids))
    
    # Chỉ lấy ID cho trang hiện tại
    current_page_ids = sorted_post_ids[start_idx:end_idx]
    
    time_pagination = datetime.now()
    print(f"Pagination time: {time_pagination - time_sorting} seconds")
    
    # Chuẩn bị truy vấn trực tiếp vào database sử dụng các ID đã lọc và sắp xếp cho trang hiện tại
    # Sử dụng từ điển để lưu trữ kết quả
    paged_data = {
        'links': {
            'next': f'?page={page + 1}' if end_idx < len(sorted_post_ids) else None,
            'previous': f'?page={page - 1}' if page > 1 else None,
        },
        'total': len(sorted_post_ids),
        'page': page,
        'total_pages': (len(sorted_post_ids) + page_size - 1) // page_size,
        'page_size': page_size,
        'results': []
    }
    
    saved_post_ids = set()
    if user.is_authenticated:
        saved_post_ids = set(SavedPostEntity.objects.filter(
            user=user, 
            post_id__in=current_page_ids
        ).values_list('post_id', flat=True))
    
    from django.db.models import Prefetch, F, Value as V
    from django.db.models.functions import Concat
    
    # Chỉ truy vấn các trường cần thiết
    posts_with_relations = PostEntity.objects.filter(
        id__in=current_page_ids
    ).select_related(
        'position', 
        'field', 
        'enterprise'
    ).only(
        # Post fields
        'id', 'title', 'description', 'required', 'type_working',
        'salary_min', 'salary_max', 'is_salary_negotiable', 'quantity',
        'city', 'created_at', 'deadline', 'is_active', 'interest', 'district',
        # Related fields (có thể tự động nạp)
        'position_id', 'field_id', 'enterprise_id'
    )
    
    # Tạo từ điển sắp xếp để giữ đúng thứ tự của kết quả
    position_map = {id: idx for idx, id in enumerate(current_page_ids)}
    
    # Sắp xếp kết quả theo thứ tự ban đầu
    sorted_results = sorted(posts_with_relations, key=lambda post: position_map.get(post.id, 999))
    
    time_fetch_detail = datetime.now()
    print(f"Fetch detail time: {time_fetch_detail - time_pagination} seconds")
    
    # Biến đổi dữ liệu sang định dạng cần thiết
    for post in sorted_results:
        post_info = post_info_map.get(post.id, {})
        
        # Tạo từ điển kết quả thủ công để tránh gọi serializer nặng nề
        result = {
            'id': post.id,
            'title': post.title,
            'description': post.description,
            'required': post.required,
            'interest': post.interest,
            'type_working': post.type_working,
            'salary_min': post.salary_min,
            'salary_max': post.salary_max,
            'is_salary_negotiable': post.is_salary_negotiable,
            'quantity': post.quantity,
            'city': post.city,
            'district': post.district,
            'created_at': post.created_at,
            'deadline': post.deadline,
            'is_active': post.is_active,
            'enterprise': post.enterprise_id,
            'enterprise_name': post.enterprise.company_name if post.enterprise else None,
            'enterprise_logo': post.enterprise.logo_url if post.enterprise else None,
            'is_saved': post.id in saved_post_ids,
            'is_enterprise_premium': post_info.get('is_enterprise_premium', False),
            'matches_criteria': post_info.get('matches_criteria', False)
        }
        
        # Thêm thông tin position
        if post.position:
            result['position'] = {
                'id': post.position.id,
                'name': post.position.name,
                'code': post.position.code,
                'status': post.position.status,
                'created_at': post.position.created_at,
                'modified_at': post.position.modified_at,
                'field': post.position.field_id
            }
        else:
            result['position'] = None
        
        # Thêm thông tin field
        if post.field:
            result['field'] = {
                'id': post.field.id,
                'name': post.field.name
            }
        else:
            result['field'] = None
        
        paged_data['results'].append(result)
    
    time_transform = datetime.now()
    print(f"Transform time: {time_transform - time_fetch_detail} seconds")
    
    # Định dạng phản hồi cuối cùng theo yêu cầu
    response_data = {
        'message': 'Data retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': paged_data
    }
    
    cache.set(cache_key, response_data, 60 * 5)  # Cache trong 5 phút
    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommended_posts(request):
    try:
        criteria = CriteriaEntity.objects.get(user=request.user)
        
        # Lấy tất cả các bài đăng active, không bị loại bỏ và chưa hết hạn
        posts = PostEntity.objects.filter(
            is_remove_by_admin=False, 
            is_active=True,
            deadline__gt=timezone.now()
        ).select_related('enterprise', 'position', 'position__field', 'field')
        
        # ĐIỀU KIỆN LƯƠNG - LOẠI BỎ NGAY CÁC BÀI ĐĂNG CÓ LƯƠNG THẤP HƠN YÊU CẦU
        filtered_posts = []
        if criteria.salary_min is not None and criteria.salary_min > 0:
            # Lọc bài đăng ngay từ đầu theo điều kiện lương
            for post in posts:
                # Chỉ giữ lại bài đăng:
                # 1. Có lương thỏa thuận HOẶC
                # 2. Có mức lương tối thiểu >= mức lương yêu cầu
                if post.is_salary_negotiable or (post.salary_min is not None and post.salary_min >= criteria.salary_min):
                    filtered_posts.append(post)
        else:
            # Nếu không có yêu cầu lương, giữ nguyên danh sách
            filtered_posts = list(posts)
        
        # Tạo danh sách kết quả với điểm số
        result = []
        
        for post in filtered_posts:
            score = 0
            
            # ĐIỀU KIỆN BẮT BUỘC: Post phải cùng lĩnh vực
            field_match = False
            if criteria.field:
                # Kiểm tra field trực tiếp của post
                if post.field and post.field.id == criteria.field.id:
                    field_match = True
                # Kiểm tra field qua position
                elif post.position and post.position.field and post.position.field.id == criteria.field.id:
                    field_match = True
            
            if field_match:
                score += 4  # Giảm từ 6 xuống 4
            
            # Nếu không cùng lĩnh vực thì bỏ qua bài đăng này
            if not field_match:
                continue
                
            # Vị trí - quan trọng thứ hai
            position_match = False
            if criteria.position and post.position and criteria.position.id == post.position.id:
                score += 3  # Giảm từ 5 xuống 3
                position_match = True
            
            # Mức lương - đã lọc ở trước đó
            salary_match = False
            if criteria.salary_min is not None and criteria.salary_min > 0:
                if post.is_salary_negotiable:
                    # Lương thỏa thuận
                    score += 1
                    salary_match = True
                else:
                    # Lương đạt yêu cầu (đã lọc ở trên)
                    score += 2  # Giảm từ 4 xuống 2
                    salary_match = True
            
            # Thành phố
            city_match = False
            if criteria.city and post.city and criteria.city.lower() == post.city.lower():
                score += 2  # Giảm từ 3 xuống 2
                city_match = True
                
            # Loại hình công việc
            if criteria.type_working and post.type_working and criteria.type_working.lower() == post.type_working.lower():
                score += 1  # Giảm từ 2 xuống 1
                
            # Kinh nghiệm
            if criteria.experience and post.experience and criteria.experience.lower() == post.experience.lower():
                score += 1  # Giảm từ 2 xuống 1
                
            # Quy mô công ty
            if criteria.scales and post.enterprise and criteria.scales.lower() == post.enterprise.scale.lower():
                score += 1  # Giữ nguyên
            
            # Cộng thêm điểm nếu đáp ứng nhiều tiêu chí cùng lúc
            if position_match:
                score += 1  # Giảm từ 2 xuống 1
                
            if city_match:
                score += 1  # Giữ nguyên
                
            if salary_match and position_match:
                score += 1  # Giảm từ 2 xuống 1
                
            if position_match and city_match:
                score += 1  # Giảm từ 2 xuống 1
                
            # Nới lỏng ngưỡng điểm từ 6 xuống 4 (chỉ cần field match)
            if score >= 4:
                result.append((post, score))
        
        # Sắp xếp kết quả theo điểm số giảm dần, sau đó theo thời gian tạo mới nhất
        result.sort(key=lambda x: (-x[1], -x[0].created_at.timestamp()))
        
        # Lấy danh sách các bài đăng đã sắp xếp (giới hạn 10 bài đăng)
        sorted_posts = [item[0] for item in result[:10]]
        
        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(sorted_posts, request)
        serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
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
    """Lấy thống kê về doanh nghiệp: số lượng CV theo trạng thái, số bài đăng"""
    enterprise = get_object_or_404(EnterpriseEntity, pk=pk, user=request.user)
    # Tổng số bài đăng
    total_posts = PostEntity.objects.filter(enterprise=enterprise).count()
    
    # Số lượng CV theo trạng thái
    cv_stats = {}
    posts = PostEntity.objects.filter(enterprise=enterprise)
    for status_choice in ['pending', 'approved', 'rejected']:
        cv_count = Cv.objects.filter(post__in=posts, status=status_choice).count()
        cv_stats[status_choice] = cv_count
    
    return Response({
        'message': 'Enterprise statistics retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': {
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
    
    # # Tạo notification khi CV được xem
    # NotificationService.notify_cv_viewed(cv)
    
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
        
        # Không gọi notify_cv_status_changed ở đây vì đã được gọi từ profiles/views.py
        # Tránh tạo ra 2 thông báo
        
        return Response({
            'message': 'CV status updated successfully',
            'data': serializer.data
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
@permission_classes([IsEnterpriseOwner])
def update_post(request, pk):
    try:
        post = PostEntity.objects.get(pk=pk)
        # Kiểm tra nếu post đã active thì không cho phép sửa
        if post.is_active:
            return Response({
                'message': 'Bài đăng đã được xét duyệt, không được sửa',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
    except PostEntity.DoesNotExist:
        return Response({
            'message': 'Bài đăng không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    # Admin có thể sửa bất kỳ post nào
    if not request.user.is_superuser:
        # Employer chỉ sửa được post của doanh nghiệp mình
        enterprise = request.user.get_enterprise()
        if not enterprise or post.enterprise != enterprise:
            return Response({
                'message': 'Bạn không có quyền sửa bài đăng này',
                'status': status.HTTP_403_FORBIDDEN
            }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = PostUpdateSerializer(post, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Cập nhật bài đăng thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Cập nhật bài đăng thất bại',
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
@permission_classes([IsAuthenticated])
def delete_post(request, pk):
    try:
        post = PostEntity.objects.get(pk=pk)
    except PostEntity.DoesNotExist:
        return Response({
            'message': 'Bài đăng không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Admin có thể xóa bất kỳ post nào
    if not request.user.is_superuser:
        # Employer chỉ xóa được post của doanh nghiệp mình
        enterprise = request.user.get_enterprise()
        if not enterprise or post.enterprise != enterprise:
            return Response({
                'message': 'Bạn không có quyền xóa bài đăng này',
                'status': status.HTTP_403_FORBIDDEN
            }, status=status.HTTP_403_FORBIDDEN)
    
    post.delete()
    return Response({
        'message': 'Xóa bài đăng thành công',
        'status': status.HTTP_200_OK
    }, status=status.HTTP_200_OK)

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
    try:
        from django.db.models import Count, Q, Prefetch, Case, When, Value, IntegerField
        from profiles.models import Cv
        from django.core.cache import cache
        import time
        
        # Đo thời gian thực hiện
        start_time = time.time()
        
        post = PostEntity.objects.select_related(
            'enterprise', 
            'enterprise__user',
            'position',
            'field'
        ).get(pk=pk)
        
        serializer = PostDetailSerializer(post)
        data = serializer.data
        
        # Thêm thông tin bổ sung về doanh nghiệp
        data['enterprise_logo'] = post.enterprise.logo_url
        data['user_id'] = post.enterprise.user.id
        data['is_enterprise_premium'] = post.enterprise.user.is_premium
        data['enterprise_address'] = post.enterprise.address
        
        # Tối ưu truy vấn đếm ứng viên bằng cách tạo index và sử dụng pk thay vì object
        total_applicants = Cv.objects.filter(post_id=pk).count()
        
        # Xử lý quyền xem thông tin ứng viên - sử dụng IDs để so sánh thay vì objects
        if request.user.is_authenticated:
            is_owner = post.enterprise.user_id == request.user.id
            if is_owner or request.user.is_premium:
                data['total_applicants'] = total_applicants
                data['can_view_applicants'] = True
            else:
                data['can_view_applicants'] = False
                data['has_applicants'] = total_applicants > 0
            
            # Kiểm tra quyền chat
            data['can_chat_with_employer'] = not request.user.is_employer() and request.user.can_chat_with_employers()
            
            # Lấy ngày ứng tuyển gần nhất - chỉ truy vấn các trường cần thiết
            latest_application = Cv.objects.filter(
                post_id=pk, 
                user_id=request.user.id
            ).order_by('-created_at').only('created_at').first()
            
            data['latest_application_date'] = latest_application.created_at.strftime('%d/%m/%Y') if latest_application else None
        else:
            # Người dùng chưa đăng nhập
            data['can_view_applicants'] = False
            data['has_applicants'] = total_applicants > 0
            data['can_chat_with_employer'] = False
            data['latest_application_date'] = None
            
        # Lấy danh sách bài đăng liên quan với một truy vấn hiệu quả
        # Chỉ lấy các bài đăng có cùng field
        related_posts_query = PostEntity.objects.filter(
            is_active=True,
            deadline__gt=timezone.now(),
            field_id=post.field_id  # Chỉ lấy bài đăng cùng field
        ).exclude(id=post.id).select_related(
            'enterprise',
            'field',
            'position'
        )
        
        # Tính điểm liên quan cho mỗi bài đăng sử dụng Case/When để tránh nhiều truy vấn
        related_posts_query = related_posts_query.annotate(
            relevance_score=Case(
                When(position_id=post.position_id, then=Value(3)),  # Ưu tiên cùng vị trí
                When(city=post.city, then=Value(2)),  # Tiếp đến là cùng thành phố
                When(enterprise_id=post.enterprise_id, then=Value(1)),  # Cuối cùng là cùng doanh nghiệp
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-relevance_score', '-created_at')[:7]  # Giới hạn 7 bài đăng liên quan
        
        # Thực hiện truy vấn và lấy kết quả
        related_posts = list(related_posts_query)
        
        # Serialize kết quả
        related_posts_serializer = PostListSerializer(related_posts, many=True, context={'request': request})
        data['related_posts'] = related_posts_serializer.data
        
        # Thông tin field
        data['field'] = post.field.name if post.field else None
        
        # Tạo response để cache và trả về
        response_data = {
            'message': 'Post details retrieved successfully',
            'status': status.HTTP_200_OK,
            'data': data
        }
        
        
        # In thời gian thực hiện để theo dõi hiệu suất
        print(f"Execution time: {time.time() - start_time:.4f}s (from database)")
        
        return Response(response_data)
    except PostEntity.DoesNotExist:
        return Response({
            'message': 'Bài đăng không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    operation_description='Lấy danh sách vị trí công việc',
    responses={
        200: openapi.Response(
            description='Thành công',
            schema=PositionSerializer(many=True)
        ),
        401: 'Chưa xác thực',
        403: 'Không có quyền truy cập'
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_positions(request):
    positions = PositionEntity.objects.filter(status='active')
    
    # Phân trang
    paginator = CustomPagination()
    paginated_positions = paginator.paginate_queryset(positions, request)
    
    serializer = PositionSerializer(paginated_positions, many=True)
    return paginator.get_paginated_response(serializer.data)

#get_position_name
@api_view(['GET'])
@permission_classes([AllowAny])
def get_position_name(request, pk):
    try:
        position = PositionEntity.objects.get(pk=pk)
        return Response({
            'message': 'Tên vị trí',
            'name': position.name,
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except PositionEntity.DoesNotExist:
        return Response({
            'message': 'Vị trí không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='post',
    operation_description='Tạo vị trí công việc mới',
    request_body=PositionSerializer,
    responses={
        201: openapi.Response(
            description='Tạo thành công',
            schema=PositionSerializer
        ),
        400: 'Dữ liệu không hợp lệ',
        401: 'Chưa xác thực',
        403: 'Không có quyền truy cập'
    }
)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_position(request):
    serializer = PositionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Tạo vị trí thành công',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Tạo vị trí thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='put',
    operation_description='Cập nhật vị trí công việc',
    request_body=PositionSerializer,
    responses={
        200: openapi.Response(
            description='Cập nhật thành công',
            schema=PositionSerializer
        ),
        400: 'Dữ liệu không hợp lệ',
        401: 'Chưa xác thực',
        403: 'Không có quyền truy cập',
        404: 'Vị trí không tồn tại'
    }
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_position(request, pk):
    try:
        position = PositionEntity.objects.get(pk=pk)
    except PositionEntity.DoesNotExist:
        return Response({
            'message': 'Vị trí không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = PositionSerializer(position, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Cập nhật vị trí thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Cập nhật vị trí thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description='Xóa vị trí công việc',
    responses={
        200: 'Xóa thành công',
        401: 'Chưa xác thực',
        403: 'Không có quyền truy cập',
        404: 'Vị trí không tồn tại'
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_position(request, pk):
    try:
        position = PositionEntity.objects.get(pk=pk)
    except PositionEntity.DoesNotExist:
        return Response({
            'message': 'Vị trí không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    position.delete()
    return Response({
        'message': 'Xóa vị trí thành công',
        'status': status.HTTP_200_OK
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='get',
    operation_description='Lấy tiêu chí tìm việc của user',
    responses={
        200: openapi.Response(
            description='Thành công',
            schema=CriteriaSerializer
        ),
        401: 'Chưa xác thực',
        404: 'Chưa có tiêu chí'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_criteria(request):
    try:
        criteria = CriteriaEntity.objects.filter(user=request.user).first()
        
        if not criteria:
            return Response({
                'message': 'Bạn chưa có tiêu chí tìm việc',
                'status': status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CriteriaSerializer(criteria)
        return Response({
            'message': 'Thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'message': f'Lỗi: {str(e)}',
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method='post',
    operation_description='Tạo tiêu chí tìm việc mới',
    request_body=CriteriaSerializer,
    responses={
        201: openapi.Response(
            description='Tạo thành công',
            schema=CriteriaSerializer
        ),
        400: 'Dữ liệu không hợp lệ',
        401: 'Chưa xác thực'
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_criteria(request):
    # Kiểm tra xem user đã có criteria chưa
    if CriteriaEntity.objects.filter(user=request.user).exists():
        return Response({
            'message': 'Bạn đã có tiêu chí tìm việc',
            'status': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = CriteriaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response({
            'message': 'Tạo tiêu chí thành công',
            'status': status.HTTP_201_CREATED,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'message': 'Tạo tiêu chí thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='put',
    operation_description='Cập nhật tiêu chí tìm việc',
    request_body=CriteriaSerializer,
    responses={
        200: openapi.Response(
            description='Cập nhật thành công',
            schema=CriteriaSerializer
        ),
        400: 'Dữ liệu không hợp lệ',
        401: 'Chưa xác thực',
        404: 'Chưa có tiêu chí'
    }
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_criteria(request):
    try:
        criteria = CriteriaEntity.objects.get(user=request.user)
    except CriteriaEntity.DoesNotExist:
        return Response({
            'message': 'Bạn chưa có tiêu chí tìm việc',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CriteriaSerializer(criteria, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Cập nhật tiêu chí thành công',
            'status': status.HTTP_200_OK,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response({
        'message': 'Cập nhật tiêu chí thất bại',
        'status': status.HTTP_400_BAD_REQUEST,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    operation_description='Xóa tiêu chí tìm việc',
    responses={
        200: 'Xóa thành công',
        401: 'Chưa xác thực',
        404: 'Chưa có tiêu chí'
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_criteria(request):
    try:
        criteria = CriteriaEntity.objects.get(user=request.user)
        criteria.delete()
        return Response({
            'message': 'Xóa tiêu chí thành công',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except CriteriaEntity.DoesNotExist:
        return Response({
            'message': 'Bạn chưa có tiêu chí tìm việc',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    operation_description='Lấy danh sách vị trí theo lĩnh vực',
    responses={
        200: openapi.Response(
            description='Thành công',
            schema=PositionSerializer(many=True)
        ),
        404: 'Lĩnh vực không tồn tại'
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_positions_by_field(request, field_id):
    """Lấy danh sách vị trí theo lĩnh vực (không phân trang)"""
    try:
        field = FieldEntity.objects.get(id=field_id)
        positions = PositionEntity.objects.filter(field=field, status='active')
        
        # Serialize tất cả vị trí, không phân trang
        serializer = PositionSerializer(positions, many=True)
        
        # Đảm bảo trả về list kết quả không phân trang
        return Response({
            'message': 'Data retrieved successfully',
            'status': status.HTTP_200_OK,
            'total': len(serializer.data),
            'data': serializer.data
        })
    except FieldEntity.DoesNotExist:
        return Response({
            'message': 'Lĩnh vực không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_field_name(request, field_id):
    try:
        field = FieldEntity.objects.get(id=field_id)
        return Response({
            'message': 'Tên lĩnh vực',
            'name': field.name,
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except FieldEntity.DoesNotExist:
        return Response({
            'message': 'Lĩnh vực không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
@permission_classes([IsEnterpriseOwner])
def toogle_post_status(request, pk):
    try:
        post = PostEntity.objects.get(pk=pk)
        post.is_active = not post.is_active
        # Không thay đổi is_remove_by_admin nữa
        post.save()
        return Response({
            'message': 'Cập nhật trạng thái bài đăng thành công',
            'status': status.HTTP_200_OK
        }, status=status.HTTP_200_OK)
    except PostEntity.DoesNotExist:
        return Response({
            'message': 'Bài đăng không tồn tại',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(
    method='get',
    operation_description="Thống kê dành cho doanh nghiệp",
    responses={
        200: openapi.Response(
            description="Thống kê thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'total_posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số tin tuyển dụng"),
                            'active_posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số tin tuyển dụng đang hoạt động"),
                            'expired_posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số tin tuyển dụng đã hết hạn"),
                            'total_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số ứng viên đã ứng tuyển"),
                            'pending_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đang chờ xử lý"),
                            'approved_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đã duyệt"),
                            'rejected_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đã từ chối"),
                            'total_interviews': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số cuộc phỏng vấn"),
                            'upcoming_interviews': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số cuộc phỏng vấn sắp diễn ra"),
                            'completed_interviews': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số cuộc phỏng vấn đã hoàn thành"),
                            'monthly_stats': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'month': openapi.Schema(type=openapi.TYPE_STRING, description="Tháng (MM/YYYY)"),
                                        'applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên trong tháng"),
                                        'posts': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số tin đăng trong tháng"),
                                    }
                                )
                            ),
                            'post_stats': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của tin tuyển dụng"),
                                        'title': openapi.Schema(type=openapi.TYPE_STRING, description="Tiêu đề tin tuyển dụng"),
                                        'total_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Tổng số ứng viên"),
                                        'pending_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đang chờ xử lý"),
                                        'approved_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đã duyệt"),
                                        'rejected_applicants': openapi.Schema(type=openapi.TYPE_INTEGER, description="Số ứng viên đã từ chối"),
                                    }
                                )
                            )
                        }
                    )
                }
            )
        ),
        403: openapi.Response(
            description="Không có quyền truy cập",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enterprise_statistics(request):
    """
    API thống kê dành cho doanh nghiệp
    """
    # Kiểm tra quyền truy cập
    if not request.user.is_employer() and not request.user.is_superuser:
        return Response({
            'message': 'Bạn không có quyền truy cập',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Lấy doanh nghiệp của người dùng
    enterprise = None
    
    if request.user.is_superuser:
        enterprise_id = request.query_params.get('enterprise_id')
        if enterprise_id:
            try:
                enterprise = EnterpriseEntity.objects.get(id=enterprise_id)
            except EnterpriseEntity.DoesNotExist:
                return Response({
                    'message': 'Doanh nghiệp không tồn tại',
                    'status': status.HTTP_404_NOT_FOUND
                }, status=status.HTTP_404_NOT_FOUND)
    else:
        enterprise = request.user.enterprises.first()
        
    if not enterprise:
        return Response({
            'message': 'Bạn chưa có doanh nghiệp',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Thống kê tin tuyển dụng
    from django.utils import timezone
    from datetime import datetime, timedelta
    from django.db.models import Count, Q
    
    # Lấy tất cả bài đăng của doanh nghiệp
    posts = PostEntity.objects.filter(enterprise=enterprise)
    total_posts = posts.count()
    active_posts = posts.filter(is_active=True, deadline__gt=timezone.now().date()).count()
    expired_posts = total_posts - active_posts
    
    # Thống kê ứng viên
    from profiles.models import Cv
    
    # Lấy tất cả CV ứng tuyển vào các bài đăng của doanh nghiệp
    cvs = Cv.objects.filter(post__enterprise=enterprise)
    total_applicants = cvs.count()
    pending_applicants = cvs.filter(status='pending').count()
    approved_applicants = cvs.filter(status='approved').count()
    rejected_applicants = cvs.filter(status='rejected').count()
    
    # Thống kê phỏng vấn
    from interviews.models import Interview
    
    interviews = Interview.objects.filter(enterprise=enterprise)
    total_interviews = interviews.count()
    upcoming_interviews = interviews.filter(
        interview_date__gt=timezone.now(),
        status__in=['pending', 'accepted']
    ).count()
    completed_interviews = interviews.filter(status='completed').count()
    
    # Thống kê theo tháng (6 tháng gần nhất)
    end_date = timezone.now().date()
    start_date = (end_date - timedelta(days=180))
    
    # Khởi tạo mảng các tháng
    monthly_stats = []
    current_date = start_date
    while current_date <= end_date:
        month_start = datetime(current_date.year, current_date.month, 1).date()
        if current_date.month == 12:
            month_end = datetime(current_date.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(current_date.year, current_date.month + 1, 1).date() - timedelta(days=1)
        
        # Đếm số ứng viên trong tháng
        month_applicants = cvs.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        
        # Đếm số tin đăng trong tháng
        month_posts = posts.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        
        monthly_stats.append({
            'month': month_start.strftime('%m/%Y'),
            'applicants': month_applicants,
            'posts': month_posts
        })
        
        # Chuyển sang tháng tiếp theo
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1).date()
    
    # Thống kê chi tiết theo từng bài đăng (10 bài đăng gần nhất)
    post_stats = []
    recent_posts = posts.order_by('-created_at')[:10]
    
    for post in recent_posts:
        post_cvs = Cv.objects.filter(post=post)
        post_stats.append({
            'id': post.id,
            'title': post.title,
            'total_applicants': post_cvs.count(),
            'pending_applicants': post_cvs.filter(status='pending').count(),
            'approved_applicants': post_cvs.filter(status='approved').count(),
            'rejected_applicants': post_cvs.filter(status='rejected').count(),
        })
    
    # Tổng hợp dữ liệu
    data = {
        'total_posts': total_posts,
        'active_posts': active_posts,
        'expired_posts': expired_posts,
        'total_applicants': total_applicants,
        'pending_applicants': pending_applicants,
        'approved_applicants': approved_applicants,
        'rejected_applicants': rejected_applicants,
        'total_interviews': total_interviews,
        'upcoming_interviews': upcoming_interviews,
        'completed_interviews': completed_interviews,
        'monthly_stats': monthly_stats,
        'post_stats': post_stats
    }
    
    return Response({
        'message': 'Thống kê thành công',
        'status': status.HTTP_200_OK,
        'data': data
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='post',
    operation_description="Lưu bài đăng việc làm",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['post_id'],
        properties={
            'post_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID của bài đăng cần lưu"),
        }
    ),
    responses={
        201: openapi.Response(
            description="Bài đăng đã được lưu thành công",
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
            description="Lỗi khi lưu bài đăng",
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
            description="Không tìm thấy bài đăng",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_post(request):
    """Lưu bài đăng việc làm"""
    post_id = request.data.get('post_id')
    
    try:
        post = PostEntity.objects.get(id=post_id)
    except PostEntity.DoesNotExist:
        return Response({
            'message': 'Không tìm thấy bài đăng',
            'status': 404
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Kiểm tra xem bài đăng đã được lưu chưa
    saved_post, created = SavedPostEntity.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        return Response({
            'message': 'Bài đăng đã được lưu trước đó',
            'status': 400,
            'errors': {'post': ['Bài đăng này đã được lưu trước đó']}
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = SavedPostSerializer(saved_post)
    
    return Response({
        'message': 'Lưu bài đăng thành công',
        'status': 201,
        'data': serializer.data
    }, status=status.HTTP_201_CREATED)

@swagger_auto_schema(
    method='get',
    operation_description="Lấy danh sách bài đăng đã lưu của người dùng",
    manual_parameters=[
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
    ],
    responses={
        200: openapi.Response(
            description="Thành công",
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
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_saved_posts(request):
    """Lấy danh sách bài đăng đã lưu của người dùng"""
    saved_posts = SavedPostEntity.objects.filter(user=request.user).order_by('-created_at')
    
    # Phân trang
    page = request.query_params.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1
    
    page_size = request.query_params.get('page_size', 10)
    try:
        page_size = int(page_size)
    except ValueError:
        page_size = 10
    
    paginator = Paginator(saved_posts, page_size)
    total_pages = paginator.num_pages
    
    try:
        current_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        current_page = paginator.page(1)
        page = 1
    
    serializer = SavedPostSerializer(current_page, many=True, context={'request': request})
    
    return Response({
        'message': 'Lấy danh sách bài đăng đã lưu thành công',
        'status': 200,
        'data': {
            'total': paginator.count,
            'page': page,
            'total_pages': total_pages,
            'page_size': page_size,
            'results': serializer.data
        }
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa bài đăng đã lưu",
    responses={
        200: openapi.Response(
            description="Xóa thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Không tìm thấy bài đăng đã lưu",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_saved_post(request, pk):
    """Xóa bài đăng đã lưu"""
    try:
        saved_post = SavedPostEntity.objects.get(id=pk, user=request.user)
    except SavedPostEntity.DoesNotExist:
        return Response({
            'message': 'Không tìm thấy bài đăng đã lưu',
            'status': 404
        }, status=status.HTTP_404_NOT_FOUND)
    
    saved_post.delete()
    
    return Response({
        'message': 'Đã xóa bài đăng đã lưu',
        'status': 200
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='delete',
    operation_description="Xóa bài đăng đã lưu theo ID bài đăng",
    responses={
        200: openapi.Response(
            description="Xóa thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        404: openapi.Response(
            description="Không tìm thấy bài đăng đã lưu",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_saved_post_by_post_id(request, post_id):
    """Xóa bài đăng đã lưu theo ID bài đăng"""
    try:
        saved_post = SavedPostEntity.objects.get(post_id=post_id, user=request.user)
    except SavedPostEntity.DoesNotExist:
        return Response({
            'message': 'Không tìm thấy bài đăng đã lưu',
            'status': 404
        }, status=status.HTTP_404_NOT_FOUND)
    
    saved_post.delete()
    
    return Response({
        'message': 'Đã xóa bài đăng đã lưu',
        'status': 200
    }, status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='get',
    operation_description="Kiểm tra xem người dùng đã lưu bài đăng hay chưa",
    responses={
        200: openapi.Response(
            description="Thành công",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'is_saved': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'saved_post_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True)
                }
            )
        )
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_post_saved(request, post_id):
    """Kiểm tra xem người dùng đã lưu bài đăng hay chưa"""
    try:
        saved_post = SavedPostEntity.objects.get(post_id=post_id, user=request.user)
        return Response({
            'message': 'Đã lưu bài đăng này',
            'status': 200,
            'is_saved': True,
            'saved_post_id': saved_post.id
        }, status=status.HTTP_200_OK)
    except SavedPostEntity.DoesNotExist:
        return Response({
            'message': 'Chưa lưu bài đăng này',
            'status': 200,
            'is_saved': False,
            'saved_post_id': None
        }, status=status.HTTP_200_OK)
    

@api_view(['GET'])
@permission_classes([IsEnterpriseOwner])
def get_enterprise_post_detail(request, pk):
    """
    API để lấy chi tiết bài đăng cho enterprise
    """
    try:
        post = PostEntity.objects.get(pk=pk)
        
        # Kiểm tra xem người dùng có phải là chủ doanh nghiệp của bài đăng không
        if post.enterprise.user != request.user:
            return Response({
                'message': 'Bạn không có quyền xem chi tiết bài đăng này',
                'status': 403
            }, status=status.HTTP_403_FORBIDDEN)
            
        serializer = EnterprisePostDetailSerializer(post)
        return Response({
            'message': 'Lấy chi tiết bài đăng thành công',
            'status': 200,
            'data': serializer.data
        })
    except PostEntity.DoesNotExist:
        return Response({
            'detail': 'Không tìm thấy bài đăng',
            'status': 404
        }, status=status.HTTP_404_NOT_FOUND)