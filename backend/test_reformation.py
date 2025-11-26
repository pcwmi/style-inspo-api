from services.product_extractor import ProductExtractor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_reformation():
    url = "https://www.thereformation.com/products/gale-satin-mid-rise-bias-pant/1313250MDN.html?dwvar_1313250MDN_color=MDN"
    print(f"Testing extraction for: {url}")
    
    extractor = ProductExtractor()
    success, data, error = extractor.extract_from_url(url)
    
    if success:
        print("✅ Extraction successful!")
        print(data)
    else:
        print("❌ Extraction failed!")
        print(f"Error: {error}")

if __name__ == "__main__":
    test_reformation()
