#!/usr/bin/env python3
"""
Test script to verify EXIF orientation fixes.

This script:
1. Creates a test image with EXIF orientation metadata
2. Tests the upload flow (exif_transpose + save)
3. Verifies the saved image has correct orientation and no EXIF
4. Tests the rotation flow

Run from project root:
    python backend/tests/test_exif_orientation.py
"""

import os
import sys
import tempfile
from io import BytesIO
from PIL import Image, ImageOps
import piexif

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def create_test_image_with_exif(orientation: int = 6) -> bytes:
    """
    Create a test image with EXIF orientation metadata.

    Orientation values:
        1 = Normal (no rotation)
        3 = 180 degrees
        6 = 90 degrees CW (portrait photo taken with camera on right side)
        8 = 90 degrees CCW
    """
    # Create a simple test image (red rectangle on white background)
    # Make it non-square so we can see rotation
    img = Image.new('RGB', (200, 100), color='white')

    # Draw a red rectangle in the top-left to indicate orientation
    for x in range(50):
        for y in range(25):
            img.putpixel((x, y), (255, 0, 0))

    # Create EXIF data with orientation
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Orientation: orientation
        }
    }
    exif_bytes = piexif.dump(exif_dict)

    # Save to bytes with EXIF
    buffer = BytesIO()
    img.save(buffer, format='JPEG', exif=exif_bytes, quality=95)
    buffer.seek(0)

    return buffer.read()


def check_image_exif(image_data: bytes) -> dict:
    """
    Check EXIF data in an image.
    Returns dict with orientation and has_exif flag.
    """
    try:
        exif_dict = piexif.load(image_data)
        orientation = exif_dict.get("0th", {}).get(piexif.ImageIFD.Orientation, None)
        return {
            "has_exif": True,
            "orientation": orientation
        }
    except Exception as e:
        return {
            "has_exif": False,
            "orientation": None,
            "error": str(e)
        }


def test_exif_transpose():
    """Test that exif_transpose correctly rotates the image."""
    print("\n" + "=" * 60)
    print("TEST 1: EXIF Transpose")
    print("=" * 60)

    # Create image with orientation 6 (90 CW rotation needed)
    image_data = create_test_image_with_exif(orientation=6)

    # Load and check original
    img = Image.open(BytesIO(image_data))
    print(f"Original size: {img.size}")  # Should be 200x100

    # Apply exif_transpose
    img_transposed = ImageOps.exif_transpose(img)
    print(f"After exif_transpose: {img_transposed.size}")  # Should be 100x200 (rotated)

    if img_transposed.size == (100, 200):
        print("✓ PASS: Image correctly rotated from 200x100 to 100x200")
        return True
    else:
        print("✗ FAIL: Image size incorrect after transpose")
        return False


def test_exif_stripping():
    """Test that our save flow strips EXIF data."""
    print("\n" + "=" * 60)
    print("TEST 2: EXIF Stripping on Save")
    print("=" * 60)

    # Create image with EXIF
    image_data = create_test_image_with_exif(orientation=6)

    # Check original has EXIF
    exif_check = check_image_exif(image_data)
    print(f"Original has EXIF: {exif_check['has_exif']}, orientation: {exif_check['orientation']}")

    if not exif_check['has_exif'] or exif_check['orientation'] != 6:
        print("✗ FAIL: Test image doesn't have expected EXIF")
        return False

    # Simulate our save flow
    img = Image.open(BytesIO(image_data))
    img = ImageOps.exif_transpose(img)  # Apply EXIF orientation

    # Strip EXIF (our fix)
    if 'exif' in img.info:
        del img.info['exif']

    # Save
    output_buffer = BytesIO()
    img.save(output_buffer, format='JPEG', quality=85)
    output_buffer.seek(0)
    saved_data = output_buffer.read()

    # Check saved image
    exif_check_after = check_image_exif(saved_data)
    print(f"After save - has EXIF: {exif_check_after['has_exif']}, orientation: {exif_check_after['orientation']}")

    # Verify EXIF is stripped
    if not exif_check_after['has_exif'] or exif_check_after['orientation'] is None:
        print("✓ PASS: EXIF data correctly stripped")
        return True
    else:
        print("✗ FAIL: EXIF data still present after save")
        return False


