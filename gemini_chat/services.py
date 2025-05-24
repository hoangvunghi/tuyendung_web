from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime

from enterprises.models import EnterpriseEntity, PostEntity, FieldEntity, PositionEntity, CriteriaEntity
from profiles.models import Cv, UserInfo
from accounts.models import UserAccount, UserRole
from .models import GeminiChatSession, GeminiChatMessage

import google.generativeai as genai
import uuid
import re
import json
import os
import logging

# Cấu hình Google Generative AI API
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiChatService:
    """Service để tương tác với Gemini API và quản lý chat"""
    
    def __init__(self):
        """Khởi tạo Gemini Chat Service"""
        self.logger = logging.getLogger(__name__)
        
        # Cấu hình generation
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        # Cấu hình an toàn
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
        
        self.model_name = "gemini-2.0-flash"
    
        # Cache dữ liệu hệ thống để tái sử dụng
        self.system_data_cache = None
        self.cache_last_updated = None
        self.cache_ttl = 3600  # 1 giờ (thời gian tính bằng giây)
    
    def get_system_prompt(self, user):
        """Tạo system prompt dựa trên vai trò của user và dữ liệu hệ thống"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Lấy dữ liệu hệ thống
        system_data = self.get_system_data()
        
        # Format dữ liệu hệ thống thành văn bản
        system_data_text = self._format_system_data_for_prompt(system_data)
        
        base_prompt = f"""Bạn là trợ lý AI hỗ trợ người dùng trên website tuyển dụng 'JobHub'. Hiện tại là {current_time}.

HƯỚNG DẪN TRUY VẤN DỮ LIỆU:
1. ƯU TIÊN DỮ LIỆU TRONG WEBSITE khi nhận được câu hỏi về:
   - Việc làm hiện có trên trang web (vị trí, mức lương, kinh nghiệm, địa điểm, ngành nghề...)
   - Thông tin doanh nghiệp đăng tuyển trên trang web
   - Thông tin ứng viên, hồ sơ tuyển dụng trong hệ thống
   - Thống kê, số liệu về việc làm trên trang web
   - Bất kỳ câu hỏi nào đề cập đến "trên trang web", "trong hệ thống", "hiện có", "đang tuyển"

2. CHỈ TÌM KIẾM INTERNET khi:
   - Câu hỏi về kiến thức chung không liên quan đến dữ liệu cụ thể trên trang web
   - Câu hỏi về kỹ năng viết CV, phỏng vấn, phát triển nghề nghiệp
   - Câu hỏi về xu hướng thị trường việc làm nói chung
   - Câu hỏi chỉ rõ yêu cầu tìm kiếm thông tin từ internet

3. CÁC YÊU CẦU KHÁC:
   - Trả lời ngắn gọn, rõ ràng, lịch sự và thân thiện
   - Hỗ trợ người dùng tìm kiếm việc làm phù hợp với nhu cầu và kỹ năng
   - Không cung cấp thông tin sai lệch hoặc gây hiểu nhầm
   - Không thực hiện hành động trái với đạo đức hoặc quy định pháp luật
   - Tôn trọng tính riêng tư và bảo mật thông tin người dùng
   - Luôn thông báo khi nội dung trả lời từ database hoặc từ internet
4. TÔI YÊU CẦU BẠN PHẢI ĐỌC DATABASE TRƯỚC KHI TRẢ LỜI NGƯỜI DÙNG
   - Dựa vào câu hỏi của người dùng, bạn phải đọc database để tìm kiếm thông tin phù hợp.
   - Nếu có thông tin trong database, hãy sử dụng thông tin đó để trả lời người dùng.
   - Nếu không có thông tin trong database, hãy thông báo cho người dùng rằng dữ liệu không có sẵn.
   - Đừng nên trả id mà hãy trả link của job. Link của job là "https://tuyendungtlu.site/job/" cộng với id của job.
   - Khi người dùng hỏi về link của job thì lấy "https://tuyendungtlu.site/job/" cộng với id của job.
THÔNG TIN VỀ WEBSITE JobHub:
- Website tuyển dụng việc làm uy tín với nhiều ngành nghề
- Kết nối doanh nghiệp và ứng viên tìm việc
- Cung cấp các công cụ tìm kiếm việc làm, đăng tuyển, quản lý hồ sơ
- Hỗ trợ cả người tìm việc và nhà tuyển dụng
- Có các gói dịch vụ premium cho người dùng

DỮ LIỆU HIỆN TẠI CỦA HỆ THỐNG:
{system_data_text}

Khi có yêu cầu về thông tin việc làm, vị trí, doanh nghiệp, hãy ưu tiên sử dụng dữ liệu tôi đã cung cấp ở trên.
Nếu thông tin không có trong dữ liệu đã cung cấp, hãy thông báo cho người dùng rằng dữ liệu không có sẵn.
Chỉ tìm kiếm thông tin trên internet khi nội dung câu hỏi rõ ràng nằm ngoài phạm vi dữ liệu của hệ thống."""

        if user.is_employer():
            employer_prompt = f"""
