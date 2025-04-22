import json
import os
import django
import sys
from django.utils import timezone
from datetime import timedelta

# Thêm đường dẫn của project vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cài đặt Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuyendung.settings')
django.setup()

from enterprises.models import FieldEntity, PositionEntity, EnterpriseEntity,PostEntity
from accounts.models import UserAccount, Role, UserRole
from profiles.models import UserInfo
from transactions.models import PremiumPackage
# from posts.models import PostEntity

def import_fields_from_json(file_path):
    """
    Import dữ liệu lĩnh vực từ file JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total = 0
        success = 0
        failed = 0
        errors = []
        
        for item in data:
            total += 1
            try:
                FieldEntity.objects.get_or_create(
                    code=item['code'],
                    defaults={
                        'name': item['name'],
                        'status': item.get('status', 'active')
                    }
                )
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"Lỗi khi import lĩnh vực {item.get('name', '')}: {str(e)}")
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'errors': errors
        }
    except Exception as e:
        return {
            'error': f"Lỗi khi đọc file JSON: {str(e)}"
        }

def import_positions_from_json(file_path):
    """
    Import dữ liệu vị trí từ file JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total = 0
        success = 0
        failed = 0
        errors = []
        
        for item in data:
            total += 1
            try:
                field = FieldEntity.objects.get(code=item['field_code'])
                PositionEntity.objects.get_or_create(
                    code=item['code'],
                    defaults={
                        'name': item['name'],
                        'field': field,
                        'status': item.get('status', 'active')
                    }
                )
                success += 1
            except FieldEntity.DoesNotExist:
                failed += 1
                errors.append(f"Không tìm thấy lĩnh vực với code {item.get('field_code', '')}")
            except Exception as e:
                failed += 1
                errors.append(f"Lỗi khi import vị trí {item.get('name', '')}: {str(e)}")
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'errors': errors
        }
    except Exception as e:
        return {
            'error': f"Lỗi khi đọc file JSON: {str(e)}"
        }

def import_enterprises_from_json(file_path):
    """
    Import enterprises and recruiters from JSON file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': ['File not found']
        }
    except json.JSONDecodeError:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': ['Invalid JSON format']
        }

    results = {
        'total': len(data),
        'success': 0,
        'failed': 0,
        'errors': []
    }

    for item in data:
        try:
            # Tạo tài khoản người tuyển dụng
            user, created = UserAccount.objects.get_or_create(
                username=item['username'],
                defaults={
                    'email': item['email'],
                    'is_active': item['is_active'],
                    'is_staff': item['is_staff'],
                    'is_superuser': item['is_superuser']
                }
            )

            if created:
                user.set_password(item['password'])
                user.save()

                # Tạo thông tin cá nhân
                UserInfo.objects.create(
                    user=user,
                    fullname=item['full_name'],
                    gender='other'
                )

                # Gán vai trò employer
                employer_role = Role.objects.get(name='employer')
                UserRole.objects.create(user=user, role=employer_role)

            # Tạo hoặc cập nhật doanh nghiệp
            enterprise, created = EnterpriseEntity.objects.update_or_create(
                company_name=item['enterprise']['company_name'],
                defaults={
                    'email_company': item['enterprise']['email_company'],
                    'field_of_activity': item['enterprise']['field_of_activity'],
                    'address': item['enterprise']['address'],
                    'description': item['enterprise']['description'],
                    'phone_number': item['enterprise']['phone_number'],
                    'scale': item['enterprise']['scale'],
                    'tax': item['enterprise']['tax'],
                    'city': item['enterprise']['city'],
                    'is_active': item['enterprise']['is_active'],
                    'business_certificate_url': item['enterprise'].get('business_certificate_url', ''),
                    'business_certificate_public_id': item['enterprise'].get('business_certificate_public_id', ''),
                    'logo_url': item['enterprise'].get('logo_url', ''),
                    'logo_public_id': item['enterprise'].get('logo_public_id', ''),
                    'background_image_url': item['enterprise'].get('background_image_url', ''),
                    'background_image_public_id': item['enterprise'].get('background_image_public_id', ''),
                    'link_web_site': item['enterprise'].get('link_web_site', ''),
                    'user': user
                }
            )

            results['success'] += 1

        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"Error importing {item.get('enterprise', {}).get('company_name', 'Unknown')}: {str(e)}")

    return results

def import_posts_from_json(file_path):
    """
    Import posts from JSON file
    """
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            posts_data = json.load(f)
            results['total'] = len(posts_data)

            for post_data in posts_data:
                try:
                    # Tìm enterprise theo tên
                    enterprise = EnterpriseEntity.objects.get(company_name=post_data['enterprise_name'])
                    
                    # Tìm position theo tên
                    position = PositionEntity.objects.get(name=post_data['position'])

                    # Tạo post mới
                    PostEntity.objects.create(
                        title=post_data['title'],
                        deadline=post_data['deadline'],
                        district=post_data['district'],
                        experience=post_data['experience'],
                        enterprise=enterprise,
                        position=position,
                        interest=post_data['interest'],
                        level=post_data['level'],
                        quantity=post_data['quantity'],
                        required=post_data['required'],
                        salary_range=post_data['salary_range'],
                        time_working=post_data['time_working'],
                        type_working=post_data['type_working'],
                        city=post_data['city'],
                        description=post_data['description'],
                        detail_address=post_data['detail_address']
                    )
                    results['success'] += 1
                except EnterpriseEntity.DoesNotExist:
                    results['failed'] += 1
                    results['errors'].append(f"Enterprise not found: {post_data['enterprise_name']}")
                except PositionEntity.DoesNotExist:
                    results['failed'] += 1
                    results['errors'].append(f"Position not found: {post_data['position']}")
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Error importing post {post_data.get('title', 'Unknown')}: {str(e)}")

    except FileNotFoundError:
        results['errors'].append(f"File not found: {file_path}")
    except json.JSONDecodeError:
        results['errors'].append(f"Invalid JSON format in file: {file_path}")
    except Exception as e:
        results['errors'].append(f"Unexpected error: {str(e)}")

    return results

def import_premium_packages_from_json(file_path):
    """
    Nhập các gói Premium từ file JSON
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        total = 0
        success = 0
        failed = 0
        errors = []
        
        for item in data:
            total += 1
            try:
                # Tạo hoặc cập nhật gói Premium với tất cả các trường
                package, created = PremiumPackage.objects.update_or_create(
                    name=item['name'],
                    defaults={
                        'description': item['description'],
                        'price': item['price'],
                        'duration_days': item['duration_days'],
                        'features': item['features'],
                        'is_active': item.get('is_active', True),
                        'name_display': item.get('name_display', ''),
                        'max_job_posts': item.get('max_job_posts', 3),
                        'max_cv_views_per_day': item.get('max_cv_views_per_day', 10),
                        'can_view_candidate_contacts': item.get('can_view_candidate_contacts', False),
                        'can_feature_posts': item.get('can_feature_posts', False),
                        'can_access_analytics': item.get('can_access_analytics', False),
                        'can_chat_with_employers': item.get('can_chat_with_employers', False),
                        'priority_in_search': item.get('priority_in_search', 0),
                        'daily_job_application_limit': item.get('daily_job_application_limit', 5),
                        'can_view_job_applications': item.get('can_view_job_applications', False),
                        'can_chat_with_candidates': item.get('can_chat_with_candidates', False),
                        'can_view_submitted_cvs': item.get('can_view_submitted_cvs', False)
                    }
                )
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"Lỗi khi import gói Premium {item.get('name', '')}: {str(e)}")
        
        return {
            'total': total,
            'success': success,
            'failed': failed,
            'errors': errors
        }
    except FileNotFoundError:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': ['File not found']
        }
    except json.JSONDecodeError:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': ['Invalid JSON format']
        }

