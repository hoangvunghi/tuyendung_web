from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response

@api_view(['GET'])
# @permission_classes([IsAdminUser])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """API để lấy dữ liệu thống kê cho dashboard admin"""
    from django.apps import apps
    
    # Lấy các model cần thiết
    UserAccount = apps.get_model("accounts", "UserAccount")
    UserInfo = apps.get_model("profiles", "UserInfo")
    EnterpriseEntity = apps.get_model("enterprises", "EnterpriseEntity")
    PostEntity = apps.get_model("enterprises", "PostEntity")
    Cv = apps.get_model("profiles", "Cv")
    Interview = apps.get_model("interviews", "Interview")
    VnPayTransaction = apps.get_model("transactions", "VnPayTransaction")
    
    # Đếm số lượng
    user_count = UserAccount.objects.count()
    user_info_count = UserInfo.objects.count()
    enterprise_count = EnterpriseEntity.objects.count()
    post_count = PostEntity.objects.count()
    cv_count = Cv.objects.count()
    interview_count = Interview.objects.count()
    
    # Tính các thống kê tài chính
    total_revenue = VnPayTransaction.objects.filter(transaction_status='00').aggregate(Sum('amount'))['amount__sum'] or 0
    premium_users = UserAccount.objects.filter(is_premium=True).count()
    
    # Số liệu theo ngày gần đây
    today = timezone.now().date()
    
    # Dữ liệu cho biểu đồ theo ngày trong 7 ngày qua
    days = 7
    date_data = []
    user_data = []
    cv_data = []
    post_data = []
    
    for i in range(days):
        # Tính toán ngày
        day = today - timedelta(days=(days-1-i))
        date_data.append(day.strftime('%d/%m'))
        
        # Đếm người dùng đăng ký trong ngày
        day_users = UserAccount.objects.filter(
            created_at__date=day
        ).count()
        user_data.append(day_users)
        
        # Đếm CV trong ngày
        day_cvs = Cv.objects.filter(
            created_at__date=day
        ).count()
        cv_data.append(day_cvs)
        
        # Đếm bài đăng trong ngày
        day_posts = PostEntity.objects.filter(
            created_at__date=day
        ).count()
        post_data.append(day_posts)
    
    # Thống kê CV theo trạng thái
    cv_pending = Cv.objects.filter(status='pending').count()
    cv_approved = Cv.objects.filter(status='approved').count()
    cv_rejected = Cv.objects.filter(status='rejected').count()
    
    # Thống kê bài đăng theo trạng thái
    post_active = PostEntity.objects.filter(is_active=True).count()
    post_inactive = PostEntity.objects.filter(is_active=False).count()
    
    # Thống kê các doanh nghiệp theo thành phố
    city_stats = EnterpriseEntity.objects.values('city').annotate(count=Count('id')).order_by('-count')[:5]
    
    return Response({
        "stats": [
            {
                "label": "Tổng số tài khoản",
                "value": user_count,
                "color": "primary",
                "icon": "person"
            },
            {
                "label": "Tổng số hồ sơ",
                "value": user_info_count,
                "color": "info", 
                "icon": "folder"
            },
            {
                "label": "Doanh nghiệp", 
                "value": enterprise_count,
                "color": "success",
                "icon": "business"
            },
            {
                "label": "Bài đăng",
                "value": post_count, 
                "color": "warning",
                "icon": "article"
            },
            {
                "label": "CV đã nhận",
                "value": cv_count,
                "color": "indigo",
                "icon": "description"
            },
            {
                "label": "Phỏng vấn",
                "value": interview_count,
                "color": "orange",
                "icon": "event"
            },
            {
                "label": "Doanh thu",
                "value": f"{total_revenue:,} VNĐ",
                "color": "error",
                "icon": "monetization_on"
            },
            {
                "label": "Người dùng Premium",
                "value": premium_users,
                "color": "purple",
                "icon": "star"
            }
        ],
        "charts": {
            "user_activity": {
                "labels": date_data,
                "datasets": [
                    {
                        "label": "Người dùng mới",
                        "data": user_data,
                        "color": "primary"
                    }
                ],
                "type": "bar",
                "title": "Hoạt động đăng ký trong 7 ngày qua"
            },
            "activity_chart": {
                "labels": date_data,
                "datasets": [
                    {
                        "label": "CV nộp vào",
                        "data": cv_data,
                        "color": "info"
                    },
                    {
                        "label": "Bài đăng mới",
                        "data": post_data,
                        "color": "orange"
                    }
                ],
                "type": "bar",
                "title": "Hoạt động CV & Bài đăng"
            },
            "cv_status": {
                "labels": ["Chờ duyệt", "Đã duyệt", "Từ chối"],
                "datasets": [
                    {
                        "data": [cv_pending, cv_approved, cv_rejected],
                        "backgroundColor": [
                            "rgba(251, 191, 36, 0.8)",
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(239, 68, 68, 0.8)"
                        ]
                    }
                ],
                "type": "pie",
                "title": "Trạng thái CV"
            },
            "post_status": {
                "labels": ["Đang hoạt động", "Không hoạt động"],
                "datasets": [
                    {
                        "data": [post_active, post_inactive],
                        "backgroundColor": [
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(148, 163, 184, 0.8)"
                        ]
                    }
                ],
                "type": "pie",
                "title": "Trạng thái Bài đăng"
            },
            "city_stats": {
                "labels": [item['city'] for item in city_stats],
                "datasets": [
                    {
                        "label": "Doanh nghiệp",
                        "data": [item['count'] for item in city_stats],
                        "color": "success"
                    }
                ],
                "type": "bar",
                "title": "Doanh nghiệp theo thành phố"
            }
        }
    }) 