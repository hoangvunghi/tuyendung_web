# Kiến Trúc Hệ Thống Tuyển Dụng (Tổng Quan)

## Tổng Quan Kiến Trúc

```
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|                                    Kiến Trúc Hệ Thống Tuyển Dụng                                 |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+

                   +--------------------------------------------------+
                   |                                                  |
                   |               Người Dùng (Users)                 |
                   |                                                  |
                   +------------------+--+---------------------------+
                                     /    \
                             Tương tác     Tương tác
                                   /        \
                                  /          \
                                 v            v
+------------------+                 +-------------------+                  +------------------+
|                  |                 |                   |                  |                  |
|  Frontend (FE)   | <----------->  |   Backend (BE)    | <------------->  |  External        |
|  (tuyendung-fe)  |      API       |    (tuyendung)    |       API        |  Services        |
|                  |                 |                   |                  |                  |
+--------+---------+                 +---------+---------+                  +---------+--------+
         |                                     |                                      |
         |                                     |                                      |
         v                                     v                                      v
+------------------+                 +-------------------+                  +------------------+
|                  |                 |                   |                  |                  |
|  Vue.js + Vite   |                 |    Django + DRF   |                  |     Storage      |
|  Pinia           | <----------->   |    Celery + Redis | <------------->  |     Auth         |
|  UI Components   |                 |    PostgreSQL     |                  |     Payment      |
|                  |                 |                   |                  |                  |
+------------------+                 +-------------------+                  +------------------+
```

## Luồng Tương Tác Người Dùng Với Hệ Thống

```
+---------------------+             +----------------------+            +----------------------+
|                     |  1. Truy cập |                      | 4. Xử lý   |                      |
|     Người Dùng      | -----------> |      Frontend        | <--------> |      Backend         |
|                     |   website    |                      |  requests  |                      |
+----------+----------+             +----------+-----------+            +-----------+----------+
           |                                   |                                    |
           |                                   |                                    |
           | 2. Tương tác                      | 3. API Calls                       | 5. Truy vấn
           | (click, nhập liệu)                | (HTTP/WebSocket)                   | Database
           v                                   v                                    v
+----------+----------+             +----------+-----------+            +-----------+----------+
|                     |             |                      |            |                      |
|    Giao diện UI     |             |   API Endpoints      |            |      Database        |
|                     |             |                      |            |                      |
+----------+----------+             +----------+-----------+            +-----------+----------+
           |                                   |                                    |
           |                                   |                                    |
           | 8. Hiển thị kết quả               | 7. Response                        | 6. Dữ liệu
           | cho người dùng                    | (JSON/HTML)                        | trả về
           v                                   v                                    v
+----------+----------+             +----------+-----------+            +-----------+----------+
|                     |             |                      |            |                      |
|    Trải nghiệm      |             |   Services &         |            |  External Services   |
|    người dùng       | <---------- |   State Management   | <--------> |  (Auth, Payment...)  |
|                     |  9. Update  |                      |   API      |                      |
+---------------------+    UI       +----------------------+   Calls    +----------------------+
```

## Kiến Trúc Frontend (tuyendung-fe)

```
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                               Frontend (tuyendung-fe)                                         |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+

                          +-------------------+
                          |                   |
                          |   Người Dùng      |
                          |                   |
                          +--------+----------+
                                   |
                                   | Tương tác (Input)
                                   v
+------------------+                                        +------------------+
|                  |          +------------------+          |                  |
|                  |          |                  |          |                  |
|    Components    | <------> |     Views        | <------> |     Stores       |
|    (UI Elements) |          |    (Pages)       |          |  (State Mgmt)    |
|                  |          |                  |          |                  |
+--------+---------+          +--------+---------+          +--------+---------+
         |                             |                             |
         |                             v                             |
         |                    +------------------+                   |
         |                    |                  |                   |
         +---------------->>> |    Services      | <<<---------------+
                              |  (API Clients)   |
                              +--------+---------+
                                       |
                                       v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                                   Vue Router / UI Framework                                   |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                                     Axios / HTTP Client                                       |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                                      Backend API                                              |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
```

## Kiến Trúc Backend (tuyendung)