if __name__ == '__main__':
    # # Import fields
    # fields_result = import_fields_from_json('data/fields.json')
    # print("\nImport Fields Result:")
    # print(f"Total: {fields_result['total']}")
    # print(f"Success: {fields_result['success']}")
    # print(f"Failed: {fields_result['failed']}")
    # if fields_result['errors']:
    #     print("Errors:")
    #     for error in fields_result['errors']:
    #         print(f"- {error}")

    # # Import positions
    # positions_result = import_positions_from_json('data/positions.json')
    # print("\nImport Positions Result:")
    # print(f"Total: {positions_result['total']}")
    # print(f"Success: {positions_result['success']}")
    # print(f"Failed: {positions_result['failed']}")
    # if positions_result['errors']:
    #     print("Errors:")
    #     for error in positions_result['errors']:
    #         print(f"- {error}")

    # Import enterprises and recruiters
    # enterprises_result = import_enterprises_from_json('data/enterprises.json')
    # print("\nImport Enterprises and Recruiters Result:")
    # print(f"Total: {enterprises_result['total']}")
    # print(f"Success: {enterprises_result['success']}")
    # print(f"Failed: {enterprises_result['failed']}")
    # if enterprises_result['errors']:
    #     print("Errors:")
    #     for error in enterprises_result['errors']:
    #         print(f"- {error}")

    # # Import posts
    # posts_result = import_posts_from_json('data/posts.json')
    # print("\nImport Posts Result:")
    # print(f"Total: {posts_result['total']}")
    # print(f"Success: {posts_result['success']}")
    # print(f"Failed: {posts_result['failed']}")
    # if posts_result['errors']:
    #     print("Errors:")
    #     for error in posts_result['errors']:
    #         print(f"- {error}")
    
    # Import premium packages
    premium_packages_result = import_premium_packages_from_json('data/premium_packages.json')
    print("\nImport Premium Packages Result:")
    print(f"Total: {premium_packages_result['total']}")
    print(f"Success: {premium_packages_result['success']}")
    print(f"Failed: {premium_packages_result['failed']}")
    if premium_packages_result['errors']:
        print("Errors:")
        for error in premium_packages_result['errors']:
            print(f"- {error}") 