THÔNG TIN DÀNH CHO NHÀ TUYỂN DỤNG:
- Bạn có thể truy vấn về các ứng viên đã ứng tuyển vào vị trí của bạn
- Tôi có thể hỗ trợ bạn đăng tin tuyển dụng và quản lý hồ sơ ứng viên
- Tôi có thể cung cấp thống kê về hiệu quả tin tuyển dụng của bạn
- Tôi có thể giúp bạn lên chiến lược tuyển dụng hiệu quả
- Tôi có thể hỗ trợ bạn nâng cấp tài khoản premium"""
            return base_prompt + employer_prompt
        else:
            job_seeker_prompt = f"""
THÔNG TIN DÀNH CHO NGƯỜI TÌM VIỆC:
- Bạn có thể truy vấn về việc làm phù hợp với kỹ năng của bạn
- Tôi có thể giúp bạn tìm việc làm theo địa điểm, mức lương, ngành nghề
- Tôi có thể hỗ trợ bạn theo dõi trạng thái hồ sơ ứng tuyển
- Tôi có thể giúp bạn nâng cao cơ hội được tuyển dụng
- Tôi có thể hỗ trợ bạn nâng cấp tài khoản premium"""
            return base_prompt + job_seeker_prompt
    
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
    
    def search_job_posts(self, query=None, city=None, experience=None, position_id=None, limit=5):
        """Tìm kiếm việc làm dựa trên các tiêu chí"""
        from enterprises.models import PostEntity, PositionEntity
        
        posts = PostEntity.objects.filter(is_active=True)
        
        # Lọc theo từ khóa tìm kiếm
        if query and query.strip():
            query_terms = query.split()
            q_object = Q()
            
            # Nếu query là vị trí công việc cụ thể, thử tìm vị trí trong database
            # Ví dụ: "Python Developer" sẽ tìm các vị trí có tên "Python", "Developer" hoặc "Python Developer"
            try:
                position_terms = query.lower().split()
                positions = PositionEntity.objects.all()
                for position in positions:
                    if any(term.lower() in position.name.lower() for term in position_terms):
                        q_object |= Q(position=position)
            except Exception as e:
                self.logger.error(f"Lỗi khi tìm vị trí: {str(e)}")
            
            for term in query_terms:
                q_object |= (
                    Q(title__icontains=term) | 
                    Q(description__icontains=term) | 
                    Q(required__icontains=term) |
                    Q(interest__icontains=term) |
                    Q(position__name__icontains=term) |
                    Q(field__name__icontains=term) |
                    Q(enterprise__company_name__icontains=term)
                )
            
            posts = posts.filter(q_object)
        
        # Lọc theo thành phố
        if city:
            posts = posts.filter(city__icontains=city)
        
        # Lọc theo kinh nghiệm
        if experience:
            posts = posts.filter(experience__icontains=experience)
        
        # Lọc theo vị trí công việc
        if position_id:
            posts = posts.filter(position_id=position_id)
        
        # Sắp xếp kết quả (mới nhất trước)
        posts = posts.order_by('-created_at')
        
        # Giới hạn số lượng kết quả
        posts = posts[:limit]
        
        # Format kết quả
        if not posts:
            return f"Không tìm thấy việc làm phù hợp với tiêu chí của bạn. Tiêu chí tìm kiếm: {query or ''}"
        
        results = []
        for post in posts:
            post_info = {
                'id': post.id,
                'title': post.title,
                'company': post.enterprise.company_name,
                'city': post.city,
                'salary': f"{post.salary_min} - {post.salary_max} triệu VND" if post.salary_min and post.salary_max else "Thỏa thuận",
                'experience': post.experience,
                'job_type': post.type_working,
                'position': post.position.name if post.position else "",
                'field': post.field.name if post.field else "",
                'created_at': post.created_at.strftime('%d/%m/%Y'),
                'deadline': post.deadline.strftime('%d/%m/%Y') if post.deadline else ""
            }
            results.append(post_info)
        
        # Format kết quả thành markdown
        markdown_result = f"### Kết quả tìm kiếm việc làm{' cho ' + query if query else ''}\n\n"
        
        for job in results:
            markdown_result += f"#### {job['title']} (ID: {job['id']})\n"
            markdown_result += f"🏢 **Công ty:** {job['company']}\n"
            markdown_result += f"📍 **Địa điểm:** {job['city']}\n"
            markdown_result += f"💰 **Mức lương:** {job['salary']}\n"
            markdown_result += f"📊 **Kinh nghiệm:** {job['experience']}\n"
            markdown_result += f"🔖 **Loại công việc:** {job['job_type']}\n"
            markdown_result += f"📌 **Vị trí:** {job['position']}\n"
            markdown_result += f"🏭 **Lĩnh vực:** {job['field']}\n"
            markdown_result += f"📅 **Ngày đăng:** {job['created_at']}\n"
            if job['deadline']:
                markdown_result += f"⏰ **Hạn nộp hồ sơ:** {job['deadline']}\n"
            markdown_result += f"🔗 **Link chi tiết:** https://tuyendungtlu.site/job/{job['id']}\n\n"
            markdown_result += "---\n\n"
        
        return markdown_result.strip()
    
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
    
    def get_job_recommendation(self, user):
        """Gợi ý việc làm dựa trên tiêu chí của người dùng"""
        # Chỉ thực hiện cho người dùng đã đăng nhập và là ứng viên
        if not user.is_authenticated or user.is_employer():
            return "Vui lòng đăng nhập với tài khoản ứng viên để nhận gợi ý việc làm phù hợp."
        
        try:
            from enterprises.models import CriteriaEntity, PostEntity
            
            # Lấy tiêu chí tìm việc của người dùng
            criteria = CriteriaEntity.objects.get(user=user)
            
            # Tạo truy vấn cơ bản (chỉ lấy các việc làm đang hoạt động)
            query = Q(status=True)
            
            # Lọc theo thành phố
            if criteria.city:
                query &= Q(city__icontains=criteria.city)
            
            # Lọc theo vị trí công việc
            if criteria.position:
                query &= Q(position=criteria.position)
            
            # Lọc theo lĩnh vực
            if criteria.field:
                query &= Q(field=criteria.field)
            
            # Lọc theo loại công việc
            if criteria.type_working:
                query &= Q(type_working__icontains=criteria.type_working)
            
            # Lọc theo mức lương tối thiểu
            if criteria.salary_min:
                query &= Q(salary_min__gte=criteria.salary_min)
            
            # Lọc theo kinh nghiệm
            if criteria.experience:
                query &= Q(experience__icontains=criteria.experience)
            
            # Thực hiện truy vấn
            posts = PostEntity.objects.filter(query).order_by('-created_at')[:5]
            
            if not posts:
                return "Không tìm thấy việc làm phù hợp với tiêu chí của bạn."
            
            results = []
            for post in posts:
                post_info = {
                    'id': post.id,
                    'title': post.title,
                    'company': post.enterprise.company_name,
                    'city': post.city,
                    'salary': f"{post.salary_min} - {post.salary_max} triệu VND" if post.salary_min and post.salary_max else "Thỏa thuận",
                    'experience': post.experience,
                    'job_type': post.type_working,
                    'position': post.position.name if post.position else "",
                    'field': post.field.name if post.field else "",
                    'created_at': post.created_at.strftime('%d/%m/%Y'),
                    'deadline': post.deadline.strftime('%d/%m/%Y') if post.deadline else ""
                }
                results.append(post_info)
            
            # Format kết quả thành markdown
            markdown_result = "### Việc làm phù hợp với bạn\n\n"
            
            markdown_result += "Dựa trên tiêu chí tìm việc của bạn:\n"
            markdown_result += f"- 📍 **Thành phố:** {criteria.city if criteria.city else 'Không'}\n"
            markdown_result += f"- 📌 **Vị trí:** {criteria.position.name if criteria.position else 'Không'}\n"
            markdown_result += f"- 🏭 **Lĩnh vực:** {criteria.field.name if criteria.field else 'Không'}\n"
            markdown_result += f"- 🔖 **Loại công việc:** {criteria.type_working if criteria.type_working else 'Không'}\n"
            markdown_result += f"- 📊 **Kinh nghiệm:** {criteria.experience if criteria.experience else 'Không'}\n"
            markdown_result += f"- 💰 **Mức lương tối thiểu:** {criteria.salary_min} triệu VND\n\n"
            
            markdown_result += "Tôi tìm thấy các việc làm phù hợp sau:\n\n"
            
            for job in results:
                markdown_result += f"#### {job['title']} (ID: {job['id']})\n"
                markdown_result += f"🏢 **Công ty:** {job['company']}\n"
                markdown_result += f"📍 **Địa điểm:** {job['city']}\n"
                markdown_result += f"💰 **Mức lương:** {job['salary']}\n"
                markdown_result += f"📊 **Kinh nghiệm:** {job['experience']}\n"
                markdown_result += f"🔖 **Loại công việc:** {job['job_type']}\n"
                markdown_result += f"📌 **Vị trí:** {job['position']}\n"
                markdown_result += f"🏭 **Lĩnh vực:** {job['field']}\n"
                markdown_result += f"📅 **Ngày đăng:** {job['created_at']}\n"
                if job['deadline']:
                    markdown_result += f"⏰ **Hạn nộp hồ sơ:** {job['deadline']}\n"
                markdown_result += f"🔗 **Link chi tiết:** https://tuyendungtlu.site/job/{job['id']}\n\n"
                markdown_result += "---\n\n"
            
            return markdown_result.strip()
        
        except CriteriaEntity.DoesNotExist:
            return "Bạn chưa cập nhật tiêu chí tìm việc. Vui lòng vào mục 'Tiêu chí tìm việc' để cập nhật."
    
    def get_highest_paying_jobs(self, limit=5):
        """Lấy danh sách việc làm có mức lương cao nhất"""
        from enterprises.models import PostEntity
        
        posts = PostEntity.objects.filter(is_active=True).order_by('-salary_max', '-salary_min')[:limit]
        
        if not posts:
            return "Không tìm thấy thông tin về việc làm lương cao nhất."
        
        results = []
        for post in posts:
            post_info = {
                'id': post.id,
                'title': post.title,
                'company': post.enterprise.company_name,
                'city': post.city,
                'salary': f"{post.salary_min} - {post.salary_max} triệu VND" if post.salary_min and post.salary_max else "Thỏa thuận",
                'experience': post.experience,
                'job_type': post.type_working,
                'position': post.position.name if post.position else "",
                'field': post.field.name if post.field else "",
                'created_at': post.created_at.strftime('%d/%m/%Y'),
                'deadline': post.deadline.strftime('%d/%m/%Y') if post.deadline else ""
            }
            results.append(post_info)
        
        # Format kết quả thành markdown
        markdown_result = "### Các công việc có mức lương cao nhất\n\n"
        
        for job in results:
            markdown_result += f"#### {job['title']} (ID: {job['id']})\n"
            markdown_result += f"🏢 **Công ty:** {job['company']}\n"
            markdown_result += f"📍 **Địa điểm:** {job['city']}\n"
            markdown_result += f"💰 **Mức lương:** {job['salary']}\n"
            markdown_result += f"📊 **Kinh nghiệm:** {job['experience']}\n"
            markdown_result += f"🔖 **Loại công việc:** {job['job_type']}\n"
            markdown_result += f"📌 **Vị trí:** {job['position']}\n"
            markdown_result += f"🏭 **Lĩnh vực:** {job['field']}\n"
            markdown_result += f"📅 **Ngày đăng:** {job['created_at']}\n"
            if job['deadline']:
                markdown_result += f"⏰ **Hạn nộp hồ sơ:** {job['deadline']}\n"
            markdown_result += f"🔗 **Link chi tiết:** https://tuyendungtlu.site/job/{job['id']}\n\n"
            markdown_result += "---\n\n"
        
        return markdown_result.strip()
    
    def get_most_recent_jobs(self, limit=5):
        """Lấy danh sách việc làm mới đăng gần đây"""
        from enterprises.models import PostEntity
        
        posts = PostEntity.objects.filter(is_active=True).order_by('-created_at')[:limit]
        
        if not posts:
            return "Không tìm thấy thông tin về việc làm mới đăng."
        
        results = []
        for post in posts:
            post_info = {
                'id': post.id,
                'title': post.title,
                'company': post.enterprise.company_name,
                'city': post.city,
                'salary': f"{post.salary_min} - {post.salary_max} triệu VND" if post.salary_min and post.salary_max else "Thỏa thuận",
                'experience': post.experience,
                'job_type': post.type_working,
                'position': post.position.name if post.position else "",
                'field': post.field.name if post.field else "",
                'created_at': post.created_at.strftime('%d/%m/%Y'),
                'deadline': post.deadline.strftime('%d/%m/%Y') if post.deadline else "",
                'days_ago': (timezone.now().date() - post.created_at.date()).days
            }
            results.append(post_info)
        
        # Format kết quả thành markdown
        markdown_result = "### Các việc làm mới đăng gần đây\n\n"
        
        for job in results:
            days_text = f"{job['days_ago']} ngày trước" if job['days_ago'] > 0 else "Hôm nay"
            markdown_result += f"#### {job['title']} (ID: {job['id']}) - *{days_text}*\n"
            markdown_result += f"🏢 **Công ty:** {job['company']}\n"
            markdown_result += f"📍 **Địa điểm:** {job['city']}\n"
            markdown_result += f"💰 **Mức lương:** {job['salary']}\n"
            markdown_result += f"📊 **Kinh nghiệm:** {job['experience']}\n"
            markdown_result += f"🔖 **Loại công việc:** {job['job_type']}\n"
            markdown_result += f"📌 **Vị trí:** {job['position']}\n"
            markdown_result += f"🏭 **Lĩnh vực:** {job['field']}\n"
            if job['deadline']:
                markdown_result += f"⏰ **Hạn nộp hồ sơ:** {job['deadline']}\n"
            markdown_result += f"🔗 **Link chi tiết:** https://tuyendungtlu.site/job/{job['id']}\n\n"
            markdown_result += "---\n\n"
        
        return markdown_result.strip()
    
    def get_stats_data(self):
        """Lấy thống kê hệ thống"""
        from enterprises.models import PostEntity, EnterpriseEntity
        
        # Đếm số lượng việc làm đang hoạt động
        active_jobs_count = PostEntity.objects.filter(is_active=True).count()
        
        # Đếm tổng số việc làm
        total_jobs_count = PostEntity.objects.count()
        
        # Đếm số lượng doanh nghiệp
        enterprise_count = EnterpriseEntity.objects.count()
        
        # Đếm số lượng người dùng
        user_count = UserAccount.objects.count()
        
        # Đếm số lượng ứng viên (người dùng có vai trò 'candidate')
        candidates_count = UserAccount.objects.filter(user_roles__role__name='candidate').count()
        
        # Tính mức lương trung bình
        avg_salary_min = PostEntity.objects.filter(is_active=True, salary_min__isnull=False).values_list('salary_min', flat=True)
        avg_salary_max = PostEntity.objects.filter(is_active=True, salary_max__isnull=False).values_list('salary_max', flat=True)
        
        avg_min = round(sum(avg_salary_min) / len(avg_salary_min)) if avg_salary_min else 0
        avg_max = round(sum(avg_salary_max) / len(avg_salary_max)) if avg_salary_max else 0
        
        # Việc làm theo thành phố
        city_stats = PostEntity.objects.filter(is_active=True).values('city').annotate(count=Count('city')).order_by('-count')[:5]
        
        # Việc làm theo lĩnh vực
        field_stats = PostEntity.objects.filter(is_active=True).values('field__name').annotate(count=Count('field')).order_by('-count')[:5]
        
        # Format kết quả thành markdown
        markdown_result = "### Thống kê hệ thống JobHub\n\n"
        
        markdown_result += "#### Tổng quan\n"
        markdown_result += f"- 📊 **Tổng số việc làm đang tuyển:** {active_jobs_count}\n"
        markdown_result += f"- 📑 **Tổng số tin tuyển dụng:** {total_jobs_count}\n"
        markdown_result += f"- 🏢 **Số lượng doanh nghiệp:** {enterprise_count}\n"
        markdown_result += f"- 👥 **Số lượng người dùng:** {user_count}\n"
        markdown_result += f"- 👨‍💼 **Số lượng ứng viên:** {candidates_count}\n"
        
        markdown_result += "\n#### Mức lương trung bình\n"
        markdown_result += f"- 💰 **Mức lương trung bình:** {avg_min} - {avg_max} triệu VND\n"
        
        markdown_result += "\n#### Top 5 thành phố có nhiều việc làm nhất\n"
        for city in city_stats:
            markdown_result += f"- 🌆 **{city['city']}:** {city['count']} việc làm\n"
        
        markdown_result += "\n#### Top 5 lĩnh vực có nhiều việc làm nhất\n"
        for field in field_stats:
            if field['field__name']:
                markdown_result += f"- 🏭 **{field['field__name']}:** {field['count']} việc làm\n"
        
        return markdown_result.strip()
    
    @transaction.atomic
    def create_chat_session(self, user):
        """Tạo phiên chat mới cho người dùng"""
        try:
            # Tạo phiên chat mới
            session = GeminiChatSession.objects.create(
                user=user,
                title="Phiên chat mới"
            )
            
            # Trả về phiên chat
            return session
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo phiên chat: {str(e)}")
            raise e
    
    @transaction.atomic
    def send_message(self, user, message_content, session_id=None):
        """Gửi tin nhắn và lưu vào cơ sở dữ liệu"""
        try:
            # Tìm hoặc tạo phiên chat
            if session_id:
                try:
                    chat_session = GeminiChatSession.objects.get(id=session_id, user=user)
                except GeminiChatSession.DoesNotExist:
                    chat_session = self.create_chat_session(user)
            else:
                # Tìm phiên chat gần nhất chưa kết thúc của user
                chat_session = GeminiChatSession.objects.filter(
                    user=user,
                    is_ended=False
                ).order_by('-created_at').first()
                
                if not chat_session:
                    chat_session = self.create_chat_session(user)
                
            # Lưu tin nhắn của người dùng
            user_message = GeminiChatMessage.objects.create(
                chat_session=chat_session,
                role="user",
                content=message_content
            )
            
            # Phân tích và xử lý yêu cầu để xác định nguồn dữ liệu
            response_data = self._process_query(message_content, user)
            
            # Lưu phản hồi của AI
            ai_message = GeminiChatMessage.objects.create(
                chat_session=chat_session,
                role="assistant",
                content=response_data["content"]
            )
            
            # Format timestamp theo định dạng Việt Nam
            def format_timestamp(timestamp):
                if not timestamp:
                    return "Không có thời gian"
                try:
                    return timestamp.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    return "Invalid Date"
            
            # Cập nhật tiêu đề phiên chat nếu cần
            if chat_session.title == "Phiên chat mới" and len(message_content) > 10:
                try:
                    # Sử dụng Gemini API để tạo tiêu đề thông minh
                    title = self.generate_chat_title(message_content)
                    chat_session.title = title
                    chat_session.save()
                except Exception as e:
                    self.logger.error(f"Lỗi khi tạo tiêu đề thông minh: {str(e)}")
                    # Fallback to simple title creation
                    if len(message_content) <= 50:
                        title = message_content
                    else:
                        words = message_content.split()
                        if len(words) <= 8:
                            title = message_content[:50] + '...' 
                        else:
                            title = ' '.join(words[:8]) + '...'
                            
                    chat_session.title = title
                    chat_session.save()
            
            # Trả về thông tin tin nhắn và phiên chat
            return {
                "session_id": chat_session.id,
                "title": chat_session.title,
                "user_message": {
                    "id": str(user_message.id),
                    "content": user_message.content,
                    "timestamp": format_timestamp(user_message.timestamp)
                },
                "assistant_message": {
                    "id": str(ai_message.id),
                    "content": ai_message.content,
                    "source_type": response_data["source_type"],
                    "timestamp": format_timestamp(ai_message.timestamp)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi tin nhắn: {str(e)}")
            return {
                "error": f"Đã xảy ra lỗi: {str(e)}"
            }
    
    def _process_query(self, message_content, user):
        """
        Phân tích yêu cầu và để Gemini xử lý toàn bộ dựa trên dữ liệu hệ thống.
        Trả về một dict có:
        - content: Nội dung câu trả lời
        - source_type: Loại nguồn dữ liệu ("gemini_database" hoặc "ai")
        """
        try:
            # Xử lý các truy vấn đơn giản trước khi gọi Gemini
            simple_response = self._handle_simple_queries(message_content, user)
            if simple_response:
                return simple_response
            
            # Lấy dữ liệu hệ thống
            system_data = self.get_system_data()
            system_data_text = self._format_system_data_for_prompt(system_data)

            # Khởi tạo model Gemini
            model = self._initialize_generative_model()

            # Tạo prompt cho Gemini với rule rõ ràng hơn
            prompt = f"""Bạn là trợ lý AI hỗ trợ người dùng trên website tuyển dụng 'JobHub'. 
    Hiện tại là {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}.

    **QUY TẮC QUAN TRỌNG:**
    1. KHI NGƯỜI DÙNG HỎI VỀ LINK CỦA ID: Luôn trả link dạng "https://tuyendungtlu.site/job/[ID]"
    2. KHI HIỂN THỊ VIỆC LÀM: Luôn kèm theo link dạng "https://tuyendungtlu.site/job/[ID]"
    3. KHÔNG BAO GIỜ NÓI "không hỗ trợ xem qua ID" - luôn cung cấp link cụ thể

    **DỮ LIỆU HỆ THỐNG:**
    {system_data_text}

    **YÊU CẦU NGƯỜI DÙNG:**
    {message_content}

    **HƯỚNG DẪN:**
    1. Phân tích yêu cầu của người dùng và sử dụng dữ liệu hệ thống ở trên để trả lời.
    2. Nếu yêu cầu liên quan đến việc làm, vị trí, công ty, hoặc thống kê, hãy sử dụng dữ liệu từ hệ thống.
    3. Nếu không có dữ liệu phù hợp trong hệ thống, hãy trả lời dựa trên kiến thức chung của bạn.
    4. Trả lời bằng tiếng Việt, rõ ràng, ngắn gọn, và định dạng bằng markdown.
    5. Nếu dữ liệu không đủ để trả lời, hãy thông báo: "Không tìm thấy thông tin phù hợp trong hệ thống."
    6. Nếu người dùng yêu cầu lọc hoặc tổng hợp dữ liệu, hãy phân tích và trình bày kết quả theo cách dễ hiểu.

    **VAI TRÒ NGƯỜI DÙNG:**
    {'Nhà tuyển dụng' if user.is_employer() else 'Ứng viên'}

    **TRẢ LỜI:**
    """

            # Gọi API Gemini
            response = model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            # Xử lý phản hồi
            content = response.text
            source_type = "gemini_database" if any(keyword in message_content.lower() for keyword in [
                "tìm việc", "việc làm", "công việc", "tuyển dụng", "trên trang web", "trong hệ thống", "link", "id"
            ]) else "ai"

            return {
                "content": content,
                "source_type": source_type
            }

        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý truy vấn với Gemini: {str(e)}")
            return {
                "content": "Xin lỗi, tôi không thể xử lý yêu cầu của bạn lúc này. Vui lòng thử lại sau.",
                "source_type": "error"
            }
    
    def _handle_simple_queries(self, message_content, user):
        """Xử lý các truy vấn đơn giản không cần gọi Gemini API"""
        message_lower = message_content.lower().strip()
        
        # Xử lý câu hỏi về link của ID
        import re
        link_pattern = r'link.*?(\d+)|(\d+).*?link'
        match = re.search(link_pattern, message_lower)
        if match:
            job_id = match.group(1) or match.group(2)
            if job_id:
                return {
                    "content": f"Link chi tiết của việc làm ID {job_id}:\n\n🔗 **https://tuyendungtlu.site/job/{job_id}**\n\nBạn có thể click vào link trên để xem thông tin chi tiết về công việc này.",
                    "source_type": "gemini_database"
                }
        
        # Xử lý câu hỏi đơn giản về ID
        id_only_pattern = r'^(?:id\s*)?(\d+)$'
        match = re.search(id_only_pattern, message_lower)
        if match:
            job_id = match.group(1)
            return {
                "content": f"Thông tin việc làm ID {job_id}:\n\n🔗 **Link chi tiết:** https://tuyendungtlu.site/job/{job_id}\n\nVui lòng click vào link trên để xem đầy đủ thông tin về công việc này.",
                "source_type": "gemini_database"
            }
        
        return None
    
    def _process_gemini_filter(self, message_content, database_data):
        """Sử dụng Gemini để lọc và phân tích dữ liệu từ database"""
        try:
            # Khởi tạo model Gemini
            model = self._initialize_generative_model()
            
            # Tạo prompt cho Gemini để lọc dữ liệu
            prompt = f"""Tôi có dữ liệu sau từ hệ thống JobHub:

