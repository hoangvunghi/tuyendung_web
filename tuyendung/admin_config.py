from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


def get_dashboard_config(request, context):
    """Hàm trả về cấu hình dashboard."""
    from django.apps import apps
    
    try:
        user_count = apps.get_model("accounts", "UserAccount").objects.count()
        user_info_count = apps.get_model("profiles", "UserInfo").objects.count()
    except:
        user_count = user_info_count = 0

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
        ],
        "charts": [
            {
                "id": "users-chart",
                "type": "line",
                "data": {
                    "labels": ["T2", "T3", "T4", "T5", "T6", "T7", "CN"],
                    "datasets": [
                        {
                            "label": "Người dùng mới",
                            "data": [10, 15, 8, 12, 9, 5, 3],
                            "borderColor": "rgb(168, 85, 247)",
                            "backgroundColor": "rgba(168, 85, 247, 0.1)",
                        },
                    ],
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": "Biểu Đồ Hoạt Động Trong Tuần"
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
    "SITE_TITLE": "Hệ Thống Tuyển Dụng",
    "SITE_HEADER": "Quản Lý Tuyển Dụng",
    "SITE_SUBHEADER": "Hệ thống quản lý tuyển dụng chuyên nghiệp",
    "SITE_URL": "/",
    "SITE_SYMBOL": "work", 
    "DASHBOARD_CALLBACK": get_dashboard_config,
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("My site"),
            "link": "http://127.0.0.1:8000",
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
                "title": _("Tài khoản"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",  # Supported icon set: https://fonts.google.com/icons
                        "link": reverse_lazy("admin:index"),
                        # "badge": "sample_app.badge_callback",
                        "permission": lambda request: request.user.is_superuser,
                    },
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
                    {
                        "title": _("CV đã xem"),
                        "icon": "visibility",
                        "link": reverse_lazy("admin:profiles_cvview_changelist"),
                    },
                    {
                        "title": _("CV đã đánh dấu"),
                        "icon": "bookmark",
                        "link": reverse_lazy("admin:profiles_cvmark_changelist"),
                    },
                ],
            },
            # services
            {
                "title": _("Dịch vụ"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Loại dịch vụ"),
                        "icon": "design_services",
                        "link": reverse_lazy("admin:services_typeservice_changelist"),
                    },
                    {
                        "title": _("Gói dịch vụ"),
                        "icon": "widgets",
                        "link": reverse_lazy("admin:services_packageentity_changelist"),
                    },
                    {
                        "title": _("Gói đăng ký"),
                        "icon": "subscriptions",
                        "link": reverse_lazy("admin:services_packagecampaign_changelist"),
                    },
                ],
            },
            # transactions
            {
                "title": _("Giao dịch"),
                "separator": True,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("Lịch sử giao dịch"),
                        "icon": "payments",
                        "link": reverse_lazy("admin:transactions_historymoney_changelist"),
                    },
                ],
            },
            
        ],
    },
}
