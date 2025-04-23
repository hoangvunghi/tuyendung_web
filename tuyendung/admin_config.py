from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


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

    context.update({
        "stats": [
            {
                "label": "Tổng số tài khoản",
                "value": user_count,
                "url": reverse_lazy("admin:accounts_useraccount_changelist"),
                "color": "primary",
                "icon": "person",
            },
            {
                "label": "Tổng số hồ sơ",
                "value": user_info_count,
                "url": reverse_lazy("admin:profiles_userinfo_changelist"),
                "color": "info",
                "icon": "folder",
            },
            {
                "label": "Doanh nghiệp",
                "value": enterprise_count,
                "url": reverse_lazy("admin:enterprises_enterpriseentity_changelist"),
                "color": "success",
                "icon": "business",
            },
            {
                "label": "Bài đăng",
                "value": post_count,
                "url": reverse_lazy("admin:enterprises_postentity_changelist"),
                "color": "warning", 
                "icon": "article",
            },
            {
                "label": "CV đã nhận",
                "value": cv_count,
                "url": reverse_lazy("admin:profiles_cv_changelist"),
                "color": "indigo",
                "icon": "description",
            }, 
            {
                "label": "Phỏng vấn",
                "value": interview_count,
                "url": reverse_lazy("admin:interviews_interview_changelist"),
                "color": "orange",
                "icon": "event",
            },
            {
                "label": "Doanh thu",
                "value": f"{total_revenue:,} VNĐ",
                "url": reverse_lazy("admin:transactions_vnpaytransaction_changelist"),
                "color": "error",
                "icon": "monetization_on",
            },
            {
                "label": "Người dùng Premium",
                "value": premium_users,
                "url": reverse_lazy("admin:accounts_useraccount_changelist") + "?is_premium__exact=1", 
                "color": "purple",
                "icon": "star",
            },
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
                            "borderColor": "rgb(168, 85, 247)",
                            "backgroundColor": "rgba(168, 85, 247, 0.1)",
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
                            "borderColor": "rgb(59, 130, 246)",
                            "backgroundColor": "rgba(59, 130, 246, 0.1)",
                            "tension": 0.3,
                        },
                        {
                            "label": "Bài đăng mới",
                            "data": post_data,
                            "borderColor": "rgb(234, 88, 12)",
                            "backgroundColor": "rgba(234, 88, 12, 0.1)",
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
            }
        ]
    })
    return context

