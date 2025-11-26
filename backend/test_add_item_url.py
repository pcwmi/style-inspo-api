import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_add_item_url():
    url = "http://localhost:8000/api/consider-buying/add-item"
    
    # Data simulating what the frontend sends
    data = {
        "image_url": "https://media.thereformation.com/image/upload/f_auto,q_auto,dpr_1.0/w_800,c_scale//PRD-SFCC/1313250/MIDNIGHT/1313250.1.MIDNIGHT?_s=RAABAB0",
        "source_url": "https://www.thereformation.com/products/gale-satin-mid-rise-bias-pant/1313250MDN.html?dwvar_1313250MDN_color=MDN",
        "user_id": "peichin"
    }
    
    print(f"Testing add-item with URL: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, data=data)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Add item successful!")
            print(response.json())
        else:
            print("❌ Add item failed!")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_add_item_url()
