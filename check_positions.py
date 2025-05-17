import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuyendung.settings')
django.setup()

from enterprises.models import PositionEntity

def check_positions():
    # Đếm số lượng vị trí
    total_positions = PositionEntity.objects.count()
    active_positions = PositionEntity.objects.filter(status='active').count()
    
    print(f"Tổng số vị trí: {total_positions}")
    print(f"Số vị trí đang hoạt động (active): {active_positions}")
    
    # Liệt kê 10 vị trí đầu tiên
    print("\nDanh sách 10 vị trí đầu tiên:")
    positions = PositionEntity.objects.all()[:10]
    for pos in positions:
        print(f"ID: {pos.id}, Tên: {pos.name}, Mã: {pos.code}, Trạng thái: {pos.status}")
    
    # Liệt kê tất cả vị trí 'active'
    print("\nDanh sách các vị trí đang hoạt động:")
    active_positions = PositionEntity.objects.filter(status='active')
    for pos in active_positions:
        print(f"ID: {pos.id}, Tên: {pos.name}, Mã: {pos.code}")

if __name__ == '__main__':
    check_positions() 