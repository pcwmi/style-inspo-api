#!/usr/bin/env python3
"""
Diagnostic script to test product extraction
"""
import requests
import json
import sys

# Test URL - replace with the actual URL you're testing
TEST_URL = sys.argv[1] if len(sys.argv) > 1 else "https://frame-store.com/en-fr/collections/most-wanted-women/products/the-cashmere-fleck-cardi-silver"
API_URL = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
USER_ID = sys.argv[3] if len(sys.argv) > 3 else "peichin"

print("=" * 80)
print("PRODUCT EXTRACTION DIAGNOSTIC")
print("=" * 80)
print(f"Test URL: {TEST_URL}")
print(f"API URL: {API_URL}")
print(f"User ID: {USER_ID}")
print("=" * 80)

# Test 1: Direct API call
print("\n1. Testing API endpoint directly...")
try:
    response = requests.post(
        f"{API_URL}/api/consider-buying/extract-url?user_id={USER_ID}",
        json={"url": TEST_URL},
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    
    print(f"   Status Code: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        if data.get('success'):
            print("   ✅ Extraction succeeded")
            print(f"   Image URL: {data.get('data', {}).get('image_url', 'N/A')}")
            print(f"   Title: {data.get('data', {}).get('title', 'N/A')}")
            print(f"   Brand: {data.get('data', {}).get('brand', 'N/A')}")
            print(f"   Price: {data.get('data', {}).get('price', 'N/A')}")
        else:
            print("   ❌ Extraction failed")
            print(f"   Error: {data.get('error', 'No error message')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        
except requests.exceptions.RequestException as e:
    print(f"   ❌ Network Error: {e}")
except Exception as e:
    print(f"   ❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test ProductExtractor directly (if running locally)
if API_URL == "http://localhost:8000":
    print("\n2. Testing ProductExtractor directly...")
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        
        from services.product_extractor import ProductExtractor
        
        extractor = ProductExtractor()
        success, data, error = extractor.extract_from_url(TEST_URL)
        
        print(f"   Success: {success}")
        if success:
            print(f"   ✅ Direct extraction succeeded")
            print(f"   Image URL: {data.get('image_url', 'N/A')}")
            print(f"   Title: {data.get('title', 'N/A')}")
            print(f"   Brand: {data.get('brand', 'N/A')}")
            print(f"   Price: {data.get('price', 'N/A')}")
        else:
            print(f"   ❌ Direct extraction failed")
            print(f"   Error: {error}")
            
    except Exception as e:
        print(f"   ⚠️  Could not test directly: {e}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

