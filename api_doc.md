# Tài liệu API

## Thông tin chung
- Base URL: `/api`
- Authentication: JWT Token (`Authorization: Bearer <token>`)
- Phân trang: 
  - Params: `page` và `page_size`
  - Mặc định: 10 items/trang
  - Tối đa: 100 items/trang
- Sắp xếp:
  - `sort_by`: Tên trường
  - `sort_order`: `asc` hoặc `desc`

## 1. Quản lý Doanh nghiệp

### Enterprises
- `GET /enterprises/` - Lấy danh sách doanh nghiệp (có phân trang)
- `GET /enterprises/{id}/` - Xem chi tiết doanh nghiệp
- `POST /enterprises/create/` - Tạo doanh nghiệp mới (yêu cầu đăng nhập)
- `PUT /enterprises/{id}/update/` - Cập nhật doanh nghiệp (chỉ chủ sở hữu)
- `DELETE /enterprises/{id}/delete/` - Xóa doanh nghiệp (chỉ chủ sở hữu)

### Tìm kiếm & Lọc Doanh nghiệp
- `GET /enterprises/search/` - Tìm kiếm doanh nghiệp (có phân trang)
  - Params: `q`, `city`, `field`, `scale`

### Thống kê
- `GET /enterprises/{id}/stats/` - Xem thống kê doanh nghiệp (chỉ chủ sở hữu)
  - Thống kê: số chiến dịch, số bài đăng, số CV theo trạng thái

## 2. Quản lý Chiến dịch

### Campaigns
- `GET /campaigns/` - Lấy danh sách chiến dịch (có phân trang)
  - Filter: `enterprise_id`
- `POST /campaigns/create/` - Tạo chiến dịch mới (yêu cầu đăng nhập)

## 3. Quản lý Bài đăng

### Posts
- `GET /posts/` - Lấy danh sách bài đăng (có phân trang)
  - Filter: `campaign_id`
- `POST /posts/create/` - Tạo bài đăng mới (yêu cầu đăng nhập)

### Tìm kiếm & Lọc Bài đăng
- `GET /posts/search/` - Tìm kiếm bài đăng (có phân trang)
  - Params: `q`, `city`, `position`, `experience`, `type_working`, `salary_min`, `salary_max`

### Gợi ý Bài đăng
- `GET /posts/recommended/` - Lấy danh sách bài đăng phù hợp (yêu cầu đăng nhập)
  - Dựa trên tiêu chí của user

## 4. Quản lý Lĩnh vực

### Fields
- `GET /fields/` - Lấy danh sách lĩnh vực (có phân trang)
- `POST /fields/create/` - Tạo lĩnh vực mới (chỉ admin)

## 5. Bộ lọc

### Filter Options
- `GET /filter-options/` - Lấy danh sách giá trị cho các bộ lọc
  - Bao gồm: thành phố, kinh nghiệm, loại công việc, quy mô doanh nghiệp, lĩnh vực, vị trí

## 6. Quản lý CV

### CV Actions
- `GET /cv/{id}/` - Xem chi tiết CV (tạo notification)
- `PUT /cv/{id}/status/` - Cập nhật trạng thái CV (tạo notification)
- `POST /cv/{id}/mark/` - Đánh dấu CV (tạo notification)

## 7. Quản lý Thông báo

### Notifications
- `GET /notifications/` - Lấy danh sách thông báo (có phân trang)
  - Response: Danh sách thông báo theo thời gian giảm dần
  - Mỗi thông báo bao gồm: loại, tiêu đề, nội dung, thời gian, trạng thái đã đọc

- `POST /notifications/{id}/read/` - Đánh dấu thông báo đã đọc
  - Yêu cầu: User phải là người nhận thông báo

- `GET /notifications/unread-count/` - Lấy số lượng thông báo chưa đọc

### WebSocket Notifications
- Endpoint: `ws://domain/ws/notifications/`
- Events:
  - `cv_viewed`: CV được xem
  - `cv_status_changed`: Trạng thái CV thay đổi
  - `cv_marked`: CV được đánh dấu
  - `interview_invited`: Mời phỏng vấn
  - `message_received`: Tin nhắn mới

## Lưu ý
- Tất cả API liệt kê và tìm kiếm đều hỗ trợ phân trang
- Response luôn trả về định dạng:
```json
{
    "message": "Thông báo",
    "status": 200,
    "data": {
        // Dữ liệu hoặc thông tin phân trang
    }
}
```
- Lỗi sẽ trả về status code tương ứng và message mô tả lỗi
- WebSocket notifications yêu cầu authentication token
- Notifications sẽ được lưu trữ trong database và có thể truy xuất lại