{database_data}

Người dùng đang yêu cầu: "{message_content}"

Vui lòng phân tích và lọc dữ liệu trên để trả lời yêu cầu của người dùng một cách hữu ích nhất.
Yêu cầu:
1. Phân loại và sắp xếp thông tin theo mức độ liên quan
2. Tóm tắt các điểm quan trọng phù hợp với nhu cầu của người dùng
3. Đưa ra gợi ý và nhận xét dựa trên dữ liệu
4. Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu
5. Format kết quả dễ đọc với markdown
6. Bắt đầu với 'Dựa trên dữ liệu của hệ thống JobHub, tôi đã phân tích và tổng hợp:'
"""
            
            # Gọi API
            response = model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Lỗi khi sử dụng Gemini để lọc dữ liệu: {str(e)}")
            return f"Xin lỗi, tôi không thể lọc thông tin theo yêu cầu của bạn. Đây là dữ liệu gốc:\n\n{database_data}"
            
    def get_basic_job_data(self):
        """Lấy dữ liệu cơ bản về việc làm trong hệ thống"""
        from enterprises.models import PostEntity, FieldEntity, PositionEntity
        
        # Lấy 10 việc làm mới nhất đang hoạt động
        recent_posts = PostEntity.objects.filter(is_active=True).order_by('-created_at')[:10]
        
        # Lấy các vị trí công việc
        positions = PositionEntity.objects.all()[:20]
        
        # Lấy các lĩnh vực
        fields = FieldEntity.objects.all()[:20]
        
        # Format kết quả
        basic_data = {
            'recent_posts': [],
            'positions': [],
            'fields': []
        }
        
        for post in recent_posts:
            basic_data['recent_posts'].append({
                'id': post.id,
                'title': post.title,
                'company': post.enterprise.company_name if post.enterprise else "",
                'city': post.city,
                'salary': f"{post.salary_min} - {post.salary_max}" if post.salary_min and post.salary_max else "Thỏa thuận",
                'position': post.position.name if post.position else "",
                'field': post.field.name if post.field else ""
            })
            
        for position in positions:
            basic_data['positions'].append({
                'id': position.id,
                'name': position.name
            })
            
        for field in fields:
            basic_data['fields'].append({
                'id': field.id,
                'name': field.name
            })
            
        return basic_data
    
    def _process_web_query(self, message_content):
        """Xử lý truy vấn bằng cách tìm kiếm thông tin trên web"""
        try:
            # Khởi tạo model Gemini
            model = self._initialize_generative_model()
            
            # Tạo prompt phù hợp cho truy vấn web
            prompt = f"""Hãy cung cấp thông tin cập nhật về: {message_content}
            
            Yêu cầu:
            1. Trả lời bằng tiếng Việt
            2. Đưa ra các gợi ý và hướng dẫn cụ thể
            3. Format câu trả lời dễ đọc với markdown
            4. Tập trung vào các best practices và kinh nghiệm thực tế
            5. Đánh dấu rõ ràng rằng đây là thông tin từ web
            """
            
            # Gọi API
            response = model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Thêm nhãn nguồn vào phản hồi
            web_response = f"""### Thông tin từ internet:

