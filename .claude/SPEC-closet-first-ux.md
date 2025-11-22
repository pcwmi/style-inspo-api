# FEATURE SPEC: Closet-First Upload UX

**Created**: Nov 22, 2025
**Owner**: Pei-Chin
**Target**: Antigravity implementation
**Priority**: P0 (Addresses #1 user frustration)

---

## Context

### Current Problem

Users find photo upload clunky and can't easily view/manage their wardrobe items.

### User Feedback (From Activated Users)

**Mia** (Nov 19, 2025):
> "It was a little clunky to upload pictures at first (take pictures, find them, email them in batches so I have enough storage etc.), but now that I can airdrop them from my phone to my desktop, it was pretty easy. The easiest thing would be to take a picture on my phone and it automatically uploads."

**Heather** (Nov 17, 2025):
> "I uploaded a black tank but it has it listed as navy. I don't see a way to edit the details of an item or tag it with other words."

> "I would add a few instructions on how to take good pics."

### Strategic Goal

Shift focus from "upload photos" to "manage my closet" - make the closet the hero, not the upload flow.

---

## What We're Building

A closet-first experience where users:
1. **See their wardrobe items first** (organized by category)
2. **Add items via floating button** (not separate upload page)
3. **Upload via modal** (stays in closet context)
4. **Edit item metadata** when AI gets details wrong
5. **See photo tips** before first upload

---

## Architecture Overview

### Current Structure (Next.js App)

- **Frontend**: `/frontend` (Next.js 13+ with App Router, deployed to Vercel)
- **Backend**: `/backend` (FastAPI, deployed to Railway)
- **Current upload page**: `/frontend/app/upload/page.tsx`
- **Dashboard**: `/frontend/app/page.tsx`
- **Production URL**: https://styleinspo.vercel.app

### New Structure (After This Feature)

- **New closet page**: `/frontend/app/closet/page.tsx` (main wardrobe view)
- **New item detail page**: `/frontend/app/closet/[item_id]/page.tsx` (view/edit single item)
- **Upload modal**: `/frontend/components/UploadModal.tsx` (replaces full page)
- **Photo guidelines modal**: `/frontend/components/PhotoGuidelines.tsx` (first-time tips)
- **Delete confirmation**: `/frontend/components/DeleteItemModal.tsx`

---

## Feature Requirements

### 1. New `/closet` Page (Main Wardrobe View)

**URL**: `/closet?user=peichin`

**Navigation**: Dashboard "Manage Closet" button → `/closet` (change from current `/upload`)

#### Layout

```
┌─────────────────────────────────────────────┐
│  ← Back to Dashboard        My Closet       │
├─────────────────────────────────────────────┤
│  [All] [Tops] [Bottoms] [Dresses] [Shoes]  │ ← Category tabs
│  [Outerwear] [Accessories]                  │
├─────────────────────────────────────────────┤
│                                             │
│  TOPS (12)                                  │
│  [Item] [Item] [Item] [Item]                │ ← 3 cols mobile
│  [Item] [Item] [Item] [Item]                │   4-5 cols desktop
│  [Item] [Item] [Item] [Item]                │
│                                             │
│  BOTTOMS (8)                                │
│  [Item] [Item] [Item] [Item]                │
│  [Item] [Item] [Item] [Item]                │
│                                             │
│  📸 Analyzing 2 photos... [1/2]             │ ← Live status (conditional)
│                                             │
│                                   ┌────────┐│
│                                   │   +    ││ ← Floating button
│                                   │  Add   ││   (bottom right)
│                                   └────────┘│
└─────────────────────────────────────────────┘
```

#### Category Tabs (Hybrid Design)

- **Default view**: "All" tab selected, shows all categories with headers
- **Filter view**: Click category tab (e.g., "Tops") → Shows only that category
- **Categories**: All | Tops | Bottoms | Dresses | Outerwear | Shoes | Accessories
- **Item count**: Show count next to category name (e.g., "TOPS (12)")

#### Item Grid

- **Mobile**: 3 columns
- **Desktop**: 4-5 columns
- **Item card**: Photo + name (truncated if long)
- **Interaction**: Tap item → Navigate to `/closet/[item_id]`

#### Floating "+ Add to Closet" Button

- **Position**: Fixed bottom right (above mobile browser controls, use safe-area CSS)
- **Style**: Circular or rounded rectangle, primary color, prominent shadow
- **Icon**: Camera icon or "+" symbol
- **Label**: "Add to Closet" or just "+"
- **Action**: Opens upload modal (or photo guidelines first time)

#### Live Upload Status Banner (Conditional)

- **Shows when**: Photos are being analyzed (backend job in progress)
- **Position**: Above item grid, below category tabs
- **Content**: "📸 Analyzing X photos... [completed/total]"
- **Updates**: Poll backend job status API every 2-3 seconds
- **Disappears**: When all jobs complete (shows toast instead)

#### Empty State (When 0 items)

```
┌─────────────────────────────────────────────┐
│                                             │
│              👗                             │
│                                             │
│   Your closet is empty—let's start         │
│   building! Add your favorite pieces       │
│   so I can help you style them.            │
│                                             │
│   ┌───────────────────────────────────┐    │
│   │    📷  Add to Closet              │    │ ← Big CTA
│   └───────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
```

---

### 2. Upload Modal Component

**File**: `/frontend/components/UploadModal.tsx`

**Triggered by**: Clicking floating "+ Add to Closet" button

**First-time users**: Show PhotoGuidelines modal first, then UploadModal

#### Modal Layout

```
┌─────────────────────────────────────────────┐
│  Upload Photos                          [×] │ ← Close button
├─────────────────────────────────────────────┤
│                                             │
│   [Click to upload or drag photos here]    │ ← File picker
│                                             │
│   Uploading 2 of 3 photos...                │ ← Progress
│   ▓▓▓▓▓▓▓▓░░░░░░░░ 67%                     │
│                                             │
│   ✅ photo1.jpg (compressed 2.1MB → 800KB) │
│   ✅ photo2.jpg (compressed 1.8MB → 650KB) │
│   ⏳ photo3.jpg uploading...                │
│                                             │
└─────────────────────────────────────────────┘
```

#### Upload Flow

1. User clicks "+ Add to Closet"
2. First time? → Show PhotoGuidelines modal → Click "Got it" → PhotoGuidelines closes
3. UploadModal opens with file picker
4. User selects photos from device
5. **Client-side compression**: Compress images before upload (reduce bandwidth)
6. **Client-side EXIF rotation**: Apply auto-rotation before upload
7. Show upload progress per file
8. When all files uploaded → Modal closes automatically
9. Return to closet page with status banner: "📸 Analyzing X photos..."
10. Items appear in grid as analysis completes (shimmer → real item fade-in)
11. Final toast notification: "✅ 3 items added to your closet"

#### Technical Details

- **Compression library**: Use `browser-image-compression` or similar
- **Target size**: Compress to ~500KB-1MB per image
- **EXIF library**: Use `exif-js` or `piexifjs` for auto-rotation (critical for Android photos)
- **Upload API**: Reuse existing `api.uploadItem()` from `/lib/api.ts`
- **Progress tracking**: Show per-file progress using upload events
- **Error handling**: If upload fails, show error message + retry button

---

### 3. Photo Guidelines Modal

**File**: `/frontend/components/PhotoGuidelines.tsx`

**Triggered by**: Before first upload (one-time only)

#### Modal Content

```
┌─────────────────────────────────────────────┐
│  📸 Tips for Great Photos               [×] │
├─────────────────────────────────────────────┤
│                                             │
│  ✓ Lay item flat on neutral surface        │
│    (bed, floor, table)                      │
│                                             │
│  ✓ Take photo from directly above          │
│                                             │
│  ✓ Include entire item (don't crop arms,   │
│    legs, etc.)                              │
│                                             │
│  ✓ Good lighting (natural light works      │
│    best)                                    │
│                                             │
│  ✓ Avoid busy backgrounds (plain white/    │
│    beige is ideal)                          │
│                                             │
│  These help the AI understand your pieces   │
│  better!                                    │
│                                             │
│         [Got it, let's start!]              │
│                                             │
└─────────────────────────────────────────────┘
```

#### Behavior

- **Show once**: Store flag in localStorage: `photo_guidelines_seen_${user}`
- **Check on button click**: If flag exists, skip directly to UploadModal
- **Dismissable**: User can close modal (still marks as "seen")

---

### 4. Item Detail/Edit Page

**URL**: `/closet/[item_id]?user=peichin`

**Triggered by**: Tapping any item in closet grid

#### View Mode Layout

```
┌─────────────────────────────────────────────┐
│  ← Back to Closet                   [Edit]  │ ← Edit button
├─────────────────────────────────────────────┤
│                                             │
│         [Large Item Photo]                  │
│         (full width, max 400px height)      │
│                                             │
├─────────────────────────────────────────────┤
│  Name:                                      │
│  Blue button-up shirt                       │
│                                             │
│  Category:                                  │
│  Tops                                       │
│                                             │
│  Colors:                                    │
│  Blue, white                                │
│                                             │
│  Style Tags:                                │
│  [Casual] [Professional]                    │
│                                             │
│  Texture:                                   │
│  Cotton                                     │
│                                             │
│  Brand:                                     │
│  [None]                                     │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  📝 AI Styling Notes:                       │
│  "Versatile basic that pairs with          │
│  everything. Perfect foundation piece..."   │
│                                             │
│  ─────────────────────────────────────────  │
│                                             │
│  [Delete Item]                              │ ← Delete button
│                                             │
└─────────────────────────────────────────────┘
```

#### Edit Mode (Tap "Edit" button)

```
┌─────────────────────────────────────────────┐
│  ← Cancel                           [Save]  │
├─────────────────────────────────────────────┤
│                                             │
│         [Large Item Photo]                  │
│                                             │
├─────────────────────────────────────────────┤
│  Name:                                      │
│  [Blue button-up shirt            ]         │ ← Text input
│                                             │
│  Category:                                  │
│  [Tops                         ▼]           │ ← Dropdown
│                                             │
│  Colors:                                    │
│  [Blue, white                  ]            │ ← Text input
│                                             │
│  Style Tags:                                │
│  [casual,professional          ]            │ ← Tag input
│                                             │
│  Texture:                                   │
│  [Cotton                       ]            │ ← Text input
│                                             │
│  Brand:                                     │
│  [                             ]            │ ← Text input
│                                             │
│  💡 AI detected: "Navy tank top"            │ ← Show overrides
│     You corrected: "Black tank top"         │
│                                             │
│  [Cancel]  [Save Changes]                   │
│                                             │
└─────────────────────────────────────────────┘
```

#### Editable Fields

- **Name**: Text input
- **Category**: Dropdown (tops, bottoms, dresses, outerwear, shoes, accessories, bags)
- **Colors**: Text input (comma-separated)
- **Style Tags**: Tag input or chips (casual, professional, edgy, minimalist, etc.)
- **Texture**: Text input
- **Brand**: Text input (optional)

#### Show AI Overrides

- When user changes a field that AI originally detected
- Show subtle indicator: "AI detected: [original] / You corrected: [new]"
- Helps user understand what they changed

#### Save Flow

1. User clicks "Save Changes"
2. Call API: `api.updateItem(itemId, updatedData)`
3. Show loading state on button
4. On success: Toast "✅ Item updated" + navigate back to closet
5. On error: Show error message, keep in edit mode

---

### 5. Delete Item Confirmation Modal

**File**: `/frontend/components/DeleteItemModal.tsx`

**Triggered by**: Clicking "Delete Item" button on item detail page

#### Modal Layout

```
┌─────────────────────────────────────────────┐
│  Delete Item                            [×] │
├─────────────────────────────────────────────┤
│                                             │
│  Are you sure you want to delete this item? │
│                                             │
│         [Item Photo - small thumbnail]      │
│         Blue button-up shirt                │
│                                             │
│  This action cannot be undone.              │
│                                             │
│  [Cancel]              [Delete]             │ ← Delete = danger color
│                                             │
└─────────────────────────────────────────────┘
```

#### Delete Flow

1. User clicks "Delete"
2. Call API: `api.deleteItem(itemId)`
3. Show loading state
4. On success: Toast "Item deleted" + navigate to `/closet`
5. Item removed from grid
6. On error: Show error message, keep modal open

---

## API Requirements

### Existing APIs (Already Implemented)

- `api.getWardrobe(user)` - Fetch all wardrobe items
- `api.uploadItem(user, file)` - Upload single photo

### New APIs Needed

#### Get Single Item

```typescript
api.getItem(user: string, itemId: string)
// GET /api/wardrobe/{user}/items/{item_id}
// Returns: Full item metadata
```

#### Update Item

```typescript
api.updateItem(user: string, itemId: string, data: ItemUpdateData)
// PUT /api/wardrobe/{user}/items/{item_id}
// Body: { name, category, colors, style_tags, texture, brand }
// Returns: Updated item metadata
```

#### Delete Item

```typescript
api.deleteItem(user: string, itemId: string)
// DELETE /api/wardrobe/{user}/items/{item_id}
// Returns: Success status
```

#### Job Status (for live upload tracking)

```typescript
api.getJobStatus(user: string, jobId: string)
// GET /api/jobs/{job_id}
// Returns: { status: "pending"|"analyzing"|"complete", progress: 0.5 }
```

**Note**: Check if these already exist in `/backend`. If not, need to implement.

---

## Dashboard Navigation Update

**File**: `/frontend/app/page.tsx`

**Change "Manage Closet" button**:
- **Current**: `href="/upload?user=${user}"`
- **New**: `href="/closet?user=${user}"`

**Location**: Find the dashboard card or button that says "Manage Closet" or "Your Closet"

---

## EXIF Auto-Rotation (Critical for Android)

### Problem

Heather's Android photos display sideways - EXIF orientation data not being applied.

### Solution

Apply EXIF rotation client-side before upload.

#### Implementation

1. **Install library**: `exif-js` or `piexifjs`
2. **In UploadModal**, before compressing:
   ```typescript
   import EXIF from 'exif-js'

   const rotateImage = (file: File): Promise<File> => {
     return new Promise((resolve) => {
       EXIF.getData(file, function() {
         const orientation = EXIF.getTag(this, "Orientation")
         // Apply rotation based on orientation value (1-8)
         // Use canvas to rotate pixels
         // Return rotated file
       })
     })
   }
   ```

3. **Apply rotation BEFORE compression**
4. **Test with Heather's Android photos** (user will provide samples)

**Fallback**: If EXIF data missing or fails, manual rotation button in item edit page (Phase 2)

---

## Design Requirements

### Mobile-First

- All layouts designed for mobile first (320px-428px width)
- Desktop is progressive enhancement
- Touch targets minimum 44px (iOS guideline)
- Bottom padding for floating button: Account for mobile browser controls using `safe-area-inset-bottom`

### Colors & Styling

- Reuse existing design system from current app
- Floating button: Primary brand color, prominent shadow
- Category tabs: Active state clearly visible
- Item cards: Clean, minimal, photo-focused

### Animations

- Item fade-in when analysis completes (subtle scale + opacity transition)
- Modal slide-up from bottom (mobile) or fade-in (desktop)
- Shimmer effect for loading items

### Accessibility

- All buttons have aria-labels
- Modals trap focus (keyboard navigation)
- Close on ESC key
- Proper heading hierarchy (h1, h2, etc.)

---

## Testing Checklist

### Upload Flow

- [ ] First-time user sees photo guidelines before upload
- [ ] Returning user goes directly to file picker
- [ ] Multiple photos can be selected at once
- [ ] Upload progress shows per-file
- [ ] Client-side compression reduces file size
- [ ] EXIF auto-rotation works (test with Heather's Android photos)
- [ ] Modal closes after upload completes
- [ ] Live status banner appears during analysis
- [ ] Items appear in grid as analysis completes
- [ ] Toast notification when all complete

### Closet Page

- [ ] Empty state shows big CTA when 0 items
- [ ] Category tabs filter correctly
- [ ] "All" tab shows all items with category headers
- [ ] Item grid is 3 columns on mobile, 4-5 on desktop
- [ ] Floating button visible on all screen sizes
- [ ] Floating button not covered by mobile browser controls

### Item Detail/Edit

- [ ] Tapping item in grid navigates to detail page
- [ ] All metadata displays correctly
- [ ] Edit mode toggles all fields to inputs
- [ ] Category dropdown has all categories
- [ ] Save button updates item and returns to closet
- [ ] "AI detected / You corrected" shows when field changed
- [ ] Delete button shows confirmation modal
- [ ] Delete confirmation actually deletes item

### Navigation

- [ ] Dashboard "Manage Closet" goes to `/closet`
- [ ] Back button on closet goes to dashboard
- [ ] Back button on item detail goes to closet
- [ ] Cancel in edit mode returns to view mode

### Error Handling

- [ ] Failed upload shows error + retry option
- [ ] Failed save shows error message
- [ ] Failed delete shows error message
- [ ] Network errors handled gracefully

---

## Files to Create

### New Pages

1. `/frontend/app/closet/page.tsx` - Main closet view
2. `/frontend/app/closet/[item_id]/page.tsx` - Item detail/edit

### New Components

3. `/frontend/components/UploadModal.tsx` - Photo upload modal
4. `/frontend/components/PhotoGuidelines.tsx` - Tips modal
5. `/frontend/components/DeleteItemModal.tsx` - Delete confirmation

### Modified Files

6. `/frontend/app/page.tsx` - Change "Manage Closet" link to `/closet`
7. `/frontend/lib/api.ts` - Add `getItem()`, `updateItem()`, `deleteItem()` if missing

### Backend (if needed)

8. `/backend/routers/wardrobe.py` - Add endpoints for get/update/delete single item

---

## Out of Scope (Defer to Phase 2)

- ❌ Search bar ("Do I have a grey sweater?")
- ❌ Bulk actions (select multiple items to delete)
- ❌ Manual photo rotation UI (if EXIF works, not needed)
- ❌ Paste link to upload (thinking about buying feature)
- ❌ Sort options (by date added, by category, etc.)
- ❌ Item usage tracking (how often worn)

---

## Success Criteria

✅ Users see their closet first (not upload page)
✅ Upload flow is mobile-native (camera → upload → done)
✅ Users can edit item metadata when AI gets details wrong
✅ Users see photo tips before first upload
✅ EXIF auto-rotation works for Android photos
✅ Users can delete items with confirmation
✅ Live upload status shows progress clearly
✅ No auto-redirect bug (users stay on closet page)

---

**This addresses the #1 user frustration (upload UX) and unlocks the #2 request (manage closet items).**

---

**Last Updated**: Nov 22, 2025
**Status**: Ready for implementation
**Assignee**: Antigravity
