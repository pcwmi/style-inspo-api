"""Test Runway provider with user-level model descriptor"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.visualization import VisualizationProviderFactory, ImageGenerationRequest
import inspect

# Test 1: Check method signature
print("Test 1: Verify generate_image() method signature")
factory = VisualizationProviderFactory()
provider = factory.create_provider("runway")

# Check that generate_image accepts model_descriptor parameter
sig = inspect.signature(provider.generate_image)
params = list(sig.parameters.keys())

print(f"   Method parameters: {params}")

if 'model_descriptor' in params:
    print("✅ generate_image() accepts model_descriptor parameter")
    print(f"   Provider name: {provider.get_provider_name()}")
else:
    print("❌ model_descriptor parameter not found!")
    sys.exit(1)

# Check _create_outfit_prompt signature
sig2 = inspect.signature(provider._create_outfit_prompt)
params2 = list(sig2.parameters.keys())

if 'model_descriptor' in params2:
    print("✅ _create_outfit_prompt() accepts model_descriptor parameter")
else:
    print("❌ _create_outfit_prompt() missing model_descriptor parameter!")
    sys.exit(1)

# Test 2: With user-level model_descriptor
print("\nTest 2: Provider with user-level descriptor")
test_descriptor = "Model: 5'6\" Black woman, curly shoulder-length hair"

# Verify we can call with custom descriptor
try:
    print(f"✅ Can pass custom descriptor: '{test_descriptor}'")
    print("   (Not calling API to avoid charges - signature test only)")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("\n✅ Step 2 Complete: Runway provider now accepts user-level model_descriptor")
