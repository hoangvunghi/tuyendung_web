# Hệ thống Phân quyền

Dự án này sử dụng một hệ thống phân quyền linh hoạt, cho phép admin có thể truy cập và quản lý tất cả các đối tượng, trong khi người dùng thông thường chỉ có thể tương tác với dữ liệu của họ.

## Cấu trúc quyền

### AdminAccessPermission

Lớp quyền `AdminAccessPermission` là lớp đặc biệt cho phép admin truy cập mọi API và thao tác với mọi đối tượng. Admin được định nghĩa là người dùng có thuộc tính `is_staff=True`.

```python
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
```

### Các Quyền Đặc biệt

Dự án định nghĩa nhiều quyền đặc biệt để kiểm tra quyền truy cập đối với các đối tượng cụ thể:

- `IsOwnerOrReadOnly`: Cho phép xem cho tất cả người dùng, chỉnh sửa chỉ cho chủ sở hữu
- `IsEnterpriseOwner`: Kiểm tra xem người dùng có phải là chủ doanh nghiệp không
- `IsPostOwner`: Kiểm tra quyền với bài đăng thông qua campaign và enterprise
- `IsCampaignOwner`: Kiểm tra quyền với chiến dịch
- `IsFieldManager`: Quyền quản lý lĩnh vực (chỉ admin)
- `IsCvOwner`: Kiểm tra xem người dùng có phải là người tạo CV không
- ... và nhiều quyền khác

## Cách Sử Dụng

### 1. Sử dụng Trực tiếp

Bạn có thể sử dụng `AdminAccessPermission` cùng với các quyền khác trong decorator `permission_classes`:

```python
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEnterpriseOwner, AdminAccessPermission])
def update_enterprise(request, pk):
    # ...
```

Tuy nhiên, cách này không hiệu quả vì thực tế là quyền được kiểm tra tuần tự và cần thỏa mãn TẤT CẢ các quyền.

### 2. Sử dụng Quyền Kết Hợp (Recommended)

Dự án cung cấp hàm tiện ích `create_permission_class_with_admin_override` để tạo lớp quyền kết hợp:

```python
# Tạo lớp quyền kết hợp
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)

# Sử dụng lớp quyền kết hợp
@api_view(['PUT'])
@permission_classes([IsAuthenticated, AdminOrEnterpriseOwner])
def update_enterprise(request, pk):
    # ...
```

Với cách này, API sẽ cho phép truy cập nếu người dùng HOẶC là admin HOẶC thỏa mãn quyền chỉ định (ví dụ: `IsEnterpriseOwner`).

### 3. Kết hợp Nhiều Quyền

Bạn cũng có thể kết hợp nhiều quyền:

```python
ComplexPermission = create_permission_class_with_admin_override(IsEnterpriseOwner, IsPostOwner)
```

Trong trường hợp này, người dùng cần thỏa mãn TẤT CẢ các quyền được liệt kê, TRỪ KHI họ là admin.

## Các Lớp Quyền Kết Hợp Đã Định Nghĩa

Dự án đã định nghĩa sẵn một số lớp quyền kết hợp:

```python
# Trong file enterprises/views.py
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)
AdminOrPostOwner = create_permission_class_with_admin_override(IsPostOwner)
AdminOrCampaignOwner = create_permission_class_with_admin_override(IsCampaignOwner)

# Trong file interviews/views.py
AdminOrEnterpriseOwner = create_permission_class_with_admin_override(IsEnterpriseOwner)
```

## Best Practices

1. **Sử dụng quyền kết hợp**: Thay vì sử dụng `AdminAccessPermission` trực tiếp, hãy sử dụng hàm `create_permission_class_with_admin_override`
2. **Kiểm tra quyền nghiêm ngặt**: Luôn kiểm tra quyền truy cập đối với các API thao tác dữ liệu
3. **Sử dụng Swagger**: Ghi rõ các yêu cầu quyền trong tài liệu Swagger để người dùng API hiểu rõ hơn

## Admin API Access

Với hệ thống phân quyền này, người dùng admin có thể:

1. Truy cập và xem tất cả dữ liệu trong hệ thống
2. Thực hiện mọi thao tác CRUD trên mọi đối tượng
3. Giám sát và quản lý toàn bộ hoạt động của ứng dụng

Tuy nhiên, API vẫn thực hiện các kiểm tra logic khác (ví dụ: xác thực dữ liệu đầu vào) để đảm bảo tính nhất quán của dữ liệu. 