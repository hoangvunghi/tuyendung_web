from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    """
    Cho phép xem (GET, HEAD, OPTIONS) cho tất cả người dùng
    Nhưng chỉ cho phép chỉnh sửa (PUT, DELETE) cho chủ sở hữu
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user

class IsEnterpriseOwner(BasePermission):
    """
    Kiểm tra xem user có phải là chủ doanh nghiệp không
    """
    def has_object_permission(self, request, view, obj):
        return obj.enterprise.user == request.user

class IsAdminUser(BasePermission):
    """
    Chỉ cho phép admin truy cập
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsServiceProvider(BasePermission):
    """
    Kiểm tra xem user có quyền quản lý dịch vụ không
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsSubscriptionOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với gói đăng ký không
    """
    def has_object_permission(self, request, view, obj):
        return obj.campaign.enterprise.user == request.user

class IsTransactionOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với giao dịch không
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsProfileOwner(BasePermission):
    """
    Kiểm tra xem user có phải là chủ của profile không
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsCvOwner(BasePermission):
    """
    Kiểm tra xem user có phải là người tạo CV không
    """
    def has_object_permission(self, request, view, obj):
        from profiles.models import CV  # Import model CV
        # Chỉ kiểm tra thuộc tính post khi đối tượng là CV
        if hasattr(obj, 'post') and hasattr(obj.post, 'enterprise'):
            return obj.post.enterprise.user == request.user
        return False

class IsPostOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với bài đăng không (thông qua campaign và enterprise)
    """
    def has_object_permission(self, request, view, obj):
        return obj.enterprise.user == request.user


class IsFieldManager(BasePermission):
    """
    Kiểm tra xem user có quyền quản lý lĩnh vực không (chỉ admin)
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsPositionManager(BasePermission):
    """
    Kiểm tra xem user có quyền quản lý vị trí không (chỉ admin)
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class IsCriteriaOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với tiêu chí không
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class CanManageCv(BasePermission):
    """
    Kiểm tra xem user có quyền quản lý CV không (người nộp hoặc người đăng bài)
    """
    def has_object_permission(self, request, view, obj):
        # Người nộp CV
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        # Người đăng bài - kiểm tra xem có thuộc tính post không
        if hasattr(obj, 'post') and hasattr(obj.post, 'campaign') and hasattr(obj.post.campaign, 'enterprise'):
            return obj.post.campaign.enterprise.user == request.user
        return False
    
class AdminAccessPermission(BasePermission):
    """
    Cho phép admin truy cập tất cả API và thực hiện mọi thao tác
    Quyền này sẽ override toàn bộ các quyền khác
    """
    def has_permission(self, request, view):
        # Admin luôn có quyền truy cập vào mọi API
        return request.user and request.user.is_staff
        
    def has_object_permission(self, request, view, obj):
        # Admin luôn có quyền thao tác với mọi đối tượng
        return request.user and request.user.is_staff
    

        