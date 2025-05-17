import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuyendung_app.settings')
django.setup()

from enterprises.models import PostEntity

def fix_posts():
    # Lấy tất cả các bài đăng đã bị đánh dấu is_remove_by_admin=True
    posts_to_fix = PostEntity.objects.filter(is_remove_by_admin=True)
    count = posts_to_fix.count()
    print(f'Sửa {count} bài đăng')
    
    # Sửa lại thành is_remove_by_admin=False
    posts_to_fix.update(is_remove_by_admin=False)
    print('Đã sửa xong')

if __name__ == '__main__':
    fix_posts() 