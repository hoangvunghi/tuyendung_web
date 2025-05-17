import requests
import json

def test_positions_by_field_api_no_pagination():
    # Thử với field ID = 1 (CNTT - có 32 vị trí)
    field_id = 1
    url = f"http://localhost:8000/api/positions/field/{field_id}/"
    
    print(f"\n--- TEST: Lấy vị trí của lĩnh vực {field_id} không phân trang ---")
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"Message: {data.get('message', 'N/A')}")
        print(f"Status: {data.get('status', 'N/A')}")
        
        # In toàn bộ cấu trúc dữ liệu để kiểm tra
        print("Cấu trúc dữ liệu response:", json.dumps(data, indent=2, ensure_ascii=False)[:200] + "...")
        
        # Kiểm tra cấu trúc và lấy kết quả
        if 'data' in data and isinstance(data['data'], list):
            results = data['data']
            print(f"Số vị trí trả về: {len(results)}")
            
            if len(results) > 0:
                print("\nVí dụ một số vị trí đầu tiên:")
                for pos in results[:3]:
                    print(f"- ID: {pos.get('id')}, Tên: {pos.get('name')}")
                    
                if len(results) > 3:
                    print("\nVí dụ một số vị trí cuối cùng:")
                    for pos in results[-3:]:
                        print(f"- ID: {pos.get('id')}, Tên: {pos.get('name')}")
        else:
            print("Dữ liệu không đúng định dạng mong đợi")
    else:
        print(f"Lỗi: {response.text}")

if __name__ == "__main__":
    test_positions_by_field_api_no_pagination() 