{response.text}

*Lưu ý: Thông tin trên được tổng hợp từ internet và có thể thay đổi theo thời gian.*"""
            
            return web_response
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý truy vấn web: {str(e)}")
            return "Xin lỗi, tôi không thể tìm thấy thông tin phù hợp cho yêu cầu của bạn."
    
    def _process_ai_query(self, message_content):
        """Xử lý truy vấn bằng AI tổng quát"""
        try:
            # Khởi tạo model Gemini
            model = self._initialize_generative_model()
            
            # Tạo prompt cho câu hỏi tổng quát
            prompt = f"""Hãy trả lời câu hỏi sau: {message_content}
            
            Yêu cầu:
            1. Trả lời bằng tiếng Việt
            2. Câu trả lời phải ngắn gọn, dễ hiểu
            3. Format câu trả lời dễ đọc
            4. Trả lời chính xác, khách quan
            """
            
            # Gọi API
            response = model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            return response.text
            
        except Exception as e:
            self.logger.error(f"Lỗi khi xử lý truy vấn AI: {str(e)}")
            return "Xin lỗi, tôi không thể xử lý yêu cầu của bạn lúc này. Vui lòng thử lại sau."
    
    def _initialize_generative_model(self):
        """Khởi tạo model Gemini"""
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
    
    def process_response(self, text, database_data=None):
        """Xử lý phản hồi từ Gemini API hoặc database"""
        if database_data:
            return f"""Dựa trên dữ liệu của hệ thống JobHub:

