import json
import psycopg2
import random
from datetime import datetime

with open("tinh_thanh.json", "r", encoding="utf-8") as f:
    tinh_thanh_data = json.load(f)
other_provinces = [province for province in tinh_thanh_data 
                  if province['name'] != 'Thành phố Hà Nội']

print(f"Có {len(other_provinces)} tỉnh thành khác ngoài Hà Nội")

def get_random_address():
    """Lấy địa chỉ ngẫu nhiên từ các tỉnh thành"""
    # Chọn ngẫu nhiên một tỉnh
    province = random.choice(other_provinces)
    
    # Chọn ngẫu nhiên một huyện
    if not province['districts']:
        return None
    district = random.choice(province['districts'])
    
    # Chọn ngẫu nhiên một xã
    if not district['wards']:
        return None
    ward = random.choice(district['wards'])
    
    # Tạo address = số nhà + xã + huyện + tỉnh
    house_number = random.randint(1, 999)
    address = f"{house_number} {ward['name']}, {district['name']}, {province['name']}"
    
    return {
        'city': province['name'],
        'address': address
    }

# Kết nối database
conn = psycopg2.connect(
    host="",
    database="",
    user="",
    password="",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'enterprises_enterpriseentity'")
columns = cursor.fetchall()
print("\nCấu trúc bảng enterprises_enterpriseentity:")
for col in columns:
    print(f"{col[0]}: {col[1]}")
cursor.execute("SELECT id, company_name, city, address FROM enterprises_enterpriseentity WHERE city != 'Thành phố Hà Nội'")
enterprises = cursor.fetchall()

print(f"\nTìm thấy {len(enterprises)} enterprises có city khác Hà Nội")

if enterprises:
    print("\nMột vài ví dụ enterprises hiện tại:")
    for i, ent in enumerate(enterprises[:3], 1):
        print(f"{i}. ID: {ent[0]} - {ent[1]} - {ent[2]} - {ent[3]}")

# Cập nhật địa chỉ cho từng enterprise
updated_count = 0

for enterprise in enterprises:
    enterprise_id = enterprise[0]
    company_name = enterprise[1]
    random_address = get_random_address()
    if not random_address:
        continue
    
    try:
        update_sql = """
        UPDATE enterprises_enterpriseentity 
        SET city = %s, address = %s, modified_at = %s 
        WHERE id = %s
        """
        
        cursor.execute(update_sql, (
            random_address['city'],
            random_address['address'], 
            datetime.now(),
            enterprise_id
        ))
        
        updated_count += 1
        
        if updated_count <= 5:  
            print(f"Cập nhật {company_name}: {random_address['city']} - {random_address['address']}")
            
    except Exception as e:
        print(f"Lỗi khi cập nhật enterprise ID {enterprise_id}: {e}")
        continue

# Commit các thay đổi
try:
    conn.commit()
    print(f"\nĐã cập nhật thành công {updated_count} enterprises!")
    
    # Kiểm tra lại kết quả
    cursor.execute("SELECT COUNT(*) FROM enterprises_enterpriseentity")
    total_enterprises = cursor.fetchone()[0]
    print(f"Tổng số enterprises: {total_enterprises}")
    
    cursor.execute("SELECT COUNT(DISTINCT city) FROM enterprises_enterpriseentity")
    total_cities = cursor.fetchone()[0]
    print(f"Số lượng thành phố khác nhau: {total_cities}")
    
    # Hiển thị một vài ví dụ sau khi cập nhật
    cursor.execute("SELECT company_name, city, address FROM enterprises_enterpriseentity WHERE city != 'Thành phố Hà Nội' LIMIT 5")
    sample_enterprises = cursor.fetchall()
    print("\nMột vài ví dụ enterprises sau khi cập nhật:")
    for i, ent in enumerate(sample_enterprises, 1):
        print(f"{i}. {ent[0]} - {ent[1]} - {ent[2]}")
        
    # Thống kê theo thành phố
    cursor.execute("SELECT city, COUNT(*) FROM enterprises_enterpriseentity GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10")
    city_stats = cursor.fetchall()
    print("\nThống kê top 10 thành phố có nhiều enterprises nhất:")
    for city, count in city_stats:
        print(f"{city}: {count} enterprises")
        
except Exception as e:
    print(f"Lỗi khi commit: {e}")
    conn.rollback()

conn.close()
print("\nHoàn thành!") 