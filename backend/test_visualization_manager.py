"""Test VisualizationManager instantiation and method signatures"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.visualization.visualization_manager import VisualizationManager
import inspect

print("Test: VisualizationManager instantiation and methods")

# Test 1: Instantiation
try:
    manager = VisualizationManager(user_id="test_user")
    print("✅ VisualizationManager instantiated successfully")
except Exception as e:
    print(f"❌ Failed to instantiate: {e}")
    sys.exit(1)

# Test 2: Check visualize_outfit method signature
sig = inspect.signature(manager.visualize_outfit)
params = list(sig.parameters.keys())

print(f"   visualize_outfit parameters: {params}")

if 'outfit_id' in params and 'provider_name' in params:
    print("✅ visualize_outfit() has correct parameters")
else:
    print("❌ visualize_outfit() missing expected parameters!")
    sys.exit(1)

# Test 3: Verify dependencies are accessible
try:
    print(f"   Storage manager: {type(manager.storage).__name__}")
    print(f"   Outfit manager: {type(manager.outfit_manager).__name__}")
    print(f"   Profile manager: {type(manager.profile_manager).__name__}")
    print(f"   Provider factory: {type(manager.provider_factory).__name__}")
    print("✅ All dependencies initialized")
except Exception as e:
    print(f"❌ Dependency error: {e}")
    sys.exit(1)

# Test 4: Verify SavedOutfitsManager has new methods
from services.saved_outfits_manager import SavedOutfitsManager

outfit_mgr = SavedOutfitsManager(user_id="test_user")
has_get_by_id = hasattr(outfit_mgr, 'get_outfit_by_id')
has_update_viz = hasattr(outfit_mgr, 'update_outfit_visualization')

if has_get_by_id and has_update_viz:
    print("✅ SavedOutfitsManager has get_outfit_by_id() and update_outfit_visualization()")
else:
    print(f"❌ SavedOutfitsManager missing methods: get_outfit_by_id={has_get_by_id}, update_outfit_visualization={has_update_viz}")
    sys.exit(1)

print("\n✅ Step 3 Complete: VisualizationManager ready")
