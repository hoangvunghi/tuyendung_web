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
    
    def get_system_prompt(self, user):
        """Tạo system prompt dựa trên vai trò của user"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
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

THÔNG TIN VỀ WEBSITE JobHub:
- Website tuyển dụng việc làm uy tín với nhiều ngành nghề
- Kết nối doanh nghiệp và ứng viên tìm việc
- Cung cấp các công cụ tìm kiếm việc làm, đăng tuyển, quản lý hồ sơ
- Hỗ trợ cả người tìm việc và nhà tuyển dụng
- Có các gói dịch vụ premium cho người dùng

Khi có yêu cầu cung cấp thông tin từ database, hãy sử dụng dữ liệu tôi cung cấp. 
Nếu không có dữ liệu hoặc yêu cầu không liên quan đến dữ liệu của hệ thống, hãy tìm kiếm thông tin phù hợp trên internet."""

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
        from enterprises.models import PostEntity
        
        posts = PostEntity.objects.filter(is_active=True)
        
        # Lọc theo từ khóa tìm kiếm
        if query and query.strip():
            query_terms = query.split()
            q_object = Q()
            
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
        markdown_result = "### Kết quả tìm kiếm việc làm\n\n"
        
        for job in results:
            markdown_result += f"#### [{job['title']}](job/{job['id']})\n"
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
            markdown_result += f"🔗 **Xem chi tiết:** [ID: {job['id']}](job/{job['id']})\n\n"
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
                markdown_result += f"#### [{job['title']}](job/{job['id']})\n"
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
                markdown_result += f"🔗 **Xem chi tiết:** [ID: {job['id']}](job/{job['id']})\n\n"
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
            markdown_result += f"#### [{job['title']}](job/{job['id']})\n"
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
            markdown_result += f"🔗 **Xem chi tiết:** [ID: {job['id']}](job/{job['id']})\n\n"
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
            markdown_result += f"#### [{job['title']}](job/{job['id']}) - *{days_text}*\n"
            markdown_result += f"🏢 **Công ty:** {job['company']}\n"
            markdown_result += f"📍 **Địa điểm:** {job['city']}\n"
            markdown_result += f"💰 **Mức lương:** {job['salary']}\n"
            markdown_result += f"📊 **Kinh nghiệm:** {job['experience']}\n"
            markdown_result += f"🔖 **Loại công việc:** {job['job_type']}\n"
            markdown_result += f"📌 **Vị trí:** {job['position']}\n"
            markdown_result += f"🏭 **Lĩnh vực:** {job['field']}\n"
            if job['deadline']:
                markdown_result += f"⏰ **Hạn nộp hồ sơ:** {job['deadline']}\n"
            markdown_result += f"🔗 **Xem chi tiết:** [ID: {job['id']}](job/{job['id']})\n\n"
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
                chat_session = self.create_chat_session(user)
                
            # Lưu tin nhắn của người dùng
            user_message = GeminiChatMessage.objects.create(
                chat_session=chat_session,
                role="user",
                content=message_content
            )
            
            # Lấy toàn bộ nội dung trò chuyện trước đó để phân tích ngữ cảnh đầy đủ
            previous_messages = GeminiChatMessage.objects.filter(
                chat_session=chat_session
            ).order_by('timestamp')
            
            # Kết hợp các tin nhắn trước đó để hiểu ngữ cảnh
            context_messages = []
            for msg in previous_messages:
                if msg.id != user_message.id:  # Bỏ qua tin nhắn hiện tại
                    context_messages.append({
                        'role': msg.role,
                        'content': msg.content
                    })
            
            # Thử truy vấn cơ sở dữ liệu với ngữ cảnh đầy đủ
            database_data = None
            # Chỉ dùng tin nhắn mới để truy vấn database
            database_data = self._process_database_queries(message_content, user)
            
            # Nếu không tìm thấy trong database và có đủ ngữ cảnh, thử phân tích ngữ cảnh
            if not database_data and len(context_messages) > 0:
                # Tạo một ngữ cảnh hoàn chỉnh từ các tin nhắn trước để tìm trong database
                context_content = self._analyze_conversation_context(context_messages, message_content)
                if context_content:
                    database_data = self._process_database_queries(context_content, user)
            
            if database_data:
                # Xử lý phản hồi với dữ liệu từ database
                response_content = self.process_response(None, database_data)
            else:
                # Gọi Gemini API nếu không có dữ liệu từ database
                # Lấy system prompt
                system_prompt = self.get_system_prompt(user)
                
                # Khởi tạo model Gemini
                model = self._initialize_generative_model()
                
                # Lấy lịch sử chat
                chat_history = []
                
                # Lấy tin nhắn của phiên chat hiện tại
                messages = GeminiChatMessage.objects.filter(
                    chat_session=chat_session
                ).order_by('timestamp')[:30]  # Tăng giới hạn từ 20 lên 30 tin nhắn gần nhất
                
                for msg in messages:
                    if msg.role == "user":
                        chat_history.append({"role": "user", "parts": [msg.content]})
                    else:
                        chat_history.append({"role": "model", "parts": [msg.content]})
                
                # Tạo chat session với Gemini
                chat = model.start_chat(history=chat_history)
                
                # Gửi tin nhắn với system prompt
                try:
                    # Thêm hướng dẫn về việc phân tích ngữ cảnh vào system prompt
                    context_aware_prompt = system_prompt + """
                    
HƯỚNG DẪN BỔ SUNG VỀ PHÂN TÍCH NGỮ CẢNH:
- Hãy phân tích toàn bộ cuộc trò chuyện từ đầu đến hiện tại để nắm rõ ngữ cảnh
- Khi người dùng hỏi câu ngắn hoặc không rõ ràng, hãy dựa vào các tin nhắn trước đó để hiểu ý định
- Nếu người dùng đề cập đến "cái đó", "việc này", "điều đó", hãy tìm trong lịch sử trò chuyện để hiểu họ đang đề cập đến điều gì
- Khi trả lời, hãy kết nối với các phần trò chuyện trước đó nếu liên quan
- Không lặp lại thông tin đã cung cấp trong các tin nhắn trước đó
                    """
                    
                    # Thử gửi với system instruction nếu API hỗ trợ
                    response = chat.send_message(
                        message_content,
                        generation_config=self.generation_config,
                        safety_settings=self.safety_settings,
                        system_instruction=context_aware_prompt
                    )
                except TypeError:
                    # Nếu API không hỗ trợ system instruction, thêm vào prompt thủ công
                    # Tạo một prompt tổng hợp bao gồm cả ngữ cảnh
                    combined_message = f"{system_prompt}\n\nLịch sử trò chuyện: {self._format_chat_history(chat_history)}\n\nUser: {message_content}"
                    response = chat.send_message(
                        combined_message,
                        generation_config=self.generation_config,
                        safety_settings=self.safety_settings
                    )
                
                # Lấy text từ phản hồi
                response_content = self.process_response(response.text)
            
            # Lưu phản hồi của AI
            ai_message = GeminiChatMessage.objects.create(
                chat_session=chat_session,
                role="assistant",
                content=response_content
            )
            
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
                    "timestamp": user_message.timestamp
                },
                "assistant_message": {
                    "id": str(ai_message.id),
                    "content": ai_message.content,
                    "timestamp": ai_message.timestamp
                }
            }
            
        except Exception as e:
            self.logger.error(f"Lỗi khi gửi tin nhắn: {str(e)}")
            return {
                "error": f"Đã xảy ra lỗi: {str(e)}"
            }
    
    def _analyze_conversation_context(self, context_messages, current_message):
        """Phân tích ngữ cảnh cuộc trò chuyện để hiểu ý định của người dùng"""
        try:
            # Nếu không có tin nhắn trước đó, trả về None
            if not context_messages:
                return None
                
            # Tạo một chuỗi chứa ngữ cảnh của cuộc trò chuyện
            context_str = ""
            for msg in context_messages[-5:]:  # Chỉ lấy 5 tin nhắn gần nhất để giới hạn độ dài
                prefix = "User: " if msg['role'] == 'user' else "Assistant: "
                context_str += f"{prefix}{msg['content']}\n"
                
            # Thêm tin nhắn hiện tại vào cuối
            context_str += f"User: {current_message}"
            
            # Phân tích các từ đại diện (đó, này, kia, v.v.)
            references = [
                "điều đó", "việc đó", "cái đó", "thứ đó", 
                "điều này", "việc này", "cái này", "thứ này",
                "điều kia", "việc kia", "cái kia", "thứ kia",
                "đó", "này", "kia", "thế", "vậy", "họ", "nó",
                "những gì", "những điều", "những thứ"
            ]
            
            # Nếu tin nhắn hiện tại có chứa các từ đại diện, tìm trong ngữ cảnh
            for ref in references:
                if ref in current_message.lower():
                    # Có từ đại diện, trả về toàn bộ ngữ cảnh để xử lý
                    return context_str
                    
            # Kiểm tra nếu tin nhắn quá ngắn (thường là câu trả lời, câu hỏi tiếp theo)
            if len(current_message.split()) <= 5:
                return context_str
                
            # Nếu không có từ đại diện và tin nhắn đủ dài, trả về None để xử lý riêng
            return None
            
        except Exception as e:
            self.logger.error(f"Lỗi khi phân tích ngữ cảnh: {str(e)}")
            return None
            
    def _format_chat_history(self, chat_history):
        """Định dạng lại lịch sử trò chuyện để đưa vào prompt"""
        formatted_history = ""
        for msg in chat_history[-10:]:  # Chỉ lấy 10 tin nhắn gần nhất để giới hạn độ dài
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["parts"][0]
            formatted_history += f"{role}: {content}\n"
        return formatted_history
    
    def _process_database_queries(self, message_content, user):
        """Phân tích tin nhắn để xác định nếu cần truy vấn database và trả về kết quả phù hợp"""
        message_lower = message_content.lower()
        
        # PHẦN 1: TRUY VẤN VIỆC LÀM THEO MỨC LƯƠNG
        # Truy vấn về việc làm lương cao nhất
        salary_high_keywords = [
            "việc làm lương cao", "lương cao nhất", "mức lương cao nhất", 
            "công việc trả lương cao", "việc trả lương cao", "lương cao",
            "việc lương cao", "việc làm trả nhiều nhất", "trả lương nhiều nhất"
        ]
        if any(keyword in message_lower for keyword in salary_high_keywords):
            return self.get_highest_paying_jobs(limit=5)
        
        # PHẦN 2: TRUY VẤN VIỆC LÀM THEO THỜI GIAN
        # Truy vấn về việc làm mới nhất
        recent_job_keywords = [
            "việc làm mới", "công việc mới", "tin tuyển dụng mới", "bài đăng mới",
            "việc làm mới nhất", "việc làm gần đây", "công việc gần đây",
            "việc mới đăng", "tuyển dụng mới đăng", "mới đăng tuyển"
        ]
        if any(keyword in message_lower for keyword in recent_job_keywords):
            return self.get_most_recent_jobs(limit=5)
        
        # PHẦN 3: TRUY VẤN VIỆC LÀM THEO VỊ TRÍ CÔNG VIỆC
        # Sử dụng regex để nhận dạng câu hỏi về mức lương của vị trí công việc
        position_salary_patterns = [
            r"lương (của |cho |về |)(.*?) (là |khoảng |dao động |vào |)(bao nhiêu|thế nào|như thế nào|ra sao|nhiêu)",
            r"(.*?) (có |)(lương|mức lương) (là |vào |)(bao nhiêu|thế nào|khoảng bao nhiêu|khoảng|dao động|nhiêu)",
            r"mức lương (của |cho |)(.*?) (là |)(bao nhiêu|thế nào|như thế nào|ra sao)",
            r"(.*?) (lương|thu nhập) (khoảng |dao động |)(bao nhiêu|như thế nào|ra sao)"
        ]
        
        for pattern in position_salary_patterns:
            match = re.search(pattern, message_lower)
            if match:
                position_name = match.group(2) if len(match.groups()) > 1 and match.group(2) else match.group(1)
                # Bỏ qua các từ không liên quan
                ignore_words = ["một", "công việc", "nghề", "vị trí", "làm"]
                if position_name in ignore_words:
                    continue
                    
                # Tìm kiếm công việc có vị trí tương tự
                return self.search_job_posts(
                    query=position_name,
                    city=None,
                    experience=None,
                    position_id=None,
                    limit=5
                )
        
        # PHẦN 4: TRUY VẤN TÌM KIẾM VIỆC LÀM TỔNG HỢP
        # Nhận dạng các cụm từ tìm kiếm việc làm
        search_patterns = [
            r"tìm (việc|công việc|việc làm) (.*?)(ở|tại|trong|với|có) (.*?)",
            r"tìm (việc|công việc|việc làm) (.*?)",
            r"tìm kiếm (việc|công việc|việc làm) (.*?)",
            r"có (việc|việc làm|công việc) (.*?) (không|nào|ở|tại)",
            r"có (việc|việc làm|công việc) (.*?) (nào|không)",
            r"(việc|việc làm|công việc) (.*?) (ở|tại) (.*?)",
            r"muốn (làm|tìm) (việc|công việc) (.*?)",
            r"(tôi |)cần (tìm |)(việc|việc làm|công việc) (.*?)",
            r"(xem|cho xem|hiển thị) (việc|việc làm|công việc) (.*?)",
            r"(tìm |)(việc|công việc|việc làm|cơ hội) (về|liên quan|liên quan đến|với) (.*?)",
            r"(tìm |)(việc|công việc|việc làm|cơ hội) (cho người|cho|dành cho) (.*?)"
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, message_lower)
            if match:
                query_parts = []
                
                # Lấy thông tin tìm kiếm từ các nhóm match
                for group in match.groups():
                    if group and group not in ["việc", "công việc", "việc làm", "tìm", "kiếm", "có", "không", "nào", "ở", "tại", "trong", "với", "có", "làm", "muốn", "cần", "tôi", "xem", "cho xem", "hiển thị", "về", "liên quan", "liên quan đến", "cho", "cho người", "dành cho", "cơ hội"]:
                        query_parts.append(group)
                
                # Xác định thành phố
                city = None
                cities = ["hà nội", "hồ chí minh", "đà nẵng", "cần thơ", "hải phòng", "nha trang", "huế", "vũng tàu", "quảng ninh", "bình dương"]
                for c in cities:
                    if c in message_lower:
                        city = c.title()
                        break
                
                # Xác định kinh nghiệm
                experience = None
                experience_patterns = [
                    r"(\d+)[-\s](\d+) năm",
                    r"(\d+) năm",
                    r"không yêu cầu kinh nghiệm",
                    r"không cần kinh nghiệm",
                    r"chưa có kinh nghiệm",
                    r"mới ra trường"
                ]
                
                for exp_pattern in experience_patterns:
                    exp_match = re.search(exp_pattern, message_lower)
                    if exp_match:
                        experience = exp_match.group(0)
                        break
                
                # Nếu có thông tin tìm kiếm
                if query_parts:
                    query = " ".join(query_parts)
                    return self.search_job_posts(
                        query=query,
                        city=city,
                        experience=experience,
                        position_id=None
                    )
        
        # PHẦN 5: TÌM KIẾM THEO VỊ TRÍ ĐỊA LÝ
        # Tìm kiếm việc làm theo thành phố
        city_job_patterns = [
            r"việc làm (ở|tại) (.*?)(có|không| |$)",
            r"công việc (ở|tại) (.*?)(có|không| |$)",
            r"tuyển dụng (ở|tại) (.*?)(có|không| |$)",
            r"(.*?) đang tuyển (những |các |)gì",
            r"tìm việc (ở|tại) (.*?)"
        ]
        
        for pattern in city_job_patterns:
            match = re.search(pattern, message_lower)
            if match:
                city = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                # Kiểm tra xem đây có phải là tên thành phố không
                cities = ["hà nội", "hồ chí minh", "đà nẵng", "cần thơ", "hải phòng", "nha trang", "huế", "vũng tàu", "quảng ninh", "bình dương"]
                if any(c in city.lower() for c in cities):
                    return self.search_job_posts(
                        query="",
                        city=city,
                        experience=None,
                        position_id=None
                    )
        
        # PHẦN 6: TRUY VẤN THỐNG KÊ HỆ THỐNG
        # Truy vấn thống kê hệ thống
        stats_keywords = [
            "thống kê", "số liệu", "báo cáo hệ thống", "tổng quan", 
            "dữ liệu thống kê", "bao nhiêu việc làm", "bao nhiêu công việc",
            "có bao nhiêu", "tổng số", "thông tin tổng quan"
        ]
        if any(keyword in message_lower for keyword in stats_keywords):
            return self.get_stats_data()
        
        # PHẦN 7: GỢI Ý VIỆC LÀM
        # Truy vấn gợi ý việc làm
        recommendation_keywords = [
            "gợi ý việc làm", "công việc phù hợp", "việc làm phù hợp", 
            "công việc dành cho tôi", "việc làm cho tôi", "công việc thích hợp",
            "gợi ý cho tôi", "đề xuất việc làm", "công việc phù hợp với tôi",
            "gợi ý", "phù hợp với tôi", "công việc nào phù hợp", "việc nào phù hợp"
        ]
        if any(keyword in message_lower for keyword in recommendation_keywords):
            return self.get_job_recommendation(user)
        
        # PHẦN 8: TÌM KIẾM THEO NGÀNH NGHỀ/LĨNH VỰC
        industry_job_patterns = [
            r"việc làm (ngành|lĩnh vực) (.*?)(có|không| |$)",
            r"công việc (ngành|lĩnh vực) (.*?)(có|không| |$)",
            r"tuyển dụng (ngành|lĩnh vực) (.*?)(có|không| |$)",
            r"(ngành|lĩnh vực) (.*?) (đang |)tuyển (dụng|gì|không|những gì)",
            r"(ngành|lĩnh vực) (.*?) (có |)(việc|công việc|cơ hội) (gì|nào|làm)"
        ]
        
        for pattern in industry_job_patterns:
            match = re.search(pattern, message_lower)
            if match:
                industry = match.group(2)
                return self.search_job_posts(
                    query=industry,
                    city=None,
                    experience=None,
                    position_id=None
                )
                
        # PHẦN 9: TÌM KIẾM VIỆC LÀM THEO KỸ NĂNG LẬP TRÌNH/CÔNG NGHỆ
        # Phát hiện kỹ năng lập trình và công nghệ trong tin nhắn
        programming_keywords = [
            "lập trình", "developer", "coder", "programmer", "development", "coding", 
            "software", "phần mềm", "code", "web", "app", "mobile", "framework",
            "fullstack", "backend", "frontend", "devops", "data", "AI", "machine learning"
        ]
        
        programming_languages = [
            "python", "java", "javascript", "typescript", "php", "c#", "c++", "ruby", 
            "swift", "kotlin", "go", "golang", "rust", "scala", "perl", "r", "dart"
        ]
        
        frameworks = [
            "django", "flask", "fastapi", "spring", "springboot", "laravel", "symfony",
            "react", "vue", "angular", "node", "express", "nestjs", "rails", "asp.net",
            ".net", "dotnet", "flutter", "android", "ios", "xamarin", "react native"
        ]
        
        databases = [
            "sql", "mysql", "postgresql", "mongodb", "nosql", "firebase", "oracle",
            "sqlite", "mariadb", "cassandra", "redis", "elasticsearch", "cơ sở dữ liệu"
        ]
        
        # Kết hợp tất cả các từ khóa công nghệ
        tech_keywords = programming_languages + frameworks + databases
        
        # Tìm kiếm các từ khóa công nghệ trong tin nhắn
        found_tech_keywords = []
        
        # Kiểm tra các từ khóa lập trình chung
        if any(keyword in message_lower for keyword in programming_keywords):
            # Nếu có từ khóa lập trình chung, tìm các từ khóa công nghệ cụ thể
            for keyword in tech_keywords:
                if keyword in message_lower:
                    found_tech_keywords.append(keyword)
        else:
            # Kiểm tra trực tiếp các từ khóa công nghệ cụ thể
            for keyword in tech_keywords:
                if keyword in message_lower:
                    found_tech_keywords.append(keyword)
        
        # Nếu tìm thấy từ khóa công nghệ
        if found_tech_keywords:
            # Tạo một truy vấn tìm kiếm với các từ khóa công nghệ
            tech_query = " ".join(found_tech_keywords)
            
            # Kiểm tra xem có từ kèm theo "việc làm", "công việc", "tìm", "tuyển dụng"
            job_related = any(term in message_lower for term in ["việc làm", "công việc", "tìm", "tuyển dụng", "tuyển", "ứng tuyển", "nghề", "job"])
            
            # Nếu không có từ liên quan đến việc làm, thêm từ "việc làm" vào truy vấn
            if not job_related:
                tech_query = tech_query + " việc làm"
                
            return self.search_job_posts(
                query=tech_query,
                city=None,
                experience=None,
                position_id=None,
                limit=8  # Tăng giới hạn kết quả cho tìm kiếm công nghệ
            )
        
        # Không tìm thấy truy vấn database phù hợp
        return None 

    def process_response(self, response_text, database_data=None):
        """Xử lý phản hồi từ Gemini và kết hợp với dữ liệu từ database nếu có"""
        if database_data:
            # Cung cấp định dạng rõ ràng cho dữ liệu từ database
            return f"{database_data}\n\n*Dữ liệu trên được cung cấp từ cơ sở dữ liệu của hệ thống.*"
        
        # Nếu không có dữ liệu từ database, trả về phản hồi gốc
        # Thêm thông báo để người dùng biết đây là dữ liệu từ internet
        if "trả lời dựa trên" not in response_text.lower() and "thông tin từ internet" not in response_text.lower():
            response_text += "\n\n*Dữ liệu trên được cung cấp từ kiến thức chung của AI.*"
        
        return response_text 

    def _initialize_generative_model(self):
        """Khởi tạo model Gemini"""
        try:
            # Lấy API key từ settings
            api_key = settings.GEMINI_API_KEY
            
            # Khởi tạo genai với API key
            genai.configure(api_key=api_key)
            
            # Trả về model Gemini Pro
            return genai.GenerativeModel('gemini-1.5-pro')
        except Exception as e:
            self.logger.error(f"Lỗi khởi tạo model Gemini: {str(e)}")
            raise e 

    def generate_chat_title(self, message_content):
        """Tạo tiêu đề tối ưu từ nội dung tin nhắn đầu tiên bằng Gemini API"""
        try:
            # Giới hạn độ dài tin nhắn để tối ưu API call
            content_for_title = message_content[:500] if len(message_content) > 500 else message_content
            
            # Khởi tạo model
            model = self._initialize_generative_model()
            
            # Tạo prompt để sinh tiêu đề
            prompt = f"""
            Dưới đây là nội dung tin nhắn đầu tiên của một cuộc hội thoại:
            
            "{content_for_title}"
            
            Hãy tạo một tiêu đề ngắn gọn (tối đa 6-8 từ) mô tả chính xác chủ đề của cuộc hội thoại. 
            Tiêu đề chỉ nên bao gồm nội dung chính, không có dấu ngoặc kép, không có từ "Tiêu đề:" hoặc bất kỳ định dạng nào khác.
            """
            
            # Gọi API để tạo tiêu đề
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 30,
                }
            )
            
            # Lấy tiêu đề từ kết quả
            title = response.text.strip()
            
            # Đảm bảo tiêu đề không quá dài
            if len(title) > 50:
                words = title.split()
                if len(words) > 8:
                    title = ' '.join(words[:8])
                else:
                    title = title[:50]
            
            # Nếu không tạo được tiêu đề, sử dụng phương án dự phòng
            if not title:
                # Phương án dự phòng: sử dụng một đoạn từ tin nhắn
                words = message_content.split()
                if len(words) <= 8:
                    title = message_content[:50]
                else:
                    title = ' '.join(words[:8])
                    
                # Thêm dấu '...' nếu tin nhắn bị cắt
                if len(message_content) > len(title):
                    title += '...'
            
            return title
        except Exception as e:
            self.logger.error(f"Lỗi khi tạo tiêu đề: {str(e)}")
            
            # Phương án dự phòng khi có lỗi: sử dụng đoạn đầu của tin nhắn
            if len(message_content) <= 50:
                return message_content
            else:
                words = message_content.split()
                if len(words) <= 8:
                    return message_content[:50] + '...'
                else:
                    return ' '.join(words[:8]) + '...' 