```
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                               Backend (tuyendung)                                             |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+

                                 +-------------------+
                                 |                   |
                                 |  Frontend Request | 
                                 |                   |
                                 +--------+----------+
                                          |
                                          v
+------------------+                    +------------------+                  +------------------+
|                  |                    |                  |                  |                  |
|     Models       | <----------------> |     Views        | <--------------> |       APIs       |
|   (Data Layer)   |                    | (Business Logic) |                  |   (Endpoints)    |
|                  |                    |                  |                  |                  |
+--------+---------+                    +--------+---------+                  +---------+--------+
         |                                       |                                      |
         |                                       v                                      |
         |                              +------------------+                            |
         |                              |                  |                            |
         +--------------------------->  |    Serializers   | <--------------------------+
                                        | (Data Transform) |
                                        +--------+---------+
                                                 |
                                                 v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                           Django REST Framework (API Layer)                                   |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                              Middlewares / Authentication                                     |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
                                                 |
                                                 v
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                                PostgreSQL (Database)                                          |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+
```

## Luồng Dữ Liệu Đơn Giản

```
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|                           Luồng Dữ Liệu Đơn Giản                                              |
|                                                                                               |
+-----------------------------------------------------------------------------------------------+

   Người Dùng
      |
      v
+-------------+          +------------+          +--------------+
|             |  HTTP    |            |  SQL     |              |
| Trình Duyệt | -------> |  Backend   | <------> |  Database    |
|  Frontend   | <------- |  Server    |          |              |
|             |  JSON    |            |          |              |
+-------------+          +------+-----+          +--------------+
      ^                         |
      |                         |
      |                         v
      |                  +--------------+
      |                  |              |
      +----------------- | Cloud/Third  |
                         | Party APIs   |
                         |              |
                         +--------------+
```

## Luồng Tương Tác Giữa Các Thành Phần

### Frontend (Chi Tiết)

```
1. User Input --> Views: Người dùng tương tác với giao diện (click, nhập liệu, v.v.)
   |
2. Views --> Stores: 
   - Views gọi actions từ Stores để cập nhật trạng thái
   - Views đọc state từ Stores để hiển thị dữ liệu
   |
3. Stores --> Components: 
   - Components nhận props từ Stores thông qua Views
   - Stores cập nhật state -> kích hoạt reactive rendering của Components
   |
4. Views/Components --> Services:
   - Gọi API methods từ Services modules để lấy/gửi dữ liệu
   - Truyền callbacks để xử lý response
   |
5. Services --> HTTP Client (Axios):
   - Tạo và gửi HTTP requests (GET, POST, PUT, DELETE)
   - Thêm headers, parameters, authentication tokens
   |
6. HTTP Client --> Backend API:
   - Gửi requests tới endpoints cụ thể
   - Nhận JSON responses
   |
7. Backend Response --> Services:
   - Parse JSON data
   - Xử lý lỗi và exceptions
   |
8. Services --> Stores:
   - Cập nhật state với dữ liệu mới nhận được
   - Trigger reactive updates
   |
9. Stores --> Views/Components:
   - Re-render UI với dữ liệu mới
   - Cập nhật computed properties
```

#### Ví dụ cụ thể trong Frontend

**Đăng nhập người dùng:**
1. User nhập email/password trong LoginView (View)
2. LoginView gọi `authService.login(credentials)` (Service)
3. AuthService gửi POST request đến `/api/auth/login` (HTTP Client)
4. Backend trả về JWT token
5. AuthService lưu token vào localStorage và trả về User object
6. LoginView gọi `authStore.setUser(user)` (Store)
7. AuthStore cập nhật trạng thái và thông báo cho NavbarComponent (Component)
8. NavbarComponent hiển thị thông tin người dùng đã đăng nhập

### Backend (Chi Tiết)

```
1. HTTP Request --> URLs (urls.py):
   - Request đến endpoint cụ thể (/api/endpoint)
   - Routing map tới view function/class tương ứng
   |
2. URLs --> Views (views.py):
   - Views nhận HTTP requests
   - Trích xuất parameters, form data, JSON
   - Kiểm tra authentication/permissions
   |
3. Views <--> Models (models.py):
   - Views gọi queries trên models để truy vấn/cập nhật dữ liệu
   - Models trả về QuerySets hoặc instances
   - Views thực hiện business logic trên dữ liệu
   |
4. Views <--> Serializers (serializers.py):
   - Serializers chuyển đổi Model instances thành JSON
   - Serializers validate dữ liệu input từ request
   - Serializers tạo/cập nhật Model instances từ JSON
   |
5. Models <--> Database:
   - ORM tạo và thực thi SQL queries
   - Database trả về result sets
   - Models map data thành Python objects
   |
6. Views --> HTTP Response:
   - Trả về serialized data (JSON)
   - Đặt HTTP status codes
   - Thiết lập response headers
```

#### Ví dụ cụ thể trong Backend