# Cấu hình cơ bản cho Unfold
UNFOLD = {
    "SITE_TITLE": "Hệ Thống Quản Lý Tuyển Dụng",
    "SITE_HEADER": "Bảng Điều Khiển Tuyển Dụng",
    "SITE_SUBHEADER": "Hệ thống quản lý tuyển dụng chuyên nghiệp",
    "SITE_URL": "/",
    "SITE_SYMBOL": "work", 
    "DASHBOARD_CALLBACK": get_dashboard_config,
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("My site"),
            "link": "http://localhost:5173",
        },
    ],
    
    "SITE_LOGO": {
        "light": lambda request: static("logo.svg"),  # light mode
        "dark": lambda request: static("logo.svg"),  # dark mode
    },

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
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    
    # Tùy chỉnh CSS và JS
    "STYLES": [
        "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600&display=swap",
        lambda request: static("css/custom.css"),
    ],
    
    # Cấu hình sidebar
    "SIDEBAR": {
        "show_search": False,  # Search in applications and models names
        "show_all_applications": False,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _("Bảng điều khiển"),
                "separator": True,  # Top border
                "collapsible": False,  # Không thu gọn được
                "items": [
                    {
                        "title": _("Bảng điều khiển"),
                        "icon": "dashboard",  # Supported icon set: https://fonts.google.com/icons
                        "link": reverse_lazy("admin:index"),
                        # "badge": "sample_app.badge_callback",
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
            {
                "title": _("Tài khoản"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Tài khoản"),
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_useraccount_changelist"),
                    },
                    {
                        "title": _("Vai trò"),
                        "icon": "admin_panel_settings",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                    },
                    {
                        "title": _("Vai trò người dùng"),
                        "icon": "supervisor_account",
                        "link": reverse_lazy("admin:accounts_userrole_changelist"),
                    },
                ],
            },
            {
                "title": _("Doanh nghiệp"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Doanh nghiệp"),
                        "icon": "business",
                        "link": reverse_lazy("admin:enterprises_enterpriseentity_changelist"),
                    },
                    {
                        "title": _("Lĩnh vực"),
                        "icon": "category",
                        "link": reverse_lazy("admin:enterprises_fieldentity_changelist"),
                    },
                    {
                        "title": _("Vị trí"),
                        "icon": "category",
                        "link": reverse_lazy("admin:enterprises_positionentity_changelist"),
                    },
                    {
                        "title": _("Bài viết"),
                        "icon": "article",
                        "link": reverse_lazy("admin:enterprises_postentity_changelist"),
                    },
                    {
                        "title": _("Tiêu chí"),
                        "icon": "checklist",
                        "link": reverse_lazy("admin:enterprises_criteriaentity_changelist"),
                    },
                ]
            },
            {
                "title": _("Chat"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Tin nhắn"),
                        "icon": "chat",
                        "link": reverse_lazy("admin:chat_message_changelist"),
                    },
                ]
            },
            {
                "title": _("Phỏng vấn"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Phỏng vấn"),
                        "icon": "event_note",
                        "link": reverse_lazy("admin:interviews_interview_changelist"),
                    },
                ]
            },
            # Notification
            {
                "title": _("Thông báo"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Thông báo"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                ]
            },
            # Profile
            {
                "title": _("Hồ sơ"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Hồ sơ"),
                        "icon": "account_box",
                        "link": reverse_lazy("admin:profiles_userinfo_changelist"),
                    },
                    {
                        "title": _("CV"),
                        "icon": "description",
                        "link": reverse_lazy("admin:profiles_cv_changelist"),
                    },
                    # {
                    #     "title": _("CV đã xem"),
                    #     "icon": "visibility",
                    #     "link": reverse_lazy("admin:profiles_cvview_changelist"),
                    # },
                    # {
                    #     "title": _("CV đã đánh dấu"),
                    #     "icon": "bookmark",
                    #     "link": reverse_lazy("admin:profiles_cvmark_changelist"),
                    # },
                ],
            },
            # services
            # {
            #     "title": _("Dịch vụ"),
            #     "separator": True,  # Top border
            #     "collapsible": True,  # Collapsible group of links
            #     "items": [
            #         {
            #             "title": _("Loại dịch vụ"),
            #             "icon": "design_services",
            #             "link": reverse_lazy("admin:services_typeservice_changelist"),
            #         },
            #         {
            #             "title": _("Gói dịch vụ"),
            #             "icon": "widgets",
            #             "link": reverse_lazy("admin:services_packageentity_changelist"),
            #         },
            #         {
            #             "title": _("Gói đăng ký"),
            #             "icon": "subscriptions",
            #             "link": reverse_lazy("admin:services_packagecampaign_changelist"),
            #         },
            #     ],
            # },
            # # transactions
            {
                "title": _("Giao dịch"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    # {
                    #     "title": _("Lịch sử giao dịch"),
                    #     "icon": "payments",
                    #     "link": reverse_lazy("admin:transactions_historymoney_changelist"),
                    # },
                    {
                        "title": _("Giao dịch VNPay"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:transactions_vnpaytransaction_changelist"),
                    },
                    # PremiumHistory
                    {
                        "title": _("Lịch sử Premium"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:transactions_premiumhistory_changelist"),
                    },
                    # premiumpackage
                    {
                        "title": _("Gói dịch vụ"),
                        "icon": "subscriptions",
                        "link": reverse_lazy("admin:transactions_premiumpackage_changelist"),
                    },
                ],
            },
            # google
            {
                "title": _("Google"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Cấu hình OAuth2"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:social_django_usersocialauth_changelist"),
                    },
                    {
                        "title": _("Đăng nhập Google"),
                        "icon": "google",
                        "link": reverse_lazy("admin:social_django_nonce_changelist"),
                    },
                    {
                        "title": _("Liên kết xã hội"),
                        "icon": "link",
                        "link": reverse_lazy("admin:social_django_association_changelist"),
                    },
                ],
            },

            
        ],
    },
}