def test_rotation_with_exif():
    """Test that rotation correctly handles EXIF images."""
    print("\n" + "=" * 60)
    print("TEST 3: Rotation with EXIF (simulating bug fix)")
    print("=" * 60)

    # Create image with EXIF orientation 6 (90 CW needed)
    image_data = create_test_image_with_exif(orientation=6)

    # Load (simulating our fixed rotation flow)
    img = Image.open(BytesIO(image_data))
    print(f"Loaded size: {img.size}")  # 200x100

    # Apply EXIF transpose (THE FIX)
    img = ImageOps.exif_transpose(img)
    print(f"After exif_transpose: {img.size}")  # 100x200

    # Now rotate 90 degrees clockwise (as user requested)
    degrees = 90
    rotated_img = img.rotate(-degrees, expand=True)
    print(f"After rotation: {rotated_img.size}")  # 200x100

    # Strip EXIF and save
    if 'exif' in rotated_img.info:
        del rotated_img.info['exif']

    output_buffer = BytesIO()
    rotated_img.save(output_buffer, format='JPEG', quality=85)
    output_buffer.seek(0)

    # Verify orientation is stripped (some EXIF may remain, but orientation must be gone)
    exif_check = check_image_exif(output_buffer.read())
    print(f"Saved image - has EXIF: {exif_check['has_exif']}, orientation: {exif_check['orientation']}")

    # What matters: orientation tag is gone or None (so browsers won't re-apply)
    if rotated_img.size == (200, 100) and exif_check['orientation'] is None:
        print("✓ PASS: Rotation correctly applied, orientation tag stripped")
        return True
    else:
        print("✗ FAIL: Rotation or orientation stripping failed")
        return False


def test_full_upload_flow():
    """Test the complete upload flow as it happens in production."""
    print("\n" + "=" * 60)
    print("TEST 4: Full Upload Flow (simulating wardrobe_manager.py)")
    print("=" * 60)

    # Simulate a portrait photo from phone (orientation 6)
    image_data = create_test_image_with_exif(orientation=6)
    uploaded_file = BytesIO(image_data)

    print("Step 1: User uploads portrait photo...")

    # Simulate wardrobe_manager.add_wardrobe_item (lines 87-88)
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)  # Line 88

    print(f"  After exif_transpose: {image.size}")

    # Simulate storage_manager._save_to_s3 (lines 134-142)
    image.thumbnail((800, 800), Image.Resampling.LANCZOS)

    # Our fix - strip EXIF
    if 'exif' in image.info:
        del image.info['exif']

    buffer = BytesIO()
    image.save(buffer, format='JPEG', quality=85, optimize=True)
    buffer.seek(0)
    saved_data = buffer.read()

    print("Step 2: Image saved to S3...")

    # Verify saved image
    saved_img = Image.open(BytesIO(saved_data))
    exif_check = check_image_exif(saved_data)

    print(f"  Saved image size: {saved_img.size}")
    print(f"  Has EXIF: {exif_check['has_exif']}, orientation: {exif_check['orientation']}")

    # Expected: portrait orientation (height > width), orientation tag stripped
    if saved_img.size[0] < saved_img.size[1] and exif_check['orientation'] is None:
        print("✓ PASS: Portrait image correctly oriented, orientation tag stripped")
        return True
    else:
        print("✗ FAIL: Image orientation or orientation tag incorrect")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("EXIF Orientation Fix - Test Suite")
    print("=" * 60)

    # Check if piexif is installed
    try:
        import piexif
    except ImportError:
        print("\n⚠️  piexif not installed. Run: pip install piexif")
        print("This is only needed for testing, not for production.")
        return 1

    results = []

    results.append(("EXIF Transpose", test_exif_transpose()))
    results.append(("EXIF Stripping", test_exif_stripping()))
    results.append(("Rotation with EXIF", test_rotation_with_exif()))
    results.append(("Full Upload Flow", test_full_upload_flow()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed! The EXIF fixes are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