**Lấy danh sách job posts:**
1. Client gửi GET request đến `/api/posts/` (URL)
2. URLs map request đến `PostViewSet.list()` (View)
3. View thực hiện permission check (Authentication)
4. View gọi `PostEntity.objects.filter(is_active=True)` (Model)
5. Database trả về records cho Model
6. View sử dụng `PostSerializer(posts, many=True)` để chuyển đổi (Serializer)
7. Serializer convert model data thành JSON
8. View trả về serialized data với status 200 OK

**Ứng tuyển vào job:**
1. Client gửi POST request đến `/api/posts/{id}/apply/` với CV data (URL)
2. `PostViewSet.apply` nhận request (View)
3. View kiểm tra user authentication và permissions 
4. View khởi tạo `CVSerializer(data=request.data)` (Serializer)
5. Serializer validate data input
6. Nếu valid, tạo instance `Cv(user=request.user, post_id=id, ...)` (Model)
7. Model lưu record vào database
8. View gọi `notification_service.notify_employer()` để thông báo cho nhà tuyển dụng
9. View trả về response với status 201 Created

### Tương tác với External Services

```
1. Backend Service <--> Google OAuth:
   - Redirect người dùng đến Google Auth page
   - Nhận OAuth token từ Google
   - Lấy user info từ Google API
   - Tạo/update user và trả về JWT
   
2. Backend <--> Cloudinary CDN:
   - Upload files (CV, hình ảnh) đến Cloudinary
   - Nhận URL và metadata
   - Lưu references vào database
   
3. Backend <--> VNPay Gateway:
   - Tạo payment request với package info
   - Redirect user đến VNPay payment page
   - Nhận payment callback từ VNPay
   - Xác thực và cập nhật payment status trong database
```

### Luồng Dữ Liệu Đầy Đủ Cho Một Tính Năng

**Tính năng: Ứng viên nộp CV cho một job posting**

1. **Frontend**:
   - Người dùng xem chi tiết công việc trong `JobDetailView`
   - Click "Apply Now" -> Mở `ApplyForm` component
   - Upload CV file và nhập thông tin
   - `ApplyForm` gọi `jobService.applyForJob(jobId, formData)`
   - `JobService` tạo FormData với file và JSON data
   - Gửi POST request đến `/api/posts/{id}/apply/`

2. **Backend**:
   - Request được route đến `PostViewSet.apply`
   - `PostViewSet` kiểm tra authentication và permissions
   - File được upload đến Cloudinary thông qua `upload_service`
   - Tạo `Cv` model instance với Cloudinary URL và metadata
   - Lưu instance vào database
   - Tạo `Notification` cho employer
   - Tạo response với CV details

3. **Real-time Notification**:
   - Backend broadcast WebSocket message đến employer channel
   - Frontend của employer nhận notification thông qua WebSocket
   - Notification hiển thị trong UI của employer

4. **Employer Review**:
   - Employer xem CV trong `CVDetailView`
   - Thay đổi status (Approved/Rejected)
   - Gửi response đến ứng viên
   - Realtime notification đến ứng viên

## Các Công Nghệ Chính

### Frontend
- **Framework**: Vue.js 3
- **Build Tool**: Vite
- **State Management**: Pinia
- **UI Framework**: Tailwind CSS
- **HTTP Client**: Axios

### Backend
- **Framework**: Django + Django REST Framework
- **Database**: PostgreSQL
- **Caching**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT, OAuth2

### External Services
- **Storage**: Cloudinary, AWS S3
- **Authentication**: Google OAuth
- **Payment**: VNPay

## Thành Phần Chính Của Hệ Thống

### Frontend
1. **UI Components**: Các thành phần giao diện người dùng có thể tái sử dụng
2. **Views/Pages**: Các trang chức năng chính của ứng dụng
3. **Services**: Kết nối với API backend
4. **Stores**: Quản lý trạng thái ứng dụng

### Backend
1. **Models**: Đại diện cho cấu trúc dữ liệu và quan hệ
2. **Views**: Xử lý logic và điều khiển
3. **Serializers**: Chuyển đổi giữa dữ liệu JSON và Python
4. **URLs & APIs**: Định nghĩa các endpoint

### Database
Cơ sở dữ liệu quan hệ PostgreSQL lưu trữ tất cả dữ liệu của hệ thống.

---

*Ghi chú: Sơ đồ này cung cấp cái nhìn tổng quan đơn giản về kiến trúc hệ thống, tập trung vào các thành phần chính mà không đi vào chi tiết các module cụ thể.* 