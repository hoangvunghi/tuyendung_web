from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, Avg, F, Q, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from enterprises.models import EnterpriseEntity, PostEntity
from profiles.models import Cv
from base.permissions import IsEnterpriseOwner
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.cache import cache
from django.utils.http import urlencode

# Create your views here.

# API cho thống kê tổng quan của doanh nghiệp
@swagger_auto_schema(
    method='get',
    operation_description="Thống kê tổng quan của doanh nghiệp: số bài đăng, số CV nhận được, tỷ lệ chuyển đổi",
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
                            'total_posts': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'active_posts': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_cvs': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'cv_status_counts': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'approved': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'rejected': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            ),
                            'conversion_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                        }
                    )
                }
            )
        ),
        403: openapi.Response(description="Không có quyền truy cập"),
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_enterprise_overview(request):
    # Lấy doanh nghiệp của người dùng hiện tại
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Tạo cache key dựa trên enterprise ID
    cache_key = f'enterprise_overview_{enterprise.id}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Thống kê số bài đăng
    total_posts = PostEntity.objects.filter(enterprise=enterprise).count()
    active_posts = PostEntity.objects.filter(enterprise=enterprise, is_active=True).count()
    
    # Lấy danh sách bài đăng của doanh nghiệp
    posts = PostEntity.objects.filter(enterprise=enterprise)
    post_ids = posts.values_list('id', flat=True)
    
    # Thống kê tổng số CV
    total_cvs = Cv.objects.filter(post__in=post_ids).count()
    
    # Thống kê số CV theo trạng thái
    cv_status_counts = {
        'pending': Cv.objects.filter(post__in=post_ids, status='pending').count(),
        'approved': Cv.objects.filter(post__in=post_ids, status='approved').count(),
        'rejected': Cv.objects.filter(post__in=post_ids, status='rejected').count(),
    }
    
    # Tính tỷ lệ chuyển đổi (số CV / số lượt xem bài đăng)
    conversion_rate = 0
    if total_posts > 0:
        conversion_rate = round(total_cvs / total_posts, 2)
    
    data = {
        'message': 'Thống kê tổng quan của doanh nghiệp',
        'status': status.HTTP_200_OK,
        'data': {
            'total_posts': total_posts,
            'active_posts': active_posts,
            'total_cvs': total_cvs,
            'cv_status_counts': cv_status_counts,
            'conversion_rate': conversion_rate,
        }
    }
    
    # Lưu vào cache trong 30 phút
    cache.set(cache_key, data, timeout=1800)
    
    return Response(data)

# API cho thống kê bài đăng theo thời gian
@swagger_auto_schema(
    method='get',
    operation_description="Thống kê bài đăng theo thời gian",
    manual_parameters=[
        openapi.Parameter(
            'period', openapi.IN_QUERY, 
            description="Khoảng thời gian (daily, weekly, monthly)", 
            type=openapi.TYPE_STRING,
            enum=['daily', 'weekly', 'monthly'],
            default='monthly'
        ),
        openapi.Parameter(
            'from_date', openapi.IN_QUERY, 
            description="Từ ngày (YYYY-MM-DD)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'to_date', openapi.IN_QUERY, 
            description="Đến ngày (YYYY-MM-DD)", 
            type=openapi.TYPE_STRING,
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
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'period': openapi.Schema(type=openapi.TYPE_STRING),
                                'post_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    )
                }
            )
        ),
        403: openapi.Response(description="Không có quyền truy cập"),
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_post_stats_by_time(request):
    # Lấy doanh nghiệp của người dùng hiện tại
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Lấy các tham số từ request
    period = request.query_params.get('period', 'monthly')
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    # Tạo cache key
    cache_params = {
        'enterprise_id': enterprise.id,
        'period': period,
        'from_date': from_date,
        'to_date': to_date
    }
    cache_key = f'post_stats_time_{urlencode(cache_params)}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Lọc bài đăng của doanh nghiệp
    posts_query = PostEntity.objects.filter(enterprise=enterprise)
    
    # Lọc theo ngày nếu có
    if from_date:
        posts_query = posts_query.filter(created_at__gte=from_date)
    if to_date:
        posts_query = posts_query.filter(created_at__lte=to_date)
    
    # Nhóm theo khoảng thời gian
    if period == 'daily':
        posts_by_period = posts_query.annotate(
            period=TruncDay('created_at')
        ).values('period').annotate(
            post_count=Count('id')
        ).order_by('period')
    elif period == 'weekly':
        posts_by_period = posts_query.annotate(
            period=TruncWeek('created_at')
        ).values('period').annotate(
            post_count=Count('id')
        ).order_by('period')
    else:  # monthly
        posts_by_period = posts_query.annotate(
            period=TruncMonth('created_at')
        ).values('period').annotate(
            post_count=Count('id')
        ).order_by('period')
    
    # Định dạng kết quả
    result = [
        {
            'period': item['period'].strftime('%Y-%m-%d'),
            'post_count': item['post_count']
        }
        for item in posts_by_period
    ]
    
    data = {
        'message': f'Thống kê bài đăng theo thời gian ({period})',
        'status': status.HTTP_200_OK,
        'data': result
    }
    
    # Lưu vào cache trong 1 giờ
    cache.set(cache_key, data, timeout=3600)
    
    return Response(data)

