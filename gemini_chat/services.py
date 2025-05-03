import uuid
import google.generativeai as genai
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from enterprises.models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from profiles.models import Cv, UserInfo
from accounts.models import UserAccount
from .models import GeminiChatSession, GeminiChatMessage

class GeminiChatService:
    """
    Service class để tương tác với Gemini API và truy xuất dữ liệu từ cơ sở dữ liệu
    """
    
    def __init__(self):
        # Cấu hình Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-2.0-flash'  # Hoặc gemini-2.5-flash/pro tùy theo nhu cầu
    
    def get_system_prompt(self, user):
        """
        Tạo system prompt dựa trên thông tin người dùng
        """
        is_employer = user.is_employer() if user.is_authenticated else False
        
        # Lấy thông tin người dùng từ cơ sở dữ liệu (nếu có)
        user_info = None
        enterprise = None
        criteria = None
        
        if user.is_authenticated:
            # Lấy thông tin cá nhân
            try:
                user_info = UserInfo.objects.filter(user=user).first()
            except:
                pass
                
            # Lấy thông tin doanh nghiệp nếu là nhà tuyển dụng
            if is_employer:
                try:
                    enterprise = EnterpriseEntity.objects.filter(user=user).first()
                except:
                    pass
            else:
                # Lấy tiêu chí tìm việc nếu là người tìm việc
                try:
                    criteria = CriteriaEntity.objects.filter(user=user).first()
                except:
                    pass
        
        # Tạo system prompt
        system_prompt = f"""
        Bạn là trợ lý ảo của hệ thống tuyển dụng và người dùng này là {"nhà tuyển dụng" if is_employer else "người tìm việc"}.
        
        # Thông tin người dùng
        - Username: {user.username if user.is_authenticated else "Khách"}
        - Email: {user.email if user.is_authenticated else ""}
        - Loại tài khoản: {"Premium" if user.is_premium else "Tiêu chuẩn"} 
        """
        
        # Thêm thông tin chi tiết doanh nghiệp nếu là nhà tuyển dụng
        if is_employer and enterprise:
            system_prompt += f"""
            # Thông tin doanh nghiệp
            - Tên công ty: {enterprise.company_name}
            - Địa chỉ: {enterprise.address}, {enterprise.city}
            - Lĩnh vực hoạt động: {enterprise.field_of_activity}
            - Quy mô: {enterprise.scale}
            - Trạng thái: {"Đã kích hoạt" if enterprise.is_active else "Chưa kích hoạt"}
            
            # Tin tuyển dụng
            {self._get_enterprise_job_posts(enterprise)}
            """
        
        # Thêm thông tin cá nhân và tiêu chí tìm việc nếu là người tìm việc
        if not is_employer:
            if user_info:
                system_prompt += f"""
                # Thông tin cá nhân
                - Họ tên: {user_info.fullname if user_info.fullname else "Chưa cập nhật"}
                - Giới tính: {user_info.gender if hasattr(user_info, 'gender') else "Chưa cập nhật"}
                - Địa chỉ: {user_info.address if hasattr(user_info, 'address') else "Chưa cập nhật"}, {user_info.city if hasattr(user_info, 'city') and user_info.city else ""}
                """
            
            if criteria:
                system_prompt += f"""
                # Tiêu chí tìm việc
                - Thành phố: {criteria.city if criteria.city else "Không có yêu cầu"}
                - Kinh nghiệm: {criteria.experience if criteria.experience else "Không có yêu cầu"}
                - Lĩnh vực: {criteria.field.name if criteria.field else "Chưa thiết lập"}
                - Vị trí: {criteria.position.name if criteria.position else "Chưa thiết lập"}
                - Loại công việc: {criteria.type_working if criteria.type_working else "Không có yêu cầu"}
                - Quy mô công ty: {criteria.scales if criteria.scales else "Không có yêu cầu"}
                - Mức lương tối thiểu: {f"{criteria.salary_min} triệu đồng" if criteria.salary_min > 0 else "Không có yêu cầu"}
                """
        
        # Hướng dẫn trả lời
        system_prompt += """
        # Hướng dẫn trả lời
        - Trả lời bằng tiếng Việt rõ ràng, dễ hiểu
        - Sử dụng thông tin từ cơ sở dữ liệu khi có thể
        - Giúp đỡ người dùng trong việc tìm kiếm việc làm, viết CV, chuẩn bị phỏng vấn, hoặc đăng tin tuyển dụng
        - Đưa ra lời khuyên phù hợp với loại tài khoản (Premium hoặc Tiêu chuẩn)
        - Tuyệt đối không cung cấp thông tin mật hoặc vi phạm chính sách bảo mật
        
        Hãy tập trung vào việc cung cấp câu trả lời hữu ích và chính xác nhất có thể.
        """
        
        return system_prompt
    
    def _get_enterprise_job_posts(self, enterprise):
        """Lấy thông tin bài đăng tuyển dụng của doanh nghiệp"""
        if not enterprise:
            return "Không có dữ liệu tin tuyển dụng"
            
        # Lấy 5 bài đăng gần nhất
        posts = PostEntity.objects.filter(enterprise=enterprise).order_by('-created_at')[:5]
        
        if not posts:
            return "Doanh nghiệp chưa có tin tuyển dụng nào"
            
        posts_info = []
        for post in posts:
            # Đếm số đơn ứng tuyển
            cv_count = Cv.objects.filter(post=post).count()
            
            posts_info.append(f"""
            - Tiêu đề: {post.title}
            - Vị trí: {post.position.name if post.position else ""}
            - Kinh nghiệm: {post.experience}
            - Lương: {f"Từ {post.salary_min} đến {post.salary_max} triệu" if not post.is_salary_negotiable else "Thỏa thuận"}
            - Thành phố: {post.city}
            - Số lượng ứng viên đã ứng tuyển: {cv_count}
            - Trạng thái: {"Đang hiển thị" if post.is_active else "Chưa đăng"}
            """)
        
        return "Một số tin tuyển dụng gần đây:\n" + "\n".join(posts_info)
    
    def search_job_posts(self, query, city=None, experience=None, position_id=None, limit=5):
        """Tìm kiếm bài đăng dựa trên từ khóa và các tiêu chí"""
        search_query = Q(is_active=True)
        
        if query:
            search_query &= (Q(title__icontains=query) | 
                          Q(description__icontains=query) |
                          Q(required__icontains=query))
        
        if city:
            search_query &= Q(city__iexact=city)
        
        if experience:
            search_query &= Q(experience__iexact=experience)
            
        if position_id:
            search_query &= Q(position_id=position_id)
            
        posts = PostEntity.objects.filter(search_query).order_by('-created_at')[:limit]
        
        if not posts:
            return "Không tìm thấy việc làm phù hợp với yêu cầu"
            
        results = []
        for post in posts:
            results.append(f"""
            - Tiêu đề: {post.title}
            - Công ty: {post.enterprise.company_name}
            - Vị trí: {post.position.name}
            - Kinh nghiệm: {post.experience}
            - Lương: {f"Từ {post.salary_min} đến {post.salary_max} triệu" if not post.is_salary_negotiable else "Thỏa thuận"}
            - Thành phố: {post.city}
            - ID: {post.id}
            """)
            
        return "Kết quả tìm kiếm việc làm:\n" + "\n".join(results)
    
    def search_candidates(self, query, city=None, experience=None, position_id=None, limit=5):
        """Tìm kiếm ứng viên dựa trên từ khóa và các tiêu chí"""
        # Chỉ dành cho nhà tuyển dụng có quyền premium
        
        # Tạo query tìm kiếm CV
        criteria_query = Q()
        
        if city:
            criteria_query |= Q(city=city)
            
        if experience:
            criteria_query |= Q(experience=experience)
            
        if position_id:
            criteria_query |= Q(position_id=position_id)
            
        # Tìm kiếm tiêu chí phù hợp
        criteria = CriteriaEntity.objects.filter(criteria_query)
        
        if not criteria:
            return "Không tìm thấy ứng viên phù hợp với yêu cầu"
            
        # Lấy thông tin ứng viên
        users = UserAccount.objects.filter(criteria__in=criteria).distinct()
        
        if not users:
            return "Không tìm thấy ứng viên phù hợp với yêu cầu"
            
        results = []
        for user in users[:limit]:
            user_info = UserInfo.objects.filter(user=user).first()
            user_criteria = CriteriaEntity.objects.filter(user=user).first()
            
            if user_info:
                results.append(f"""
                - Họ tên: {user_info.fullname if user_info.fullname else user.username}
                - Email: {user.email}
                - Kinh nghiệm mong muốn: {user_criteria.experience if user_criteria else "Không có thông tin"}
                - Vị trí mong muốn: {user_criteria.position.name if user_criteria and user_criteria.position else "Không có thông tin"}
                - Thành phố: {user_criteria.city if user_criteria else "Không có thông tin"}
                """)
                
        if not results:
            return "Không tìm thấy ứng viên phù hợp với yêu cầu"
            
        return "Kết quả tìm kiếm ứng viên:\n" + "\n".join(results)
    
    def get_job_recommendation(self, user, limit=5):
        """Lấy gợi ý việc làm dựa trên tiêu chí tìm việc của người dùng"""
        if not user.is_authenticated:
            return "Vui lòng đăng nhập để nhận gợi ý việc làm phù hợp"
            
        try:
            criteria = CriteriaEntity.objects.get(user=user)
        except CriteriaEntity.DoesNotExist:
            return "Bạn chưa thiết lập tiêu chí tìm việc. Vui lòng cập nhật để nhận gợi ý phù hợp"
            
        query = Q(is_active=True)
        
        if criteria.city:
            query &= Q(city__iexact=criteria.city)
            
        if criteria.experience:
            query &= Q(experience__iexact=criteria.experience)
            
        if criteria.type_working:
            query &= Q(type_working__iexact=criteria.type_working)
            
        if criteria.position:
            query &= Q(position=criteria.position)
            
        if criteria.field:
            query &= (Q(field=criteria.field) | Q(position__field=criteria.field))
            
        if criteria.salary_min > 0:
            query &= Q(salary_min__gte=criteria.salary_min)
            
        recommended_jobs = PostEntity.objects.filter(query).order_by('-created_at')[:limit]
        
        if not recommended_jobs:
            return "Hiện tại chưa có việc làm phù hợp với tiêu chí của bạn"
            
        results = []
        for job in recommended_jobs:
            results.append(f"""
            - Tiêu đề: {job.title}
            - Công ty: {job.enterprise.company_name}
            - Vị trí: {job.position.name}
            - Kinh nghiệm: {job.experience}
            - Lương: {f"Từ {job.salary_min} đến {job.salary_max} triệu" if not job.is_salary_negotiable else "Thỏa thuận"}
            - Thành phố: {job.city}
            - ID: {job.id}
            """)
            
        return "Gợi ý việc làm phù hợp với bạn:\n" + "\n".join(results)
    
    @transaction.atomic
    def create_chat_session(self, user):
        """Tạo phiên chat mới"""
        session_id = str(uuid.uuid4())
        
        # Tạo phiên chat
        session = GeminiChatSession.objects.create(
            user=user,
            session_id=session_id,
            title="Cuộc trò chuyện mới"
        )
        
        # Thêm tin nhắn hệ thống đầu tiên
        system_prompt = self.get_system_prompt(user)
        GeminiChatMessage.objects.create(
            session=session,
            role='system',
            content=system_prompt
        )
        
        return session
    
    @transaction.atomic
    def send_message(self, user, message_content, session_id=None):
        """Gửi tin nhắn và nhận phản hồi từ Gemini"""
        # Lấy hoặc tạo phiên chat
        if not session_id:
            session = self.create_chat_session(user)
        else:
            try:
                session = GeminiChatSession.objects.get(session_id=session_id, user=user)
                if not session.is_active:
                    # Tạo phiên mới nếu phiên cũ không còn hoạt động
                    session = self.create_chat_session(user)
            except GeminiChatSession.DoesNotExist:
                session = self.create_chat_session(user)
        
        # Cập nhật thời gian sửa đổi của phiên
        session.save(update_fields=['updated_at'])
        
        # Lưu tin nhắn người dùng
        user_message = GeminiChatMessage.objects.create(
            session=session,
            role='user',
            content=message_content
        )
        
        # Lấy tất cả tin nhắn trước đó trong phiên
        previous_messages = list(GeminiChatMessage.objects.filter(
            session=session
        ).order_by('created_at'))
        
        # Tạo history cho Gemini API
        history = []
        for msg in previous_messages:
            if msg.role == 'user':
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == 'model':
                history.append({"role": "model", "parts": [msg.content]})
            # Bỏ qua tin nhắn system vì đã được xử lý trong prompt
        
        # Phân tích tin nhắn để xác định nếu cần truy vấn database
        response_content = ""
        
        try:
            # Khởi tạo model Gemini
            model = genai.GenerativeModel(self.model_name)
            gemini_response = model.generate_content(message_content, stream=False)
            response_content = gemini_response.text
        except Exception as e:
            response_content = f"Xin lỗi, tôi gặp sự cố khi xử lý yêu cầu của bạn. Lỗi: {str(e)}"
        
        # Lưu phản hồi
        model_message = GeminiChatMessage.objects.create(
            session=session,
            role='model',
            content=response_content
        )
        
        # Cập nhật tiêu đề phiên chat nếu là phiên mới
        if session.title == "Cuộc trò chuyện mới" and len(previous_messages) <= 1:
            try:
                # Tạo tiêu đề ngắn gọn từ tin nhắn đầu tiên
                title_prompt = f"Tạo tiêu đề ngắn gọn (dưới 50 ký tự) cho cuộc trò chuyện này dựa trên câu hỏi: '{message_content}'"
                title_model = genai.GenerativeModel('gemini-2.0-flash')
                title_response = title_model.generate_content(title_prompt)
                
                new_title = title_response.text.strip()
                if len(new_title) > 255:
                    new_title = new_title[:252] + "..."
                
                session.title = new_title
                session.save(update_fields=['title'])
            except:
                # Nếu không thể tạo tiêu đề, sử dụng một phần của tin nhắn đầu tiên
                if len(message_content) > 50:
                    session.title = message_content[:47] + "..."
                else:
                    session.title = message_content
                session.save(update_fields=['title'])
        
        return {
            'session': session,
            'user_message': user_message,
            'model_message': model_message
        } 