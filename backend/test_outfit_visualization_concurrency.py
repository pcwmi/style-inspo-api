"""Unit tests for outfit visualization concurrency."""
import time
import threading
from services.saved_outfits_manager import SavedOutfitsManager

def test_update_visualization_no_deadlock():
    """Test that update_outfit_visualization completes without deadlock."""
    manager = SavedOutfitsManager(user_id="test_user")

    # Create a simple mock outfit combo object
    class MockOutfitCombo:
        def __init__(self):
            self.items = [
                {"id": "item1", "name": "Test Item", "category": "tops", "image_path": "test.jpg"}
            ]
            self.styling_notes = "Test notes"
            self.why_it_works = "Test reason"
            self.confidence_level = "Comfort Zone"
            self.vibe_keywords = ["casual"]

    outfit = MockOutfitCombo()
    manager.save_outfit(outfit, reason="Test")

    # Get the outfit ID
    outfits = manager.get_saved_outfits()
    outfit_id = outfits[0]["id"]

    # Test that update completes within 1 second (should be instant)
    start = time.time()
    success = manager.update_outfit_visualization(
        outfit_id,
        "https://example.com/viz.jpg"
    )
    elapsed = time.time() - start

    # Assertions
    assert success is True, "Update should succeed"
    assert elapsed < 1.0, f"Update took {elapsed}s - should be instant (deadlock would timeout at 180s)"

    # Verify the URL was actually updated
    updated_outfits = manager.get_saved_outfits()
    assert updated_outfits[0]["visualization_url"] == "https://example.com/viz.jpg"
    print(f"✅ Update completed in {elapsed:.3f}s (no deadlock)")


def test_concurrent_updates_no_crash():
    """Test that concurrent updates don't cause crashes (race condition test)."""
    manager = SavedOutfitsManager(user_id="test_user_concurrent")

    # Create a simple mock outfit combo object
    class MockOutfitCombo:
        def __init__(self):
            self.items = [{"id": "item1", "name": "Test", "category": "tops", "image_path": "test.jpg"}]
            self.styling_notes = "Test"
            self.why_it_works = "Test"
            self.confidence_level = "Comfort Zone"
            self.vibe_keywords = ["casual"]

    outfit = MockOutfitCombo()
    manager.save_outfit(outfit, reason="Test")

    outfits = manager.get_saved_outfits()
    outfit_id = outfits[0]["id"]

    # Run 10 concurrent updates
    errors = []
    def update_worker(i):
        try:
            manager.update_outfit_visualization(
                outfit_id,
                f"https://example.com/viz{i}.jpg"
            )
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=update_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5.0)  # 5 second timeout per thread

    # Verify no crashes
    assert len(errors) == 0, f"Concurrent updates caused errors: {errors}"

    # Verify one of the URLs was written (may be any due to race)
    final_outfits = manager.get_saved_outfits()
    assert "visualization_url" in final_outfits[0]
    print(f"✅ 10 concurrent updates completed without crashes")


if __name__ == "__main__":
    test_update_visualization_no_deadlock()
    test_concurrent_updates_no_crash()
    print("\n✅ All concurrency tests passed!")
