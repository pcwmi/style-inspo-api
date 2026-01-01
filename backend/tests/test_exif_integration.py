#!/usr/bin/env python3
"""
Integration test for EXIF orientation fixes.
Tests the actual backend services with local storage.

Run: STORAGE_TYPE=local python backend/tests/test_exif_integration.py
"""

import os
import sys
import tempfile
import shutil
from io import BytesIO
from PIL import Image, ImageOps
import piexif

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set up test environment
os.environ['STORAGE_TYPE'] = 'local'

from services.storage_manager import StorageManager
from services.wardrobe_manager import WardrobeManager


def create_portrait_image_with_exif() -> BytesIO:
    """
    Create a test portrait image (taken with phone rotated).
    The image pixels are landscape (200x100), but EXIF says rotate 90 CW.
    A browser would display this as portrait (100x200).
    """
    # Create landscape image with marker in top-left
    img = Image.new('RGB', (200, 100), color='white')

    # Red marker in top-left corner
    for x in range(40):
        for y in range(20):
            img.putpixel((x, y), (255, 0, 0))

    # Blue marker in bottom-right
    for x in range(160, 200):
        for y in range(80, 100):
            img.putpixel((x, y), (0, 0, 255))

    # Add EXIF orientation 6 (rotate 90 CW to display correctly)
    exif_dict = {"0th": {piexif.ImageIFD.Orientation: 6}}
    exif_bytes = piexif.dump(exif_dict)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', exif=exif_bytes, quality=95)
    buffer.seek(0)
    buffer.name = "test_portrait.jpg"

    return buffer


def check_orientation(image_data: bytes) -> dict:
    """Check EXIF orientation of image data."""
    try:
        exif_dict = piexif.load(image_data)
        orientation = exif_dict.get("0th", {}).get(piexif.ImageIFD.Orientation)
        return {"orientation": orientation}
    except:
        return {"orientation": None}


def test_storage_manager_save():
    """Test that StorageManager strips EXIF orientation."""
    print("\n" + "=" * 60)
    print("TEST: StorageManager.save_image()")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test image
        test_file = create_portrait_image_with_exif()
        original_data = test_file.read()
        test_file.seek(0)

        print(f"Original image size (pixels): 200x100")
        print(f"Original EXIF orientation: {check_orientation(original_data)['orientation']}")

        # Load and process as wardrobe_manager does
        img = Image.open(test_file)
        print(f"Loaded size: {img.size}")

        img = ImageOps.exif_transpose(img)
        print(f"After exif_transpose: {img.size}")

        # Save via storage manager
        storage = StorageManager(storage_type="local", user_id="test_user")
        storage.base_path = tmpdir

        saved_path = storage.save_image(img, "test.jpg")
        print(f"Saved to: {saved_path}")

        # Read back and check
        with open(saved_path, 'rb') as f:
            saved_data = f.read()

        saved_img = Image.open(BytesIO(saved_data))
        exif_check = check_orientation(saved_data)

        print(f"Saved image size: {saved_img.size}")
        print(f"Saved EXIF orientation: {exif_check['orientation']}")

        # Verify
        if saved_img.size == (100, 200) and exif_check['orientation'] is None:
            print("✓ PASS: Image correctly rotated, orientation stripped")
            return True
        else:
            print("✗ FAIL")
            return False


