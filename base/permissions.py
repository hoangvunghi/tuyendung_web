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
        return obj.user == request.user

class IsPostOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với bài đăng không (thông qua campaign và enterprise)
    """
    def has_object_permission(self, request, view, obj):
        return obj.campaign.enterprise.user == request.user

class IsCampaignOwner(BasePermission):
    """
    Kiểm tra xem user có quyền với chiến dịch không
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
        if obj.user == request.user:
            return True
        # Người đăng bài
        return obj.post.campaign.enterprise.user == request.user
    

        