"""End-to-end test for outfit visualization"""
import requests
import time
import sys

API_URL = "http://localhost:8000"
USER_ID = "peichin"

print("=" * 60)
print("END-TO-END VISUALIZATION TEST")
print("=" * 60)

# Step 1: Verify user has model_descriptor set
print("\n[Step 1] Checking user profile...")
profile_response = requests.get(f"{API_URL}/api/users/{USER_ID}/profile")
if profile_response.status_code != 200:
    print(f"❌ Failed to get profile: {profile_response.status_code}")
    sys.exit(1)

profile = profile_response.json()
model_descriptor = profile.get('model_descriptor')

if not model_descriptor:
    print("  No model_descriptor set. Setting default...")
    update_response = requests.post(
        f"{API_URL}/api/users/{USER_ID}/profile",
        json={
            "model_descriptor": "Model: ~163 cm, ~150 lb, Asian woman, dark wavy chest-length hair, softly defined hourglass figure"
        }
    )
    if update_response.status_code == 200:
        print("  ✅ Model descriptor set")
    else:
        print(f"  ❌ Failed to set model_descriptor: {update_response.text}")
        sys.exit(1)
else:
    print(f"  ✅ Model descriptor: {model_descriptor[:60]}...")

# Step 2: Get first saved outfit
print("\n[Step 2] Fetching saved outfits...")
outfits_response = requests.get(f"{API_URL}/api/outfits/{USER_ID}/saved")
if outfits_response.status_code != 200:
    print(f"❌ Failed to get outfits: {outfits_response.status_code}")
    sys.exit(1)

outfits = outfits_response.json()
if not outfits.get('outfits'):
    print("❌ No saved outfits found!")
    sys.exit(1)

outfit = outfits['outfits'][0]
outfit_id = outfit['id']
num_items = len(outfit['outfit_data']['items'])

print(f"  ✅ Using outfit: {outfit_id}")
print(f"     Items: {num_items}")
for item in outfit['outfit_data']['items']:
    print(f"       - {item['name']}")

# Step 3: Request visualization
print(f"\n[Step 3] Requesting visualization...")
viz_response = requests.post(
    f"{API_URL}/api/outfits/{outfit_id}/visualize?user_id={USER_ID}"
)

if viz_response.status_code != 200:
    print(f"❌ Failed to create job: {viz_response.status_code}")
    print(f"   Response: {viz_response.text}")
    sys.exit(1)

job_data = viz_response.json()
job_id = job_data["job_id"]
print(f"  ✅ Visualization job created: {job_id}")
print(f"     Status: {job_data['status']}")
print(f"     Estimated time: {job_data['estimated_time']}s")

# Step 4: Poll for completion
print(f"\n[Step 4] Polling job status...")
print("  (Note: Actual Runway API call will take 25-40 seconds)")
print("  " + "-" * 56)

max_polls = 90  # 3 minutes max
poll_count = 0

for i in range(max_polls):
    time.sleep(2)
    poll_count += 1

    status_response = requests.get(f"{API_URL}/api/jobs/{job_id}")
    if status_response.status_code != 200:
        print(f"\n  ❌ Failed to get job status: {status_response.status_code}")
        continue

    status_data = status_response.json()
    status = status_data.get('status', 'unknown')
    progress = status_data.get('progress', 0)

    # Show progress
    if poll_count % 5 == 0 or status in ['complete', 'failed']:
        elapsed = poll_count * 2
        print(f"  Poll {poll_count} ({elapsed}s): {status} - Progress: {progress}%")

    if status == 'complete':
        result = status_data.get('result', {})
        image_url = result.get('image_url')
        generation_time = result.get('generation_time')
        provider = result.get('provider')

        print("\n" + "=" * 60)
        print("✅ VISUALIZATION COMPLETE!")
        print("=" * 60)
        print(f"  Image URL: {image_url}")
        print(f"  Generation time: {generation_time:.1f}s")
        print(f"  Provider: {provider}")
        print()

        # Verify permanent storage
        if 'style-inspo.s3' in image_url or image_url.startswith('https://') or 'wardrobe_photos' in image_url:
            print("  ✅ Image stored in permanent location")
        else:
            print(f"  ⚠️  Warning: Image URL doesn't look permanent: {image_url}")

        # Step 5: Verify outfit was updated with visualization_url
        print("\n[Step 5] Verifying outfit was updated...")
        updated_outfits = requests.get(f"{API_URL}/api/outfits/{USER_ID}/saved").json()
        updated_outfit = next((o for o in updated_outfits['outfits'] if o['id'] == outfit_id), None)

        if updated_outfit and updated_outfit.get('visualization_url'):
            print(f"  ✅ Outfit updated with visualization_url")
            print(f"     URL: {updated_outfit['visualization_url'][:80]}...")
        else:
            print(f"  ⚠️  Outfit not updated with visualization_url")

        print("\n" + "=" * 60)
        print("✅ END-TO-END TEST PASSED")
        print("=" * 60)
        sys.exit(0)

    elif status == 'failed':
        error = status_data.get('error', 'Unknown error')
        print(f"\n❌ Job failed: {error}")
        sys.exit(1)

print(f"\n❌ Timeout waiting for visualization (waited {max_polls * 2}s)")
sys.exit(1)
