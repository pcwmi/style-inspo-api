from services.product_extractor import ProductExtractor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_download():
    # The URL that was extracted successfully
    image_url = "https://media.thereformation.com/image/upload/f_auto,q_auto,dpr_1.0/w_800,c_scale//PRD-SFCC/1313250/MIDNIGHT/1313250.1.MIDNIGHT?_s=RAABAB0"
    print(f"Testing download for: {image_url}")
    
    extractor = ProductExtractor()
    success, image, error = extractor.download_image(image_url)
    
    if success:
        print("✅ Download successful!")
        print(f"Image format: {image.format}")
        print(f"Image size: {image.size}")
    else:
        print("❌ Download failed!")
        print(f"Error: {error}")

if __name__ == "__main__":
    test_download()
