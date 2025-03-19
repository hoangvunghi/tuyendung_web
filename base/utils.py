from functools import wraps
from django.utils.decorators import method_decorator
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import permission_classes
from .permissions import AdminAccessPermission
from rest_framework.exceptions import PermissionDenied

def admin_or_permission(*permissions):
    """
    Decorator để dễ dàng kết hợp AdminAccessPermission với các quyền khác.
    Admin sẽ luôn có quyền truy cập, không cần kiểm tra các quyền khác.
    
    Sử dụng:
    @api_view(['GET'])
    @admin_or_permission(IsAuthenticated, IsEnterpriseOwner)
    def my_view(request):
        ...
    """
    def decorator(view_func):
        # Sử dụng permission_classes với permission classes gốc và AdminAccessPermission
        permission_classes_decorator = permission_classes([AdminAccessPermission] + list(permissions))
        return permission_classes_decorator(view_func)
    
    return decorator

def create_permission_class_with_admin_override(*permission_classes):
    """
    Tạo một permission class mới kết hợp các permission class đã cho và AdminAccessPermission
    với điều kiện HOẶC: nếu là admin HOẶC thỏa mãn các permission khác
    
    Sử dụng:
    AdminOrOwner = create_permission_class_with_admin_override(IsOwnerOrReadOnly)
    
    @permission_classes([AdminOrOwner])
    def my_view(request):
        ...
    """
    class CombinedPermission(BasePermission):
        def has_permission(self, request, view):
            # Nếu là admin, cho phép ngay lập tức
            if request.user and request.user.is_staff:
                return True
                
            # Kiểm tra từng permission class
            for permission_class in permission_classes:
                instance = permission_class()
                if not hasattr(instance, 'has_permission') or not instance.has_permission(request, view):
                    return False
            
            return True
            
        def has_object_permission(self, request, view, obj):
            # Nếu là admin, cho phép ngay lập tức
            if request.user and request.user.is_staff:
                return True
                
            # Kiểm tra từng permission class
            for permission_class in permission_classes:
                instance = permission_class()
                if hasattr(instance, 'has_object_permission') and not instance.has_object_permission(request, view, obj):
                    return False
            
            return True
    
    return CombinedPermission 