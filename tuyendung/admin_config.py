from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import os
from django.contrib.staticfiles.storage import staticfiles_storage
import json

# Thay thế việc sử dụng reverse_lazy trực tiếp bằng một hàm trì hoãn
def get_admin_url(viewname, *args, **kwargs):
    """Trả về một hàm lambda để trì hoãn việc tạo URL cho đến khi cần thiết"""
    return lambda request=None: reverse_lazy(viewname, *args, **kwargs)

def get_dashboard_config(request, context):
    """Hàm trả về cấu hình dashboard."""
    from django.apps import apps
    from django.db.models import Count, Sum
    from django.utils import timezone
    from datetime import timedelta, datetime
    
    try:
        # Lấy số lượng từ các model
        UserAccount = apps.get_model("accounts", "UserAccount")
        UserInfo = apps.get_model("profiles", "UserInfo") 
        EnterpriseEntity = apps.get_model("enterprises", "EnterpriseEntity")
        PostEntity = apps.get_model("enterprises", "PostEntity")
        Cv = apps.get_model("profiles", "Cv")
        Interview = apps.get_model("interviews", "Interview")
        VnPayTransaction = apps.get_model("transactions", "VnPayTransaction")
        PremiumPackage = apps.get_model("transactions", "PremiumPackage")
        
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
        
        # Dữ liệu cho biểu đồ theo ngày
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
                date_joined__date=day
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
        
        # Thống kê người dùng theo loại
        candidate_count = UserAccount.objects.filter(user_roles__role__name='candidate').count()
        employer_count = UserAccount.objects.filter(user_roles__role__name='employer').count()
        
        # Thống kê việc làm theo lĩnh vực
        job_fields = PostEntity.objects.values('field__name').annotate(count=Count('id')).order_by('-count')[:5]
        job_field_labels = [field['field__name'] or 'Không xác định' for field in job_fields]
        job_field_data = [field['count'] for field in job_fields]
        
    except Exception as e:
        # Nếu có lỗi, thiết lập giá trị mặc định
        user_count = user_info_count = enterprise_count = post_count = cv_count = interview_count = 0
        total_revenue = premium_users = 0
        date_data = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        user_data = [10, 15, 8, 12, 9, 5, 3]
        cv_data = [5, 8, 4, 7, 6, 3, 1]
        post_data = [2, 3, 1, 4, 2, 1, 0]
        cv_pending = cv_approved = cv_rejected = 0
        post_active = post_inactive = 0
        candidate_count = employer_count = 0
        job_field_labels = ["IT", "Marketing", "Kế toán", "Bán hàng", "Khác"]
        job_field_data = [10, 8, 5, 7, 3]

    context.update({
        "stats": [
            {
                "label": "Tổng số tài khoản",
                "value": user_count,
                "url": get_admin_url("admin:accounts_useraccount_changelist"),
                "color": "primary",
                "icon": "person",
            },
            {
                "label": "Tổng số hồ sơ",
                "value": user_info_count,
                "url": get_admin_url("admin:profiles_userinfo_changelist"),
                "color": "info",
                "icon": "folder",
            },
            {
                "label": "Doanh nghiệp",
                "value": enterprise_count,
                "url": get_admin_url("admin:enterprises_enterpriseentity_changelist"),
                "color": "success",
                "icon": "business",
            },
            {
                "label": "Bài đăng",
                "value": post_count,
                "url": get_admin_url("admin:enterprises_postentity_changelist"),
                "color": "warning", 
                "icon": "article",
            },
            {
                "label": "CV đã nhận",
                "value": cv_count,
                "url": get_admin_url("admin:profiles_cv_changelist"),
                "color": "indigo",
                "icon": "description",
            }, 
            {
                "label": "Phỏng vấn",
                "value": interview_count,
                "url": get_admin_url("admin:interviews_interview_changelist"),
                "color": "orange",
                "icon": "event",
            },
            {
                "label": "Doanh thu",
                "value": f"{total_revenue:,} VNĐ",
                "url": get_admin_url("admin:transactions_vnpaytransaction_changelist"),
                "color": "error",
                "icon": "monetization_on",
            },
            {
                "label": "Người dùng Premium",
                "value": premium_users,
                "url": lambda request=None: reverse_lazy("admin:accounts_useraccount_changelist") + "?is_premium__exact=1", 
                "color": "purple",
                "icon": "star",
            },
        ],
        "widgets": [
            {
                "title": "Công việc hot đang tuyển",
                "content_template": "admin/widgets/hot_jobs.html",
                "classes": "col-span-full xl:col-span-6 bg-white shadow rounded-lg p-4",
            },
            {
                "title": "Doanh nghiệp gần đây",
                "content_template": "admin/widgets/recent_enterprises.html",
                "classes": "col-span-full xl:col-span-6 bg-white shadow rounded-lg p-4",
            },
            {
                "title": "Người dùng Premium",
                "content_template": "admin/widgets/premium_users.html",
                "classes": "col-span-full xl:col-span-6 bg-white shadow rounded-lg p-4",
            }
        ],
        "charts": [
            {
                "id": "users-chart",
                "type": "line",
                "data": {
                    "labels": date_data,
                    "datasets": [
                        {
                            "label": "Người dùng mới",
                            "data": user_data,
                            "borderColor": "rgb(59, 130, 246)",
                            "backgroundColor": "rgba(59, 130, 246, 0.1)",
                            "tension": 0.3,
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Hoạt động đăng ký trong 7 ngày qua"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            },
            {
                "id": "activity-chart", 
                "type": "line",
                "data": {
                    "labels": date_data,
                    "datasets": [
                        {
                            "label": "CV nộp vào",
                            "data": cv_data,
                            "borderColor": "rgb(16, 185, 129)",
                            "backgroundColor": "rgba(16, 185, 129, 0.1)",
                            "tension": 0.3,
                        },
                        {
                            "label": "Bài đăng mới",
                            "data": post_data,
                            "borderColor": "rgb(245, 158, 11)",
                            "backgroundColor": "rgba(245, 158, 11, 0.1)",
                            "tension": 0.3,
                        }
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Hoạt động CV & Bài đăng trong 7 ngày qua"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            },
            {
                "id": "cv-status-chart",
                "type": "doughnut",
                "data": {
                    "labels": ["Chờ duyệt", "Đã duyệt", "Từ chối"],
                    "datasets": [
                        {
                            "data": [cv_pending, cv_approved, cv_rejected],
                            "backgroundColor": [
                                "rgba(251, 191, 36, 0.7)",
                                "rgba(34, 197, 94, 0.7)",
                                "rgba(239, 68, 68, 0.7)"
                            ],
                            "borderColor": [
                                "rgb(251, 191, 36)",
                                "rgb(34, 197, 94)",
                                "rgb(239, 68, 68)"
                            ],
                            "borderWidth": 1
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Trạng thái CV"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            },
            {
                "id": "post-status-chart",
                "type": "pie",
                "data": {
                    "labels": ["Đang hoạt động", "Không hoạt động"],
                    "datasets": [
                        {
                            "data": [post_active, post_inactive],
                            "backgroundColor": [
                                "rgba(34, 197, 94, 0.7)",
                                "rgba(148, 163, 184, 0.7)"
                            ],
                            "borderColor": [
                                "rgb(34, 197, 94)",
                                "rgb(148, 163, 184)"
                            ],
                            "borderWidth": 1
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Trạng thái Bài đăng"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            },
            {
                "id": "user-type-chart",
                "type": "pie",
                "data": {
                    "labels": ["Ứng viên", "Nhà tuyển dụng"],
                    "datasets": [
                        {
                            "data": [candidate_count, employer_count],
                            "backgroundColor": [
                                "rgba(59, 130, 246, 0.7)",
                                "rgba(139, 92, 246, 0.7)"
                            ],
                            "borderColor": [
                                "rgb(59, 130, 246)",
                                "rgb(139, 92, 246)"
                            ],
                            "borderWidth": 1
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Phân loại người dùng"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            },
            {
                "id": "job-fields-chart",
                "type": "bar",
                "data": {
                    "labels": job_field_labels,
                    "datasets": [
                        {
                            "label": "Số lượng việc làm",
                            "data": job_field_data,
                            "backgroundColor": "rgba(14, 165, 233, 0.7)",
                            "borderColor": "rgb(14, 165, 233)",
                            "borderWidth": 1
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Việc làm theo lĩnh vực"
                        },
                        "legend": {
                            "position": "bottom"
                        }
                    }
                }
            }
        ]
    })
    return context

# Cấu hình cơ bản cho Unfold
UNFOLD = {
    "SITE_TITLE": "Tuyển Dụng Admin",
    "SITE_HEADER": "Tuyển Dụng Admin",
    "SITE_SUBHEADER": "Quản lý hệ thống tuyển dụng",
    "SITE_ICON": None,  # Favicon, tương đối với STATIC_URL hoặc URL đầy đủ
    "SITE_LOGO": None,  # Logo, tương đối với STATIC_URL hoặc URL đầy đủ
    "SITE_SYMBOL": "diversity_3",  # Biểu tượng cho sidebar, từ Google Material Symbols
    "DASHBOARD_CALLBACK": get_dashboard_config,
    "SITE_DROPDOWN": [
        {
            "icon": "public",
            "title": _("Trang chủ"),
            "link": "http://localhost:5173",
        },
        {
            "icon": "analytics", 
            "title": _("Thống kê"),
            "link": get_admin_url("admin:index"),
        },
        {
            "icon": "settings",
            "title": _("Cài đặt"),
            "link": get_admin_url("admin:index"),
        },
    ],
    
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("logo.svg"),
        },
    ],
    # Cấu hình chung
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": "development",
    
    # Giao diện
    "BORDER_RADIUS": "10px",
    "COLOR_SCHEME": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "COLORS": {
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    
    # Tùy chỉnh CSS và JS
    "STYLES": [
        "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap",
        lambda request: static("css/custom.css"),
    ],
    
    # Cấu hình sidebar
    "SIDEBAR": {
        "show_search": True,  # Search in applications and models names
        "show_all_applications": True,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _("Bảng điều khiển"),
                "separator": True,  # Top border
                "collapsible": False,  # Không thu gọn được
                "items": [
                    {
                        "title": _("Tổng quan"),
                        "icon": "dashboard",  # Supported icon set: https://fonts.google.com/icons
                        "link": get_admin_url("admin:index"),
                        # "badge": "sample_app.badge_callback",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Quản lý tài khoản"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Tài khoản người dùng"),
                        "icon": "person",
                        "link": get_admin_url("admin:accounts_useraccount_changelist"),
                    },
                    {
                        "title": _("Tài khoản premium"),
                        "icon": "workspace_premium",
                        "link": lambda request=None: reverse_lazy("admin:accounts_useraccount_changelist") + "?is_premium__exact=1",
                    },
                    {
                        "title": _("Vai trò"),
                        "icon": "admin_panel_settings",
                        "link": get_admin_url("admin:accounts_role_changelist"),
                    },
                    {
                        "title": _("Vai trò người dùng"),
                        "icon": "supervisor_account",
                        "link": get_admin_url("admin:accounts_userrole_changelist"),
                    },
                ],
            },
            {
                "title": _("Quản lý doanh nghiệp"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Doanh nghiệp"),
                        "icon": "business",
                        "link": get_admin_url("admin:enterprises_enterpriseentity_changelist"),
                    },
                    {
                        "title": _("Lĩnh vực"),
                        "icon": "category",
                        "link": get_admin_url("admin:enterprises_fieldentity_changelist"),
                    },
                    {
                        "title": _("Vị trí tuyển dụng"),
                        "icon": "work_outline",
                        "link": get_admin_url("admin:enterprises_positionentity_changelist"),
                    },
                    {
                        "title": _("Tin tuyển dụng"),
                        "icon": "article",
                        "link": get_admin_url("admin:enterprises_postentity_changelist"),
                    },
                    {
                        "title": _("Tiêu chí"),
                        "icon": "checklist",
                        "link": get_admin_url("admin:enterprises_criteriaentity_changelist"),
                    },
                ]
            },
            {
                "title": _("Quản lý tương tác"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Tin nhắn"),
                        "icon": "chat",
                        "link": get_admin_url("admin:chat_message_changelist"),
                    },
                    {
                        "title": _("Phỏng vấn"),
                        "icon": "event_note",
                        "link": get_admin_url("admin:interviews_interview_changelist"),
                    },
                    {
                        "title": _("Thông báo"),
                        "icon": "notifications",
                        "link": get_admin_url("admin:notifications_notification_changelist"),
                    },
                ]
            },
            {
                "title": _("Quản lý hồ sơ"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Hồ sơ ứng viên"),
                        "icon": "account_box",
                        "link": get_admin_url("admin:profiles_userinfo_changelist"),
                    },
                    {
                        "title": _("CV ứng tuyển"),
                        "icon": "description",
                        "link": get_admin_url("admin:profiles_cv_changelist"),
                    },
                ],
            },
            {
                "title": _("Quản lý thanh toán"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Giao dịch VNPay"),
                        "icon": "payments",
                        "link": get_admin_url("admin:transactions_vnpaytransaction_changelist"),
                    },
                    {
                        "title": _("Lịch sử Premium"),
                        "icon": "history",
                        "link": get_admin_url("admin:transactions_premiumhistory_changelist"),
                    },
                    {
                        "title": _("Gói Premium"),
                        "icon": "subscriptions",
                        "link": get_admin_url("admin:transactions_premiumpackage_changelist"),
                    },
                ],
            },
            {
                "title": _("Tích hợp"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Google OAuth2"),
                        "icon": "google",
                        "link": get_admin_url("admin:social_django_usersocialauth_changelist"),
                    },
                    {
                        "title": _("Các liên kết xã hội khác"),
                        "icon": "link",
                        "link": get_admin_url("admin:social_django_association_changelist"),
                    },
                ],
            },
        ],
    },
}

