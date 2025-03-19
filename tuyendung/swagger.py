from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from django.urls import path
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Tuyển Dụng API",
        default_version='v1',
        description="""
        API documentation cho hệ thống tuyển dụng.
        
        ## Xác thực
        Hầu hết các API yêu cầu xác thực qua JWT Token.
        Thêm header: `Authorization: Bearer <token>`
        
        ## Phân trang
        Các API trả về nhiều kết quả đều hỗ trợ phân trang với các tham số:
        - `page`: Số trang (mặc định: 1)
        - `page_size`: Số lượng item mỗi trang (mặc định: 10, tối đa: 100)
        
        ## Response Format
        Tất cả các API đều trả về format thống nhất:
        ```
        {
            "message": "Thông báo",
            "status": 200,
            "data": { ... }
        }
        ```
        
        ## Sắp xếp
        Nhiều API hỗ trợ sắp xếp kết quả với các tham số:
        - `sort_by`: Tên trường để sắp xếp
        - `sort_order`: "asc" hoặc "desc"
        """,
        terms_of_service="https://www.tuyendung.com/terms/",
        contact=openapi.Contact(email="contact@tuyendung.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] 