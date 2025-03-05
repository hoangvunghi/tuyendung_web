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
    IsFieldManager, IsPositionManager, IsCriteriaOwner
)
from notifications.services import NotificationService
from base.pagination import CustomPagination

# Create your views here.

# Enterprise CRUD
@api_view(['GET'])
@permission_classes([AllowAny])
def get_enterprises(request):
    enterprises = EnterpriseEntity.objects.filter(is_active=True)
    
    # Khởi tạo paginator
    paginator = CustomPagination()
    paginated_enterprises = paginator.paginate_queryset(enterprises, request)
    
    serializer = EnterpriseSerializer(paginated_enterprises, many=True)
    return paginator.get_paginated_response(serializer.data)

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
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

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def update_enterprise(request, pk):
    enterprise = get_object_or_404(EnterpriseEntity, pk=pk, user=request.user)
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

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_enterprise(request, pk):
    enterprise = get_object_or_404(EnterpriseEntity, pk=pk, user=request.user)
    enterprise.is_active = False
    enterprise.save()
    return Response({
        'message': 'Enterprise deleted successfully',
        'status': status.HTTP_200_OK
    })

# Campaign CRUD
@api_view(['GET'])
@permission_classes([AllowAny])
def get_campaigns(request):
    enterprise_id = request.query_params.get('enterprise_id')
    if enterprise_id:
        campaigns = CampaignEntity.objects.filter(enterprise_id=enterprise_id, is_active=True)
    else:
        campaigns = CampaignEntity.objects.filter(is_active=True)
    
    # Sắp xếp
    sort_by = request.query_params.get('sort_by', '-created_at')
    sort_order = request.query_params.get('sort_order', 'desc')
    
    if sort_order == 'desc' and not sort_by.startswith('-'):
        sort_by = f'-{sort_by}'
    campaigns = campaigns.order_by(sort_by)
    
    # Phân trang
    paginator = CustomPagination()
    paginated_campaigns = paginator.paginate_queryset(campaigns, request)
    
    serializer = CampaignSerializer(paginated_campaigns, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_campaign(request):
    serializer = CampaignSerializer(data=request.data)
    if serializer.is_valid():
        enterprise = get_object_or_404(EnterpriseEntity, 
                                     id=request.data.get('enterprise'),
                                     user=request.user)
        serializer.save()
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
@api_view(['GET'])
@permission_classes([AllowAny])
def get_posts(request):
    campaign_id = request.query_params.get('campaign_id')
    if campaign_id:
        posts = PostEntity.objects.filter(campaign_id=campaign_id)
    else:
        posts = PostEntity.objects.all()
    
    paginator = CustomPagination()
    paginated_posts = paginator.paginate_queryset(posts, request)
    
    serializer = PostSerializer(paginated_posts, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCampaignOwner])
def create_post(request):
    serializer = PostSerializer(data=request.data)
    if serializer.is_valid():
        campaign = get_object_or_404(CampaignEntity, 
                                   id=request.data.get('campaign'),
                                   enterprise__user=request.user)
        serializer.save()
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

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsFieldManager])
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
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
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

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def view_cv(request, cv_id):
    cv = get_object_or_404(Cv, id=cv_id)
    
    # Tạo notification khi CV được xem
    NotificationService.notify_cv_viewed(cv)
    
    serializer = CvSerializer(cv)
    return Response({
        'message': 'CV retrieved successfully',
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
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
@api_view(['GET'])
@permission_classes([AllowAny])
def get_campaign_detail(request, pk):
    """Chi tiết chiến dịch"""
    campaign = get_object_or_404(CampaignEntity, pk=pk)
    serializer = CampaignSerializer(campaign)
    return Response({
        'message': 'Campaign details retrieved successfully',
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def get_post_detail(request, pk):
    """Chi tiết bài đăng"""
    post = get_object_or_404(PostEntity, pk=pk)
    serializer = PostSerializer(post)
    return Response({
        'message': 'Post details retrieved successfully',
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_campaign_detail(request, pk):
    campaign = get_object_or_404(CampaignEntity, pk=pk)
    serializer = CampaignSerializer(campaign)
    return Response({
        'message': 'Campaign details retrieved successfully',
        'status': status.HTTP_200_OK,
        'data': serializer.data
    })

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
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

@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner])
def delete_campaign(request, pk):
    campaign = get_object_or_404(CampaignEntity, pk=pk, enterprise__user=request.user)
    campaign.is_active = False
    campaign.save()
    return Response({
        'message': 'Campaign deleted successfully',
        'status': status.HTTP_200_OK
    })

# update_post
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsPostOwner])
def update_post(request, pk):
    post = get_object_or_404(PostEntity, pk=pk, campaign__enterprise__user=request.user)
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
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsPostOwner])
def delete_post(request, pk):
    post = get_object_or_404(PostEntity, pk=pk, campaign__enterprise__user=request.user)
    post.is_active = False
    post.save()
    return Response({
        'message': 'Post deleted successfully',
        'status': status.HTTP_200_OK
    })