{database_data}"""
        return text
    
    def _format_chat_history(self, chat_history):
        """Format lịch sử trò chuyện để đưa vào prompt"""
        formatted_history = ""
        for message in chat_history:
            role = "User" if message.role == "user" else "Assistant"
            formatted_history += f"{role}: {message.content}\n\n"
        return formatted_history

    def generate_chat_title(self, message_content):
        """Tạo tiêu đề thông minh cho phiên chat dựa trên nội dung tin nhắn đầu tiên"""
        try:
            # Khởi tạo model
            model = self._initialize_generative_model()
            
            # Tạo prompt để sinh tiêu đề
            prompt = f"""Tin nhắn: "{message_content}"
            
            Hãy tạo một tiêu đề ngắn gọn (dưới 50 ký tự) cho cuộc trò chuyện này.
            Chỉ trả về tiêu đề, không có giải thích hay định dạng thêm.
            Tiêu đề phải bằng tiếng Việt và mô tả ngắn gọn nội dung chính của tin nhắn.
            """
            
            # Gọi API với cấu hình temperature thấp hơn để có kết quả ổn định
            title_config = self.generation_config.copy()
            title_config["temperature"] = 0.1
            title_config["max_output_tokens"] = 50
            
            response = model.generate_content(
                prompt,
                generation_config=title_config,
                safety_settings=self.safety_settings
            )
            
            # Làm sạch tiêu đề
            title = response.text.strip().replace('"', '').replace('\n', ' ')
            
            # Giới hạn độ dài tiêu đề
            if len(title) > 50:
                title = title[:47] + '...'
            
            return title
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo tiêu đề thông minh: {str(e)}")
            # Fallback to simple title creation
            if len(message_content) <= 50:
                return message_content
            else:
                words = message_content.split()
                if len(words) <= 8:
                    return message_content[:50] + '...'
                else:
                    return ' '.join(words[:8]) + '...' 

    def get_system_data(self, force_refresh=False):
        """Lấy dữ liệu hệ thống từ database và cache lại"""
        current_time = datetime.now()
        
        # Kiểm tra nếu cache đã hết hạn hoặc bị buộc làm mới
        if (self.system_data_cache is None or 
            self.cache_last_updated is None or 
            (current_time - self.cache_last_updated).total_seconds() > self.cache_ttl or 
            force_refresh):
            try:
                # Lấy dữ liệu cơ bản
                all_job = PostEntity.objects.all()
                all_company = EnterpriseEntity.objects.all()
                all_position = PositionEntity.objects.all()
                all_field = FieldEntity.objects.all()

                basic_job_data = self.get_basic_job_data()
                
                # Lấy dữ liệu thống kê
                stats_data = self.get_stats_data_raw()
                
                # Tổng hợp dữ liệu hệ thống
                self.system_data_cache = {
                    "all_job": all_job,
                    "all_company": all_company,
                    "all_position": all_position,
                    "all_field": all_field,
                    "basic_job_data": basic_job_data,
                    "stats_data": stats_data,
                    "updated_at": current_time.strftime("%d/%m/%Y %H:%M:%S")
                }
                
                self.cache_last_updated = current_time
                
            except Exception as e:
                self.logger.error(f"Lỗi khi lấy dữ liệu hệ thống: {str(e)}")
                if self.system_data_cache is None:
                    self.system_data_cache = {"error": "Không thể lấy dữ liệu hệ thống"}
        
        return self.system_data_cache
        
    def _format_system_data_for_prompt(self, system_data):
        """Format dữ liệu hệ thống thành văn bản ngắn gọn cho system prompt"""
        if not system_data or "error" in system_data:
            return "Không có dữ liệu hệ thống."

        formatted_text = f"Dữ liệu được cập nhật lúc: {system_data.get('updated_at', 'không xác định')}\n\n"

        # Format việc làm
        basic_job_data = system_data.get('basic_job_data', {})
        if basic_job_data.get('recent_posts'):
            formatted_text += "**VIỆC LÀM GẦN ĐÂY**:\n"
            for post in basic_job_data['recent_posts'][:5]:
                formatted_text += f"- ID: {post['id']} | {post['title']} | {post['company']} | {post['city']} | {post['salary']}\n"

        # Format vị trí
        if basic_job_data.get('positions'):
            formatted_text += "\n**VỊ TRÍ CÔNG VIỆC**:\n"
            formatted_text += ", ".join([pos['name'] for pos in basic_job_data['positions'][:10]]) + "\n"

        # Format lĩnh vực
        if basic_job_data.get('fields'):
            formatted_text += "\n**LĨNH VỰC**:\n"
            formatted_text += ", ".join([field['name'] for field in basic_job_data['fields'][:10]]) + "\n"

        # Format thống kê
        stats_data = system_data.get('stats_data', {})
        if stats_data:
            formatted_text += "\n**THỐNG KÊ**:\n"
            formatted_text += f"- Việc làm đang tuyển: {stats_data.get('active_jobs_count', 'N/A')}\n"
            formatted_text += f"- Tổng tin tuyển dụng: {stats_data.get('total_jobs_count', 'N/A')}\n"
            formatted_text += f"- Doanh nghiệp: {stats_data.get('enterprise_count', 'N/A')}\n"
            formatted_text += f"- Ứng viên: {stats_data.get('candidates_count', 'N/A')}\n"
            formatted_text += f"- Mức lương trung bình: {stats_data.get('avg_min', 'N/A')} - {stats_data.get('avg_max', 'N/A')} triệu VND\n"

        return formatted_text
        
    def get_stats_data_raw(self):
        """Lấy dữ liệu thống kê hệ thống dạng raw"""
        from enterprises.models import PostEntity, EnterpriseEntity
        
        # Đếm số lượng việc làm đang hoạt động
        active_jobs_count = PostEntity.objects.filter(is_active=True).count()
        
        # Đếm tổng số việc làm
        total_jobs_count = PostEntity.objects.count()
        
        # Đếm số lượng doanh nghiệp
        enterprise_count = EnterpriseEntity.objects.count()
        
        # Đếm số lượng người dùng
        user_count = UserAccount.objects.count()
        
        # Đếm số lượng ứng viên (người dùng có vai trò 'candidate')
        candidates_count = UserAccount.objects.filter(user_roles__role__name='candidate').count()
        
        # Tính mức lương trung bình
        avg_salary_min = PostEntity.objects.filter(is_active=True, salary_min__isnull=False).values_list('salary_min', flat=True)
        avg_salary_max = PostEntity.objects.filter(is_active=True, salary_max__isnull=False).values_list('salary_max', flat=True)
        
        avg_min = round(sum(avg_salary_min) / len(avg_salary_min)) if avg_salary_min else 0
        avg_max = round(sum(avg_salary_max) / len(avg_salary_max)) if avg_salary_max else 0
        
        # Việc làm theo thành phố
        city_stats = PostEntity.objects.filter(is_active=True).values('city').annotate(count=Count('city')).order_by('-count')[:5]
        
        # Việc làm theo lĩnh vực
        field_stats = PostEntity.objects.filter(is_active=True).values('field__name').annotate(count=Count('field')).order_by('-count')[:5]
        
        return {
            'active_jobs_count': active_jobs_count,
            'total_jobs_count': total_jobs_count,
            'enterprise_count': enterprise_count,
            'user_count': user_count,
            'candidates_count': candidates_count,
            'avg_min': avg_min,
            'avg_max': avg_max,
            'city_stats': list(city_stats),
            'field_stats': list(field_stats)
        } 