# API cho thống kê CV theo thời gian
@swagger_auto_schema(
    method='get',
    operation_description="Thống kê CV theo thời gian",
    manual_parameters=[
        openapi.Parameter(
            'period', openapi.IN_QUERY, 
            description="Khoảng thời gian (daily, weekly, monthly)", 
            type=openapi.TYPE_STRING,
            enum=['daily', 'weekly', 'monthly'],
            default='monthly'
        ),
        openapi.Parameter(
            'from_date', openapi.IN_QUERY, 
            description="Từ ngày (YYYY-MM-DD)", 
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'to_date', openapi.IN_QUERY, 
            description="Đến ngày (YYYY-MM-DD)", 
            type=openapi.TYPE_STRING,
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
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'period': openapi.Schema(type=openapi.TYPE_STRING),
                                'cv_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    )
                }
            )
        ),
        403: openapi.Response(description="Không có quyền truy cập"),
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_cv_stats_by_time(request):
    # Lấy doanh nghiệp của người dùng hiện tại
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Lấy các tham số từ request
    period = request.query_params.get('period', 'monthly')
    from_date = request.query_params.get('from_date')
    to_date = request.query_params.get('to_date')
    
    # Tạo cache key
    cache_params = {
        'enterprise_id': enterprise.id,
        'period': period,
        'from_date': from_date,
        'to_date': to_date
    }
    cache_key = f'cv_stats_time_{urlencode(cache_params)}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Lấy ID các bài đăng của doanh nghiệp
    post_ids = PostEntity.objects.filter(enterprise=enterprise).values_list('id', flat=True)
    
    # Lọc CV theo bài đăng của doanh nghiệp
    cv_query = Cv.objects.filter(post__in=post_ids)
    
    # Lọc theo ngày nếu có
    if from_date:
        cv_query = cv_query.filter(created_at__gte=from_date)
    if to_date:
        cv_query = cv_query.filter(created_at__lte=to_date)
    
    # Nhóm theo khoảng thời gian
    if period == 'daily':
        cvs_by_period = cv_query.annotate(
            period=TruncDay('created_at')
        ).values('period').annotate(
            cv_count=Count('id')
        ).order_by('period')
    elif period == 'weekly':
        cvs_by_period = cv_query.annotate(
            period=TruncWeek('created_at')
        ).values('period').annotate(
            cv_count=Count('id')
        ).order_by('period')
    else:  # monthly
        cvs_by_period = cv_query.annotate(
            period=TruncMonth('created_at')
        ).values('period').annotate(
            cv_count=Count('id')
        ).order_by('period')
    
    # Định dạng kết quả
    result = [
        {
            'period': item['period'].strftime('%Y-%m-%d'),
            'cv_count': item['cv_count']
        }
        for item in cvs_by_period
    ]
    
    data = {
        'message': f'Thống kê CV theo thời gian ({period})',
        'status': status.HTTP_200_OK,
        'data': result
    }
    
    # Lưu vào cache trong 1 giờ
    cache.set(cache_key, data, timeout=3600)
    
    return Response(data)

