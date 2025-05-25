import json
import psycopg2
import random
from datetime import datetime, date
import requests

# response = requests.get("https://provinces.open-api.vn/api/?depth=3")

# with open("tinh_thanh.json", "w", encoding="utf-8") as f:
#     json.dump(response.json(), f, ensure_ascii=False, indent=4)

with open("tinh_thanh.json", "r", encoding="utf-8") as f:
    tinh_thanh_data = json.load(f)

other_provinces = [province for province in tinh_thanh_data 
                  if province['name'] != 'Thành phố Hồ Chí Minh']

def get_random_address():
    province = random.choice(other_provinces)
    if not province['districts']:
        return None
    district = random.choice(province['districts'])
    if not district['wards']:
        return None
    ward = random.choice(district['wards'])
    detail_address = f"{ward['name']}, {district['name']}, {province['name']}"
    return {
        'city': province['name'],
        'district': district['name'],
        'detail_address': detail_address
    }

conn = psycopg2.connect(
    host="",
    database="",
    user="",
    password="",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM posts WHERE city = 'Thành phố Hồ Chí Minh'")
hcm_posts = cursor.fetchall()

print(f"Tìm thấy {len(hcm_posts)} posts ở TP.HCM")

cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'posts' ORDER BY ordinal_position")
column_names = [row[0] for row in cursor.fetchall()]
print(f"Các cột: {column_names}")

new_posts = []
created_count = 0

for post in hcm_posts:
    # Lấy địa chỉ ngẫu nhiên
    random_address = get_random_address()
    if not random_address:
        continue
    
    post_dict = dict(zip(column_names, post))
    
    # Loại bỏ id để database tự generate
    post_dict.pop('id', None)
    
    # Cập nhật địa chỉ mới
    post_dict['city'] = random_address['city']
    post_dict['district'] = random_address['district'] 
    post_dict['detail_address'] = random_address['detail_address']
    
    # Cập nhật thời gian tạo và sửa đổi
    post_dict['created_at'] = datetime.now()
    post_dict['modified_at'] = datetime.now()
    
    new_posts.append(post_dict)
    created_count += 1

print(f"Đã tạo {created_count} posts mới với địa chỉ ngẫu nhiên")

# Insert posts mới vào database
if new_posts:
    # Tạo câu SQL insert
    columns_to_insert = [col for col in column_names if col != 'id']
    placeholders = ', '.join(['%s'] * len(columns_to_insert))
    columns_str = ', '.join(columns_to_insert)
    
    insert_sql = f"INSERT INTO posts ({columns_str}) VALUES ({placeholders})"
    
    # Chuẩn bị dữ liệu để insert
    insert_data = []
    for post in new_posts:
        row_data = [post[col] for col in columns_to_insert]
        insert_data.append(row_data)
    
    # Thực hiện insert
    try:
        cursor.executemany(insert_sql, insert_data)
        conn.commit()
        print(f"Đã insert thành công {len(insert_data)} posts mới!")
        
        # Kiểm tra lại số lượng posts
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_posts = cursor.fetchone()[0]
        print(f"Tổng số posts hiện tại: {total_posts}")
        
        # Hiển thị một vài ví dụ posts mới
        cursor.execute("SELECT city, district, detail_address FROM posts WHERE city != 'Thành phố Hồ Chí Minh' LIMIT 5")
        sample_new_posts = cursor.fetchall()
        print("\nMột vài ví dụ posts mới:")
        for i, post in enumerate(sample_new_posts, 1):
            print(f"{i}. {post[0]} - {post[1]} - {post[2]}")
            
    except Exception as e:
        print(f"Lỗi khi insert: {e}")
        conn.rollback()

conn.close()
print("Hoàn thành!") 