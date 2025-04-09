from concurrent.futures import ThreadPoolExecutor
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from .serializers import (
    EnterpriseDetailSerializer, EnterpriseSerializer, PostEnterpriseSerializer, PostSerializer,
    FieldSerializer, PositionSerializer, CriteriaSerializer,
    PostUpdateSerializer
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
from django.core.cache import cache
from django.utils.http import urlencode
import os

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
    sort = request.query_params.get('sort', '-created_at')
    posts = PostEntity.objects.filter(is_active=True)
    if (sort == '-salary_max'):
        posts = posts.order_by('-salary_max')
    elif (sort == '-salary_min'):
        posts = posts.order_by('-salary_min')
    elif (sort == '-created_at'):
        posts = posts.order_by('-created_at')
    # Phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostSerializer(paginated_posts, many=True)
    return paginator.get_paginated_response(serializer.data)


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
    posts = posts.order_by('-created_at')
    # phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    serializer = PostEnterpriseSerializer(paginated_posts, many=True)
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
    serializer = PostSerializer(posts, many=True)
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
    serializer = PostSerializer(paginated_posts, many=True)
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
    posts = PostEntity.objects.filter(is_active=True)
    
    # Phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostSerializer(paginated_posts, many=True)
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
    # Tạo cache key dựa trên tất cả các tham số tìm kiếm
    params = {}
    
    # Lấy các tham số và chỉ thêm vào dict nếu có giá trị
    for key in ['q', 'city', 'position', 'experience', 'type_working']:
        value = request.query_params.get(key, '')
        if value:
            params[key] = value
            
    # Xử lý các tham số số nguyên
    for key in ['salary_min', 'salary_max']:
        value = request.query_params.get(key)
        if value and value.isdigit():
            params[key] = value
            
    # Xử lý tham số boolean negotiable
    negotiable = request.query_params.get('negotiable')
    if negotiable in ['true', 'false']:
        params['negotiable'] = negotiable
        
    # Thêm các tham số phân trang và sắp xếp
    params['sort_by'] = request.query_params.get('sort_by', '-created_at')
    params['sort_order'] = request.query_params.get('sort_order', 'desc')
    params['page'] = request.query_params.get('page', '1')
    params['page_size'] = request.query_params.get('page_size', '10')
    
    cache_key = f'posts_search_{urlencode(params)}'
    
    # Kiểm tra cache
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        return Response(cached_response)
    
    # Nếu không có trong cache, thực hiện tìm kiếm
    posts = PostEntity.objects.select_related('position', 'enterprise', 'field').filter(is_active=True)
    
    # Tạo Q objects cho việc tìm kiếm
    search_conditions = Q()
    if params.get('q'):
        search_conditions |= (
            Q(title__icontains=params['q']) |
            Q(description__icontains=params['q']) |
            Q(required__icontains=params['q']) |
            Q(enterprise__company_name__icontains=params['q'])
        )
        posts = posts.filter(search_conditions)
    
    # Áp dụng các bộ lọc chính xác
    if params.get('city'):
        posts = posts.filter(city__iexact=params['city'])
    if params.get('position'):
        posts = posts.filter(position__name__iexact=params['position'])
    if params.get('experience'):
        posts = posts.filter(experience__iexact=params['experience'])
    if params.get('type_working'):
        posts = posts.filter(type_working__iexact=params['type_working'])
    
    # Xử lý lọc theo khoảng lương
    if params.get('salary_min') and params.get('salary_max'):
        posts = posts.filter(
            salary_min__gte=params['salary_min'],
            salary_max__lte=params['salary_max'],
            is_salary_negotiable=False
        )
    elif params.get('salary_min'):
        posts = posts.filter(
            salary_min__gte=params['salary_min'],
            is_salary_negotiable=False
        )
    elif params.get('salary_max'):
        posts = posts.filter(
            salary_max__lte=params['salary_max'],
            is_salary_negotiable=False
        )
    
    # Lọc lương thỏa thuận
    if params.get('negotiable') == 'true':
        posts = posts.filter(is_salary_negotiable=True)
    
    # Sắp xếp kết quả
    sort_by = params['sort_by']
    if params['sort_order'] == 'desc' and not sort_by.startswith('-'):
        sort_by = f'-{sort_by}'
    
    # Thực hiện sắp xếp và đánh index
    posts = posts.order_by(sort_by).distinct()
    
    # Phân trang
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostSerializer(paginated_posts, many=True)
    response_data = paginator.get_paginated_response(serializer.data).data
    
    # Lưu kết quả vào cache
    cache.set(cache_key, response_data)
    
    return Response(response_data)

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
            Q(enterprise__scale__iexact=criteria.scales) |
            Q(position=criteria.position) |
            Q(enterprise__field_of_activity__icontains=criteria.field.name)
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
        post = PostEntity.objects.select_related('enterprise').get(pk=pk)
        serializer = PostSerializer(post)
        data = serializer.data
        # Thêm thông tin ảnh của doanh nghiệp
        data['enterprise_logo'] = post.enterprise.logo_url
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
        criteria = CriteriaEntity.objects.get(user=request.user)
        
        # Phân trang
        paginator = CustomPagination()
        paginated_criteria = paginator.paginate_queryset([criteria], request)
        
        serializer = CriteriaSerializer(paginated_criteria, many=True)
        return paginator.get_paginated_response(serializer.data)
    except CriteriaEntity.DoesNotExist:
        return Response({
            'message': 'Bạn chưa có tiêu chí tìm việc',
            'status': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)

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