# API cho thống kê hiệu suất bài đăng
@swagger_auto_schema(
    method='get',
    operation_description="Thống kê hiệu suất các bài đăng",
    responses={
        200: openapi.Response(
            description="Thành công",
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
                                'post_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING),
                                'cv_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'approved_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'conversion_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                            }
                        )
                    )
                }
            )
        ),
        403: openapi.Response(description="Không có quyền truy cập"),
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_post_performance(request):
    # Lấy doanh nghiệp của người dùng hiện tại
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Tạo cache key
    cache_key = f'post_performance_{enterprise.id}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Lấy bài đăng của doanh nghiệp
    posts = PostEntity.objects.filter(enterprise=enterprise)
    
    result = []
    for post in posts:
        # Đếm số CV cho mỗi bài đăng
        cv_count = Cv.objects.filter(post=post).count()
        approved_count = Cv.objects.filter(post=post, status='approved').count()
        
        # Tính tỷ lệ chuyển đổi (số CV được duyệt / tổng số CV)
        conversion_rate = 0
        if cv_count > 0:
            conversion_rate = round(approved_count / cv_count * 100, 2)
        
        result.append({
            'post_id': post.id,
            'title': post.title,
            'created_at': post.created_at.strftime('%Y-%m-%d'),
            'cv_count': cv_count,
            'approved_count': approved_count,
            'conversion_rate': conversion_rate,
        })
    
    # Sắp xếp theo số lượng CV giảm dần
    result = sorted(result, key=lambda x: x['cv_count'], reverse=True)
    
    data = {
        'message': 'Thống kê hiệu suất các bài đăng',
        'status': status.HTTP_200_OK,
        'data': result
    }
    
    # Lưu vào cache trong 1 giờ
    cache.set(cache_key, data, timeout=3600)
    
    return Response(data)

# API cho thống kê các tỷ lệ chuyển đổi
@swagger_auto_schema(
    method='get',
    operation_description="Thống kê tỷ lệ phê duyệt CV",
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
                            'total_cvs': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'approval_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'rejection_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'processing_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'status_counts': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'approved': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'rejected': openapi.Schema(type=openapi.TYPE_INTEGER),
                                }
                            ),
                        }
                    )
                }
            )
        ),
        403: openapi.Response(description="Không có quyền truy cập"),
    },
    security=[{'Bearer': []}]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def get_cv_approval_stats(request):
    # Lấy doanh nghiệp của người dùng hiện tại
    enterprise = request.user.get_enterprise()
    if not enterprise:
        return Response({
            'message': 'Bạn không phải là nhà tuyển dụng',
            'status': status.HTTP_403_FORBIDDEN
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Tạo cache key
    cache_key = f'cv_approval_stats_{enterprise.id}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)
    
    # Lấy ID các bài đăng của doanh nghiệp
    post_ids = PostEntity.objects.filter(enterprise=enterprise).values_list('id', flat=True)
    
    # Thống kê CV theo trạng thái
    total_cvs = Cv.objects.filter(post__in=post_ids).count()
    
    status_counts = {
        'pending': Cv.objects.filter(post__in=post_ids, status='pending').count(),
        'approved': Cv.objects.filter(post__in=post_ids, status='approved').count(),
        'rejected': Cv.objects.filter(post__in=post_ids, status='rejected').count(),
    }
    
    # Tính tỷ lệ
    approval_rate = 0
    rejection_rate = 0
    processing_rate = 0
    
    if total_cvs > 0:
        approval_rate = round(status_counts['approved'] / total_cvs * 100, 2)
        rejection_rate = round(status_counts['rejected'] / total_cvs * 100, 2)
        processing_rate = round(status_counts['pending'] / total_cvs * 100, 2)
    
    data = {
        'message': 'Thống kê tỷ lệ phê duyệt CV',
        'status': status.HTTP_200_OK,
        'data': {
            'total_cvs': total_cvs,
            'approval_rate': approval_rate,
            'rejection_rate': rejection_rate,
            'processing_rate': processing_rate,
            'status_counts': status_counts,
        }
    }
    
    # Lưu vào cache trong 30 phút
    cache.set(cache_key, data, timeout=1800)
    
    return Response(data)
