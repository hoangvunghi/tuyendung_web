import requests
import json

def test_positions_by_field_api():
    # Thử với field ID = 1 (CNTT - có 32 vị trí)
    field_id = 1
    url = f"http://localhost:8000/api/positions/field/{field_id}/"
    
    # Thử không dùng page_size (mặc định là 10)
    print(f"\n--- TEST 1: Lấy vị trí của lĩnh vực {field_id} với page_size mặc định ---")
    response = requests.get(url)
    test_response(response)
    
    # Thử với page_size = 50
    print(f"\n--- TEST 2: Lấy vị trí của lĩnh vực {field_id} với page_size=50 ---")
    response = requests.get(url + "?page_size=50")
    test_response(response)
    
def test_response(response):
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"Message: {data.get('message', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")
        
        if 'data' in data:
            results = data['data'].get('results', [])
            total = data['data'].get('total', 0)
            page_size = data['data'].get('page_size', 0)
            
            print(f"Tổng số vị trí: {total}")
            print(f"Kích thước trang: {page_size}")
            print(f"Số vị trí trả về: {len(results)}")
            
            if len(results) > 0:
                print("\nVí dụ một số vị trí:")
                for pos in results[:3]:
                    print(f"- ID: {pos.get('id')}, Tên: {pos.get('name')}")
        else:
            print("Không có dữ liệu trả về")
    else:
        print(f"Lỗi: {response.text}")

if __name__ == "__main__":
    test_positions_by_field_api() 