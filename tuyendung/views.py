from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from django.db.models.functions import Extract
import json
from django.conf import settings
from django.db.models import ExpressionWrapper, DurationField
from django.db.models import F

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
    PremiumPackage = apps.get_model("transactions", "PremiumPackage")
    FieldEntity = apps.get_model("enterprises", "FieldEntity")
    
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
        day = today - timedelta(days=(days-1-i))
        date_data.append(day.strftime('%d/%m'))
        
        day_users = UserAccount.objects.filter(created_at__date=day).count()
        user_data.append(day_users)
        
        day_cvs = Cv.objects.filter(created_at__date=day).count()
        cv_data.append(day_cvs)
        
        day_posts = PostEntity.objects.filter(created_at__date=day).count()
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

    # Thống kê người dùng theo vai trò
    candidate_count = UserAccount.objects.filter(user_roles__role__name='candidate').count()
    employer_count = UserAccount.objects.filter(user_roles__role__name='employer').count()
    active_candidates = UserAccount.objects.filter(user_roles__role__name='candidate', last_login__gte=today-timedelta(days=30)).count()
    active_employers = UserAccount.objects.filter(user_roles__role__name='employer', last_login__gte=today-timedelta(days=30)).count()

    # Thống kê đăng nhập
    daily_login = UserAccount.objects.filter(last_login__date=today).count()
    weekly_login = UserAccount.objects.filter(last_login__gte=today-timedelta(days=7)).count()
    monthly_login = UserAccount.objects.filter(last_login__gte=today-timedelta(days=30)).count()

    # Thống kê nguồn đăng ký
    email_reg = UserAccount.objects.filter(google_id__isnull=True).count()
    google_reg = UserAccount.objects.filter(google_id__isnull=False).count()
    facebook_reg = 0  # Không có dữ liệu Facebook trong model hiện tại

    # Thống kê Premium
    premium_conversion = UserAccount.objects.filter(is_premium=True).count()
    premium_retention = UserAccount.objects.filter(is_premium=True, last_login__gte=today-timedelta(days=30)).count()

    # Thống kê doanh nghiệp
    enterprise_activity = {
        'posts': PostEntity.objects.count(),
        'cv_views': Cv.objects.filter(is_viewed=True).count(),
        'applications': Interview.objects.count()
    }

    # Top doanh nghiệp theo ứng viên
    top_enterprises = EnterpriseEntity.objects.annotate(
        application_count=Count('interview')
    ).order_by('-application_count')[:5]

    # Trạng thái xác thực doanh nghiệp
    verified_enterprises = EnterpriseEntity.objects.filter(business_certificate_url__isnull=False).count()
    pending_enterprises = EnterpriseEntity.objects.filter(business_certificate_url__isnull=True, is_active=True).count()
    unverified_enterprises = EnterpriseEntity.objects.filter(business_certificate_url__isnull=True, is_active=False).count()

    # Phân bố ngành
    industry_stats = EnterpriseEntity.objects.values('field_of_activity').annotate(count=Count('id')).order_by('-count')[:5]

    # Thống kê bài đăng theo lĩnh vực
    field_stats = PostEntity.objects.values('field').annotate(
        post_count=Count('id'),
        application_count=Count('cvs')
    ).order_by('-post_count')[:4]

    # Thời gian tuyển dụng
    fill_time_stats = PostEntity.objects.filter(
        is_active=False
    ).values('field').annotate(
        avg_days=Avg(
            Extract('modified_at', 'epoch') - Extract('created_at', 'epoch')
        ) / (24 * 3600)  # Chuyển từ giây sang ngày
    )[:4]

    # Phân bố địa điểm và mức lương
    location_salary = PostEntity.objects.values('city').annotate(
        avg_salary=Avg('salary_max')
    ).order_by('-avg_salary')[:4]

    # Loại hình công việc
    job_types = PostEntity.objects.values('type_working').annotate(
        count=Count('id')
    ).order_by('-count')

    # Thống kê CV
    fields = FieldEntity.objects.all()
    cv_by_field = []
    for field in fields:
        count = Cv.objects.filter(post__field=field).count()
        cv_by_field.append({'field': field.name, 'count': count})
    cv_by_field = sorted(cv_by_field, key=lambda x: x['count'], reverse=True)[:5]

    # Thời gian xử lý CV chỉ tính CV đã duyệt hoặc từ chối
    processed_cvs = Cv.objects.filter(status__in=['approved', 'rejected'])
    cv_processing = processed_cvs.annotate(
        process_time=ExpressionWrapper(F('modified_at') - F('created_at'), output_field=DurationField())
    ).aggregate(avg_days=Avg('process_time'))
    avg_processing_days = round(cv_processing['avg_days'].total_seconds() / (24*3600), 1) if cv_processing['avg_days'] else 0

    # Thống kê ứng tuyển thành công/thất bại
    application_success = {
        'accepted': Interview.objects.filter(status='accepted').count(),
        'pending': Interview.objects.filter(status='pending').count(),
        'rejected': Interview.objects.filter(status='rejected').count(),
        'completed': Interview.objects.filter(status='completed').count(),
        'cancelled': Interview.objects.filter(status='cancelled').count(),
    }

    # Kỹ năng phổ biến (nếu không có thì trả về mảng rỗng)
    top_skills = Cv.objects.values('post__required').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    top_skills_labels = [item['post__required'] for item in top_skills]
    top_skills_data = [item['count'] for item in top_skills]

    # Thống kê doanh thu theo gói Premium
    premium_packages = PremiumPackage.objects.all()
    package_map = {pkg.name: pkg.name_display or pkg.name for pkg in premium_packages}
    revenue_by_package = VnPayTransaction.objects.filter(
        transaction_status='00'
    ).values('order_info').annotate(
        total=Sum('amount')
    ).order_by('-total')

    revenue_labels = [key for key in package_map]
    revenue_data = [item['total']/1000000 for item in revenue_by_package]
    # t cần package_map
    # ARPPU theo quý
    arppu = VnPayTransaction.objects.filter(
        transaction_status='00',
        created_at__year=today.year
    ).values('created_at__quarter').annotate(
        avg_amount=Avg('amount')
    ).order_by('created_at__quarter')

    # Tỷ lệ giao dịch thành công
    transaction_stats = {
        'success': VnPayTransaction.objects.filter(transaction_status='00').count(),
        'failed': 10
    }

    # Doanh thu theo phương thức thanh toán
    revenue_by_payment = VnPayTransaction.objects.filter(
        transaction_status='00'
    ).values('transaction_no').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # Thống kê trạng thái CV
    cv_by_status = Cv.objects.values('status').annotate(count=Count('id'))

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
                "label": "Doanh thu",
                "value": f"{total_revenue:,}",
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
        "user_stats": {
            "role_activity": {
                "labels": ["Ứng viên", "Doanh nghiệp"],
                "datasets": [
                    {
                        "label": "Người dùng hoạt động",
                        "data": [active_candidates, active_employers],
                        "color": "primary"
                    },
                    {
                        "label": "Người dùng mới",
                        "data": [candidate_count, employer_count],
                        "color": "success"
                    }
                ]
            },
            "login_frequency": {
                "labels": ["Hàng ngày", "Hàng tuần", "Hàng tháng"],
                "datasets": [
                    {
                        "label": "Tần suất đăng nhập",
                        "data": [daily_login, weekly_login, monthly_login],
                        "color": "info"
                    }
                ]
            },
            "registration_source": {
                "labels": ["Email", "Google", "Facebook"],
                "datasets": [
                    {
                        "label": "Nguồn đăng ký",
                        "data": [email_reg, google_reg, facebook_reg],
                        "color": "warning"
                    }
                ]
            },
            "premium_conversion": {
                "labels": ["Chuyển đổi", "Giữ chân"],
                "datasets": [
                    {
                        "label": "Tỷ lệ Premium",
                        "data": [premium_conversion, premium_retention],
                        "color": "purple"
                    }
                ]
            }
        },
        "enterprise_stats": {
            "activity": {
                "labels": ["Bài đăng", "Xem CV", "Ứng tuyển"],
                "datasets": [
                    {
                        "label": "Hoạt động",
                        "data": [
                            enterprise_activity['posts'],
                            enterprise_activity['cv_views'],
                            enterprise_activity['applications']
                        ],
                        "color": "success"
                    }
                ]
            },
            "top_enterprises": {
                "labels": [f"DN {i+1}" for i in range(len(top_enterprises))],
                "datasets": [
                    {
                        "label": "Số lượng ứng viên",
                        "data": [e.application_count for e in top_enterprises],
                        "color": "info"
                    }
                ]
            },
            "verification": {
                "labels": ["Đã xác thực", "Đang chờ", "Chưa xác thực"],
                "datasets": [
                    {
                        "data": [verified_enterprises, pending_enterprises, unverified_enterprises],
                        "backgroundColor": [
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(251, 191, 36, 0.8)",
                            "rgba(239, 68, 68, 0.8)"
                        ]
                    }
                ]
            },
            "industry": {
                "labels": [item['field_of_activity'] for item in industry_stats],
                "datasets": [
                    {
                        "label": "Phân bố ngành",
                        "data": [item['count'] for item in industry_stats],
                        "color": "warning"
                    }
                ]
            }
        },
        "job_stats": {
            "field_stats": {
                "labels": [item['field'] for item in field_stats],
                "datasets": [
                    {
                        "label": "Số bài đăng",
                        "data": [item['post_count'] for item in field_stats],
                        "color": "primary"
                    },
                    {
                        "label": "Số ứng viên",
                        "data": [item['application_count'] for item in field_stats],
                        "color": "success"
                    }
                ]
            },
            "fill_time": {
                "labels": [item['field'] for item in fill_time_stats],
                "datasets": [
                    {
                        "label": "Thời gian (ngày)",
                        "data": [round(item['avg_days'], 1) for item in fill_time_stats],
                        "color": "info"
                    }
                ]
            },
            "location_salary": {
                "labels": [item['city'] for item in location_salary],
                "datasets": [
                    {
                        "label": "Mức lương (triệu)",
                        "data": [item['avg_salary']/1000000 for item in location_salary],
                        "color": "warning"
                    }
                ]
            },
            "job_type": {
                "labels": [item['type_working'] for item in job_types],
                "datasets": [
                    {
                        "data": [item['count'] for item in job_types],
                        "backgroundColor": [
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(59, 130, 246, 0.8)",
                            "rgba(251, 191, 36, 0.8)",
                            "rgba(139, 92, 246, 0.8)"
                        ]
                    }
                ]
            }
        },
        "cv_stats": {
            "submission": {
                "labels": [item['field'] for item in cv_by_field],
                "datasets": [
                    {
                        "label": "Số lượng CV",
                        "data": [item['count'] for item in cv_by_field],
                        "color": "primary"
                    }
                ]
            },
            "processing_time": {
                "labels": ["Trung bình (ngày)"],
                "datasets": [
                    {
                        "label": "Thời gian xử lý trung bình",
                        "data": [avg_processing_days],
                        "color": "info"
                    }
                ]
            },
            "success_rate": {
                "labels": ["Đã chấp nhận", "Đang chờ", "Từ chối", "Hoàn thành", "Đã hủy"],
                "datasets": [
                    {
                        "data": [
                            application_success['accepted'],
                            application_success['pending'],
                            application_success['rejected'],
                            application_success['completed'],
                            application_success['cancelled']
                        ],
                        "backgroundColor": [
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(251, 191, 36, 0.8)",
                            "rgba(239, 68, 68, 0.8)",
                            "rgba(59, 130, 246, 0.8)",
                            "rgba(139, 92, 246, 0.8)"
                        ]
                    }
                ]
            },
            "status_distribution": {
                "labels": [item['status'] for item in cv_by_status],
                "datasets": [
                    {
                        "label": "Số lượng theo trạng thái",
                        "data": [item['count'] for item in cv_by_status],
                        "color": "warning"
                    }
                ]
            },
            "top_skills": {
                "labels": top_skills_labels,
                "datasets": [
                    {
                        "label": "Tần suất xuất hiện",
                        "data": top_skills_data,
                        "color": "warning"
                    }
                ]
            }
        },
        "financial_stats": {
            "revenue_by_package": {
                "labels": revenue_labels,
                "datasets": [
                    {
                        "label": "Doanh thu (triệu)",
                        "data": revenue_data,
                        "color": "success"
                    }
                ]
            },
            "arppu": {
                "labels": [f"Q{q}" for q in range(1, 5)],
                "datasets": [
                    {
                        "label": "ARPPU (triệu)",
                        "data": [item['avg_amount']/1000000 for item in arppu],
                        "color": "primary"
                    }
                ]
            },
            "transaction_success": {
                "labels": ["Thành công", "Thất bại"],
                "datasets": [
                    {
                        "data": [
                            transaction_stats['success'],
                            transaction_stats['failed']
                        ],
                        "backgroundColor": [
                            "rgba(34, 197, 94, 0.8)",
                            "rgba(239, 68, 68, 0.8)"
                        ]
                    }
                ]
            },
            "revenue_by_payment": {
                "labels": [],
                "datasets": [{
                    "label": "Doanh thu (triệu)",
                    "data": [],
                    "color": "info"
                }]
            }
        }
    }) 