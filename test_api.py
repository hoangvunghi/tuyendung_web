import requests
import json

def test_positions_api():
    url = "http://localhost:8000/api/positions/"
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("API trả về thành công!")
            print(f"Số lượng vị trí: {len(data['results']) if 'results' in data else 'N/A'}")
            print("Dữ liệu mẫu:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
        else:
            print(f"Lỗi: {response.text}")
    except Exception as e:
        print(f"Lỗi khi gọi API: {str(e)}")

if __name__ == "__main__":
    test_positions_api() 