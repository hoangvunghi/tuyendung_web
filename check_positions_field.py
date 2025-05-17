import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuyendung.settings')
django.setup()

from enterprises.models import PositionEntity, FieldEntity

def check_positions_by_field():
    print(f'Tổng số vị trí: {PositionEntity.objects.count()}')
    print(f'Số vị trí active: {PositionEntity.objects.filter(status="active").count()}')
    
    print('\nSố vị trí theo từng lĩnh vực:')
    for field in FieldEntity.objects.all():
        positions_count = PositionEntity.objects.filter(field=field, status="active").count()
        print(f'- {field.name} (ID: {field.id}): {positions_count} vị trí active')

if __name__ == '__main__':
    check_positions_by_field() 