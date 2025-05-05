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
    EnterpriseDetailSerializer, EnterpriseSerializer, PostEnterpriseSerializer, PostSerializer,
    FieldSerializer, PositionSerializer, CriteriaSerializer,
    PostUpdateSerializer, PostEnterpriseForEmployerSerializer, SavedPostSerializer
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
    cache_key = f'posts_basic_data_{sort}_{page}_{page_size}'
    
    # Thử lấy post IDs từ cache
    cached_post_ids = cache.get(cache_key)
    
    if cached_post_ids is None:
        # Nếu không có trong cache, thực hiện truy vấn để lấy post IDs
        posts = PostEntity.objects.filter(
            is_active=True, 
            deadline__gt=datetime.now()
        ).select_related(
            'position', 
            'enterprise', 
            'field'
        )
        
        # Sắp xếp cơ bản theo tham số
    if (sort == '-salary_max'):
        posts = posts.order_by('-salary_max')
    elif (sort == '-salary_min'):
        posts = posts.order_by('-salary_min')
    elif (sort == '-created_at'):
        posts = posts.order_by('-created_at')
            
        # # Lấy danh sách ID bài đăng theo thứ tự cơ bản
        # post_ids = list(posts.values_list('id', flat=True))
        
        # # Cần thông tin enterprise_id để sắp xếp theo premium
        # post_data = list(posts.values('id', 'enterprise_id', 'created_at'))
        
        # # Tìm doanh nghiệp liên quan đến các bài đăng
        # enterprise_ids = {post['enterprise_id'] for post in post_data}
        
        # # Lấy thông tin priority coefficient từ cache
        # priority_cache_key = 'enterprise_priority_coefficients'
        # priority_coefficients = cache.get(priority_cache_key, {})
        
        # # Chỉ truy vấn các doanh nghiệp chưa có trong cache
        # missing_enterprise_ids = [eid for eid in enterprise_ids if eid not in priority_coefficients]
        
        # if missing_enterprise_ids:
        #     # Lấy thông tin doanh nghiệp
        #     enterprises = EnterpriseEntity.objects.filter(
        #         id__in=missing_enterprise_ids
        #     ).select_related('user')
            
        #     # Map user_id to enterprise_id
        #     user_to_enterprise = {e.user_id: e.id for e in enterprises}
            
        #     # Lấy premium histories hiệu quả với một truy vấn
        #     premium_histories = PremiumHistory.objects.filter(
        #         user_id__in=user_to_enterprise.keys(),
        #         is_active=True,
        #         is_cancelled=False,
        #         end_date__gt=timezone.now()
        #     ).select_related('package')
            
        #     # Map user_id to premium_history hiệu quả
        #     user_premiums = {}
        #     for ph in premium_histories:
        #         if ph.user_id not in user_premiums:
        #             user_premiums[ph.user_id] = ph
            
        #     # Tính toán priority coefficients cho các doanh nghiệp thiếu
        #     for enterprise in enterprises:
        #         premium = user_premiums.get(enterprise.user_id)
        #         if premium and premium.package:
        #             priority_coefficients[enterprise.id] = premium.package.priority_coefficient
        #         else:
        #             priority_coefficients[enterprise.id] = 999
            
        #     # Lưu vào cache trong 1 giờ
        #     cache.set(priority_cache_key, priority_coefficients, 60 * 60)
        
        # # Sắp xếp post_data theo hệ số ưu tiên
        # post_data.sort(key=lambda post: (
        #     priority_coefficients.get(post['enterprise_id'], 999),
        #     -(post['created_at'].timestamp() if isinstance(post['created_at'], datetime) else 0)
        # ))
        
        # # Lấy ID bài đăng theo thứ tự mới
        # sorted_ids = [post['id'] for post in post_data]
        
        # # Cache danh sách ID đã sắp xếp
        # cache.set(cache_key, sorted_ids, 60 * 5)  # Cache trong 5 phút
    # else:
    #     sorted_ids = cached_post_ids

    # # Lấy dữ liệu posts từ database với các ID đã sắp xếp
    # if sorted_ids:
    #     from django.db import models  # Import models namespace
        
    #     order_clause = models.Case(
    #         *[models.When(id=pk, then=models.Value(pos)) for pos, pk in enumerate(sorted_ids)],
    #         output_field=models.IntegerField()
    #     )
        
    #     ordered_posts = PostEntity.objects.filter(
    #         id__in=sorted_ids
    #     ).select_related(
    #         'position', 
    #         'enterprise', 
    #         'field'
    #     ).order_by(order_clause)
    # else:
    #     ordered_posts = PostEntity.objects.none()
    
    # Phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    # Serialize với context để tính toán các trường động như is_saved
    serializer = PostSerializer(paginated_posts, many=True, context={'request': request})
    response_data = paginator.get_paginated_response(serializer.data).data
    
    time_end = datetime.now()
    print(f"Time taken: {time_end - time_start} seconds")

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
    posts = PostEntity.objects.filter(is_active=True, deadline__gt=datetime.now())
    
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
    # Tạo cache key dựa trên tất cả các tham số tìm kiếm:
    # - q (từ khóa tìm kiếm)
    # - city (thành phố)
    # - field (lĩnh vực)
    # - scale (quy mô)
    # - sort_by (trường sắp xếp)
    # - sort_order (thứ tự sắp xếp)
    # - page (số trang)
    # - page_size (số lượng doanh nghiệp mỗi trang)
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
    
    # Kiểm tra xem kết quả đã được cache chưa:
    # - Nếu có trong cache thì trả về kết quả ngay lập tức
    # - Nếu không có trong cache thì thực hiện tìm kiếm bình thường
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
    
    # Sau khi tìm kiếm xong, lưu kết quả vào cache với thời gian sống là 5 phút (theo cấu hình trong settings.py)
    cache.set(cache_key, response_data)
    
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
    
    # Lấy các tham số và tạo cache key
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
    
    time_params = datetime.now()
    print(f"Parameters processing time: {time_params - time_start} seconds")
    
    # Kiểm tra cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        time_end = datetime.now()
        print(f"Cache hit! Time taken: {time_end - time_start} seconds")
        return Response(cached_data)
    
    # Bắt đầu xây dựng query (chưa thực thi cho đến khi cần thiết)
    query = PostEntity.objects.filter(
        is_active=True,
        deadline__gte=datetime.now()
    )
    
    # Áp dụng bộ lọc tìm kiếm từ params nếu có (chưa thực thi truy vấn)
    if params.get('q'):
        search_term = params.get('q')
        query = query.filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(required__icontains=search_term) |
            Q(enterprise__company_name__icontains=search_term)
        )
    if params.get('city'):
        query = query.filter(city__iexact=params.get('city'))

    if params.get('experience'):
        query = query.filter(experience__iexact=params.get('experience'))

    if params.get('type_working'):
        query = query.filter(type_working__iexact=params.get('type_working'))

    if params.get('scales'):
        query = query.filter(enterprise__scale__iexact=params.get('scales'))

    if params.get('position'):
        position_param = params.get('position')
        if position_param.isdigit():
            query = query.filter(position__id=int(position_param))
        else:
            query = query.filter(position__name__icontains=position_param)

    if params.get('field'):
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

    if params.get('salary_min'):
        query = query.filter(salary_min__gte=int(params.get('salary_min')))

    if params.get('salary_max'):
        query = query.filter(salary_max__lte=int(params.get('salary_max')))

    if params.get('negotiable') == 'true':
        query = query.filter(is_salary_negotiable=True)
    
    time_query_build = datetime.now()
    print(f"Query building time: {time_query_build - time_params} seconds")
    
    # Cải thiện hiệu suất bằng select_related trước khi thực hiện truy vấn
    filtered_query = query.select_related(
        'position', 
        'field', 
        'enterprise'
    )
    
    # Chỉ lấy các trường cần thiết cho việc tính điểm và sắp xếp
    post_data = list(filtered_query.values(
        'id', 'title', 'city', 'experience', 'type_working', 
        'salary_min', 'salary_max', 'is_salary_negotiable', 'created_at',
        'enterprise_id', 'position_id', 'field_id',
        'enterprise__scale', 'position__field_id'
    ))
    
    time_initial_query = datetime.now()
    print(f"Initial query execution time: {time_initial_query - time_query_build} seconds")
    
    # **Bỏ logic lấy toàn bộ bài đăng khi không có kết quả và all=true**
    # Thay vào đó, nếu post_data rỗng và q được cung cấp, trả về danh sách rỗng
    if not post_data and params.get('q'):
        empty_data = {
            'message': 'No matching posts found',
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
    
    # Lấy thông tin user criteria nếu đã đăng nhập
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
        enterprise_users = {}
        for item in EnterpriseEntity.objects.filter(id__in=missing_enterprise_ids).values('id', 'user_id'):
            enterprise_users[item['id']] = item['user_id']
        
        if enterprise_users:
            user_ids = list(enterprise_users.values())
            user_premium_coefficients = {}
            
            for ph in PremiumHistory.objects.filter(
                user_id__in=user_ids,
                is_active=True,
                is_cancelled=False,
                end_date__gt=timezone.now()
            ).select_related('package').values('user_id', 'package__priority_coefficient'):
                user_premium_coefficients[ph['user_id']] = ph['package__priority_coefficient']
            
            for enterprise_id, user_id in enterprise_users.items():
                coefficient = user_premium_coefficients.get(user_id)
                enterprise_premium_coefficients[enterprise_id] = coefficient if coefficient else 999
            
            cache.set(priority_cache_key, enterprise_premium_coefficients, 60 * 60)
    
    time_premium_fetch = datetime.now()
    print(f"Premium data fetch time: {time_premium_fetch - time_initial_query} seconds")
    
    # Tính điểm và priority cho mỗi post
    scored_posts = []
    for post in post_data:
        score = 0
        post_obj = {**post}
        
        if user_criteria:
            if user_criteria.city and post['city'] and post['city'].lower() == user_criteria.city.lower():
                score += 4
            if user_criteria.experience and post['experience'] and post['experience'].lower() == user_criteria.experience.lower():
                score += 3
            if user_criteria.type_working and post['type_working'] and post['type_working'].lower() == user_criteria.type_working.lower():
                score += 3
            if user_criteria.scales and post['enterprise__scale'] and post['enterprise__scale'].lower() == user_criteria.scales.lower():
                score += 2
            if user_criteria.field:
                if (post['field_id'] and post['field_id'] == user_criteria.field.id) or \
                   (post['position__field_id'] and post['position__field_id'] == user_criteria.field.id):
                    score += 5
            if user_criteria.position and post['position_id'] and post['position_id'] == user_criteria.position.id:
                score += 5
            if user_criteria.salary_min and post['salary_min'] and post['salary_min'] >= user_criteria.salary_min:
                score += 3
        
        if params.get('city') and post['city'] and post['city'].lower() == params.get('city').lower():
            score += 4
        if params.get('experience') and post['experience'] and post['experience'].lower() == params.get('experience').lower():
            score += 3
        if params.get('type_working') and post['type_working'] and post['type_working'].lower() == params.get('type_working').lower():
            score += 3
        if params.get('scales') and post['enterprise__scale'] and post['enterprise__scale'].lower() == params.get('scales').lower():
            score += 2
        
        post_obj['match_score'] = score
        post_obj['matches_criteria'] = score >= 7
        post_obj['priority_coefficient'] = enterprise_premium_coefficients.get(post['enterprise_id'], 999)
        post_obj['is_enterprise_premium'] = post_obj['priority_coefficient'] < 999
        
        scored_posts.append(post_obj)
    
    time_scoring = datetime.now()
    print(f"Post scoring time: {time_scoring - time_premium_fetch} seconds")
    
    # Lọc và sắp xếp posts theo tiêu chí
    if params.get('all') == 'false':
        filtered_posts = [post for post in scored_posts if post['matches_criteria']]
    else:
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
        empty_data = {
            'message': 'No matching posts found',
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
    
    # Tiếp tục xử lý phân trang và trả về kết quả như trong code gốc
    post_info_map = {post['id']: post for post in filtered_posts}
    
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 10))
    
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, len(sorted_post_ids))
    
    current_page_ids = sorted_post_ids[start_idx:end_idx]
    
    time_pagination = datetime.now()
    print(f"Pagination time: {time_pagination - time_sorting} seconds")
    
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
    
    posts_with_relations = PostEntity.objects.filter(
        id__in=current_page_ids
    ).select_related(
        'position', 
        'field', 
        'enterprise'
    ).only(
        'id', 'title', 'description', 'required', 'type_working',
        'salary_min', 'salary_max', 'is_salary_negotiable', 'quantity',
        'city', 'created_at', 'deadline', 'is_active', 'interest', 'district',
        'position_id', 'field_id', 'enterprise_id'
    )
    
    position_map = {id: idx for idx, id in enumerate(current_page_ids)}
    sorted_results = sorted(posts_with_relations, key=lambda post: position_map.get(post.id, 999))
    
    time_fetch_detail = datetime.now()
    print(f"Fetch detail time: {time_fetch_detail - time_pagination} seconds")
    
    for post in sorted_results:
        post_info = post_info_map.get(post.id, {})
        
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
    
    response_data = {
        'message': 'Data retrieved successfully',
        'status': status.HTTP_200_OK,
        "test": "test",
        'data': paged_data
    }
    
    time_end = datetime.now()
    print(f"------------------------")
    print(f"Parameters processing:  {time_params - time_start} seconds")
    print(f"Query building:         {time_query_build - time_params} seconds")
    print(f"Initial data fetch:     {time_initial_query - time_query_build} seconds")
    print(f"Premium data fetch:     {time_premium_fetch - time_initial_query} seconds")
    print(f"Post scoring:           {time_scoring - time_premium_fetch} seconds")
    print(f"Sorting:                {time_sorting - time_scoring} seconds")
    print(f"Pagination:             {time_pagination - time_sorting} seconds")
    print(f"Detail data fetch:      {time_fetch_detail - time_pagination} seconds")
    print(f"Data transformation:    {time_transform - time_fetch_detail} seconds")
    print(f"Cache & response:       {time_end - time_transform} seconds")
    print(f"------------------------")
    print(f"TOTAL SEARCH TIME:      {time_end - time_start} seconds")
    
    cache.set(cache_key, response_data, 60 * 5)
    return Response(response_data)
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
            Q(enterprise__scale__iexact=criteria.scales) |
            Q(position=criteria.position) |
            Q(enterprise__field_of_activity__icontains=criteria.field.name)
        ).distinct()
        
        # Sắp xếp theo độ phù hợp (có thể thêm logic tính điểm phù hợp ở đây)
        posts = posts.order_by('-created_at')
        
        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)
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
        from django.db.models import Count
        from profiles.models import Cv
        
        post = PostEntity.objects.select_related('enterprise').get(pk=pk)
        serializer = PostSerializer(post)
        data = serializer.data
        
        # Thêm thông tin ảnh của doanh nghiệp
        data['enterprise_logo'] = post.enterprise.logo_url
        data['user_id'] = post.enterprise.user.id
        data['is_enterprise_premium'] = post.enterprise.user.is_premium
        data['enterprise_address'] = post.enterprise.address
        # Tính tổng số ứng viên đã ứng tuyển
        total_applicants = Cv.objects.filter(post=post).count()
        
        if request.user.is_authenticated:
            # Nếu là chủ doanh nghiệp hoặc có quyền xem số lượng ứng viên
            if (post.enterprise.user == request.user) or (request.user.is_premium):
                data['total_applicants'] = total_applicants
                data['can_view_applicants'] = True
            else:
                data['can_view_applicants'] = False
                # Nếu là người dùng không có quyền, ẩn số lượng ứng viên
                if total_applicants > 0:
                    data['has_applicants'] = True
                else:
                    data['has_applicants'] = False
        else:
            # Người dùng chưa đăng nhập
            data['can_view_applicants'] = False
            if total_applicants > 0:
                data['has_applicants'] = True
            else:
                data['has_applicants'] = False
                
        # Kiểm tra quyền chat
        if request.user.is_authenticated and not request.user.is_employer():
            data['can_chat_with_employer'] = request.user.can_chat_with_employers()
        else:
            data['can_chat_with_employer'] = False
        # lấy ngày ứng tuyển gần nhất của user đang đăng nhập
        if request.user.is_authenticated:
            latest_application = Cv.objects.filter(post=post, user=request.user).order_by('-created_at').first()
            if latest_application:
                data['latest_application_date'] = latest_application.created_at.strftime('%d/%m/%Y')
            else:
                data['latest_application_date'] = None
        else:
            data['latest_application_date'] = None
        return Response({
            'message': 'Post details retrieved successfully',
            'status': status.HTTP_200_OK,
            'data': data
        })
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
@permission_classes([IsAuthenticated])
def get_positions(request):
    positions = PositionEntity.objects.all()
    
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
    try:
        field = FieldEntity.objects.get(id=field_id)
        positions = PositionEntity.objects.filter(field=field, status='active')
        
        # Phân trang
        paginator = CustomPagination()
        paginated_positions = paginator.paginate_queryset(positions, request)
        
        serializer = PositionSerializer(paginated_positions, many=True)
        return paginator.get_paginated_response(serializer.data)
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