---
description: Test the mock outfit generation and verify the Dislike flow
---

This workflow guides you through testing the mock outfit generation and verifying the "Dislike" functionality, including the "Other" reason text box.

1. **Navigate to the Occasion Page with Test User**
   - Open `http://localhost:3001/occasion?user=test`
   - This user ID triggers the mock generation mode automatically.

2. **Generate Mock Outfits**
   - Select an occasion (e.g., "Weekend errands").
   - Click "Create Outfits".
   - You should see the "Creating your outfits..." screen briefly, followed by the Reveal page.
   - Verify that "Mock Shirt", "Mock Jeans", etc., are displayed.

3. **Verify Dislike Flow**
   - Click the "Dislike" (thumbs down) button on any outfit.
   - Select "Other" as the reason.
   - Type a reason in the "Please specify" text box (e.g., "Test reason").
   - **Verification Point**: Ensure the text box remains visible while typing.
   - Click "Submit".
   - Verify that an alert "Feedback recorded" appears.

4. **Verify Save Flow (Optional)**
   - Click "Save Outfit" on another outfit.
   - Select some feedback options.
   - Click "Save".
   - Verify that an alert "Outfit saved!" appears.