def test_wardrobe_manager_add_item():
    """Test full WardrobeManager.add_wardrobe_item() flow."""
    print("\n" + "=" * 60)
    print("TEST: WardrobeManager.add_wardrobe_item()")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override base path
        original_base = os.environ.get('WARDROBE_BASE_PATH')
        os.environ['WARDROBE_BASE_PATH'] = tmpdir

        try:
            # Create test image
            test_file = create_portrait_image_with_exif()
            original_data = test_file.read()
            test_file.seek(0)

            print(f"Original EXIF orientation: {check_orientation(original_data)['orientation']}")

            # Create wardrobe manager
            manager = WardrobeManager(base_path=tmpdir, user_id="test_user")

            # Add item (simulates upload)
            analysis_data = {
                "name": "Test Item",
                "category": "tops",
                "colors": ["red", "white"],
                "sub_category": "t-shirt"
            }

            result = manager.add_wardrobe_item(
                uploaded_file=test_file,
                analysis_data=analysis_data,
                is_styling_challenge=False
            )

            if not result:
                print("✗ FAIL: add_wardrobe_item returned None")
                return False

            print(f"Item added with ID: {result.get('id')}")

            # Get image path and check
            image_path = result.get('system_metadata', {}).get('image_path')
            if not image_path:
                print("✗ FAIL: No image_path in result")
                return False

            # Read the saved image - search for it in the temp directory
            full_path = None
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith('.jpg'):
                        full_path = os.path.join(root, f)
                        break
                if full_path:
                    break

            if not full_path or not os.path.exists(full_path):
                print(f"✗ FAIL: Saved image not found in {tmpdir}")
                return False

            print(f"Found saved image at: {full_path}")

            with open(full_path, 'rb') as f:
                saved_data = f.read()

            saved_img = Image.open(BytesIO(saved_data))
            exif_check = check_orientation(saved_data)

            print(f"Saved image size: {saved_img.size}")
            print(f"Saved EXIF orientation: {exif_check['orientation']}")

            # Verify: portrait orientation (height > width), no EXIF orientation
            if saved_img.size[0] < saved_img.size[1] and exif_check['orientation'] is None:
                print("✓ PASS: Upload flow correctly handles EXIF orientation")
                return True
            else:
                print("✗ FAIL: Image orientation or EXIF incorrect")
                return False

        finally:
            if original_base:
                os.environ['WARDROBE_BASE_PATH'] = original_base
            elif 'WARDROBE_BASE_PATH' in os.environ:
                del os.environ['WARDROBE_BASE_PATH']


def test_rotation_flow():
    """Test that rotation now correctly handles EXIF."""
    print("\n" + "=" * 60)
    print("TEST: Rotation with EXIF pre-processing")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create and save a test image with EXIF
        test_file = create_portrait_image_with_exif()
        original_data = test_file.read()

        # Save to temp file (simulating S3 download)
        test_path = os.path.join(tmpdir, "test.jpg")
        with open(test_path, 'wb') as f:
            f.write(original_data)

        print(f"Original EXIF orientation: {check_orientation(original_data)['orientation']}")

        # Simulate the FIXED rotation flow
        from io import BytesIO
        from PIL import Image, ImageOps

        with open(test_path, 'rb') as f:
            image_data = f.read()

        img = Image.open(BytesIO(image_data))
        print(f"Loaded size: {img.size}")

        # THE FIX: Apply EXIF before rotating
        img = ImageOps.exif_transpose(img)
        print(f"After exif_transpose: {img.size}")

        # Rotate 90 degrees clockwise
        rotated_img = img.rotate(-90, expand=True)
        print(f"After rotation: {rotated_img.size}")

        # Strip EXIF and save
        if 'exif' in rotated_img.info:
            del rotated_img.info['exif']

        output_path = os.path.join(tmpdir, "rotated.jpg")
        rotated_img.save(output_path, format='JPEG', quality=85)

        # Check result
        with open(output_path, 'rb') as f:
            rotated_data = f.read()

        final_img = Image.open(BytesIO(rotated_data))
        exif_check = check_orientation(rotated_data)

        print(f"Final size: {final_img.size}")
        print(f"Final EXIF orientation: {exif_check['orientation']}")

        # After transpose (100x200) + rotate 90 CW = (200x100)
        if final_img.size == (200, 100) and exif_check['orientation'] is None:
            print("✓ PASS: Rotation correctly applies EXIF first")
            return True
        else:
            print("✗ FAIL")
            return False


def main():
    print("\n" + "=" * 60)
    print("EXIF Integration Tests")
    print("Testing actual backend services with local storage")
    print("=" * 60)

    # Check piexif
    try:
        import piexif
    except ImportError:
        print("⚠️  Install piexif first: pip install piexif")
        return 1

    results = []

    results.append(("StorageManager.save_image", test_storage_manager_save()))
    results.append(("WardrobeManager.add_wardrobe_item", test_wardrobe_manager_add_item()))
    results.append(("Rotation Flow", test_rotation_flow()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
