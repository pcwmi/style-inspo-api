# Closet-First UX Spec - Implementation Addendum

**Date**: Nov 22, 2025
**Purpose**: Supplement main spec with actual codebase details for Antigravity

**Main Spec**: `.claude/SPEC-closet-first-ux.md`

---

## Existing Implementation Details (Don't Rebuild)

### **API Client** (`/frontend/lib/api.ts`)

**Already Implemented** ✅:
```typescript
// Wardrobe APIs - ALREADY EXIST
api.getWardrobe(userId: string)           // Line 9-13
api.uploadItem(userId, file, useRealAi)   // Line 15-31
api.deleteItem(userId, itemId)            // Line 33-39

// Job Status API - ALREADY EXISTS
api.getJobStatus(jobId: string)           // Line 60-70

// Outfit APIs - ALREADY EXIST
api.generateOutfits(request)              // Line 42-58
api.saveOutfit(request)                   // Line 72-84
api.dislikeOutfit(request)                // Line 86-98

// Profile APIs - ALREADY EXIST
api.getProfile(userId)                    // Line 101-105
api.updateProfile(userId, profile)        // Line 107-118

// Saved/Disliked - ALREADY EXIST
api.getSavedOutfits(userId)               // Line 121-125
api.getDislikedOutfits(userId)            // Line 127-131
```

**Need to Add** ❌:
```typescript
// Get single item for detail page
api.getItem(userId: string, itemId: string) {
  const res = await fetch(`${API_URL}/api/wardrobe/${userId}/items/${itemId}`)
  if (!res.ok) throw new Error('Failed to fetch item')
  return res.json()
}

// Update item metadata
api.updateItem(userId: string, itemId: string, data: ItemUpdateData) {
  const res = await fetch(`${API_URL}/api/wardrobe/${userId}/items/${itemId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error('Failed to update item')
  return res.json()
}
```

**Backend endpoints to implement** (if not exist):
- `GET /api/wardrobe/{user_id}/items/{item_id}` - Get single item
- `PUT /api/wardrobe/{user_id}/items/{item_id}` - Update item metadata

---

### **Design System** (`/frontend/app/globals.css`)

**DO NOT invent new design** - Use existing editorial magazine theme:

#### **Fonts** (Already loaded):
```css
--font-serif: 'Libre Baskerville', serif;     /* Headings, editorial feel */
--font-sans: 'DM Sans', sans-serif;           /* Body text, clean readability */
```

#### **Colors** (Already defined):
```css
/* Backgrounds */
--bg-bone: #FAF7F2;              /* Page background (warm white) */
--bg-card: rgba(255,255,255,0.5); /* Card backgrounds (translucent) */

/* Text */
--text-ink: #1a1614;             /* Primary text (dark brown) */
--text-muted: #6B625A;           /* Secondary text (muted brown) */

/* Accents */
--accent-terracotta: #C85A3E;    /* Primary CTA buttons (warm orange-red) */
--accent-sand: #E8DED2;          /* Subtle accents (beige) */

/* Borders */
--border-subtle: rgba(26,22,20,0.12); /* Subtle dividers */
```

#### **Typography Scale** (Already defined):
- h1: `text-2xl md:text-3xl` (24px → 30px)
- h2: `text-xl md:text-2xl` (20px → 24px)
- h3: `text-lg md:text-xl` (18px → 20px)
- Body: `16px` (minimum readable on mobile, prevents iOS zoom)

#### **Button Styles** (Use these patterns):

**Primary CTA** (floating "+ Add" button):
```jsx
<button className="
  bg-[var(--accent-terracotta)]
  text-white
  rounded-full
  px-6 py-3
  shadow-lg
  hover:shadow-xl
  transition-shadow
  fixed bottom-8 right-4
  z-50
">
  + Add to Closet
</button>
```

**Secondary Button**:
```jsx
<button className="
  border-2
  border-[var(--text-ink)]
  bg-transparent
  text-[var(--text-ink)]
  px-4 py-2
  rounded
  hover:bg-[var(--accent-sand)]
  transition-colors
">
  Cancel
</button>
```

**Danger Button** (Delete):
```jsx
<button className="
  bg-red-600
  text-white
  px-4 py-2
  rounded
  hover:bg-red-700
  transition-colors
">
  Delete
</button>
```

#### **Mobile Safe-Area** (Already configured):
```css
/* Use CSS custom properties for mobile safe area */
padding-bottom: calc(1rem + env(safe-area-inset-bottom));
```

Apply to floating button to avoid overlap with mobile browser controls.

---

### **Existing Page Structure**

**Current routes** (`/frontend/app/`):
```
/                    → Dashboard (page.tsx)
/welcome             → Onboarding start
/words               → 3-word style profile
/upload              → Photo upload (TO BE DEPRECATED - replace with closet)
/path-choice         → Post-onboarding choice
/occasion            → Occasion-based generation
/complete            → Complete my look
/reveal              → Outfit reveal
/saved               → Saved outfits
/disliked            → Disliked outfits
```

**NEW routes to create**:
```
/closet              → Main wardrobe view (NEW)
/closet/[item_id]    → Item detail/edit (NEW)
```

---

### **Dashboard Navigation Update**

**File**: `/frontend/app/page.tsx`

**Find this link** (approximate location, search for "Manage Closet" or "upload"):
```tsx
<Link href={`/upload?user=${user}`}>
  Manage Closet
</Link>
```

**Change to**:
```tsx
<Link href={`/closet?user=${user}`}>
  Manage Closet
</Link>
```

---

## Technical Implementation Notes

### **1. Client-Side Image Compression**

**Recommended library**: `browser-image-compression`

```bash
npm install browser-image-compression
```

**Usage in UploadModal**:
```typescript
import imageCompression from 'browser-image-compression'

const compressImage = async (file: File): Promise<File> => {
  const options = {
    maxSizeMB: 1,              // Target max size 1MB
    maxWidthOrHeight: 1920,    // Max dimension
    useWebWorker: true,        // Better performance
    fileType: 'image/jpeg'     // Standardize to JPEG
  }
  return await imageCompression(file, options)
}
```

---

### **2. EXIF Auto-Rotation**

**Recommended library**: `exif-js`

```bash
npm install exif-js
npm install --save-dev @types/exif-js
```

**Usage**:
```typescript
import EXIF from 'exif-js'

const rotateImage = async (file: File): Promise<File> => {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const reader = new FileReader()

    reader.onload = (e) => {
      img.src = e.target?.result as string

      img.onload = () => {
        EXIF.getData(img as any, function(this: any) {
          const orientation = EXIF.getTag(this, "Orientation")

          // Create canvas and rotate based on orientation (1-8)
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')!

          // Apply rotation logic based on orientation value
          // ... (implement full rotation matrix)

          canvas.toBlob((blob) => {
            if (blob) {
              resolve(new File([blob], file.name, { type: 'image/jpeg' }))
            }
          }, 'image/jpeg', 0.95)
        })
      }
    }

    reader.readAsDataURL(file)
  })
}
```

**Order of operations**:
1. Read file
2. Apply EXIF rotation **first**
3. Then compress image
4. Then upload

---

### **3. Modal Component Pattern**

**Use React portal** for modals to avoid z-index issues:

```tsx
import { createPortal } from 'react-dom'
import { useEffect, useState } from 'react'

export function Modal({ isOpen, onClose, children }: ModalProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    return () => setMounted(false)
  }, [])

  if (!isOpen || !mounted) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal content */}
      <div className="relative bg-white rounded-lg shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {children}
      </div>
    </div>,
    document.body
  )
}
```

---

### **4. Toast Notifications**

**Recommended**: Use `react-hot-toast` (lightweight, mobile-friendly)

```bash
npm install react-hot-toast
```

**Usage**:
```tsx
import toast, { Toaster } from 'react-hot-toast'

// In layout.tsx
<Toaster
  position="bottom-center"
  toastOptions={{
    style: {
      background: 'var(--text-ink)',
      color: 'white',
      fontSize: '16px',
    },
    duration: 3000,
  }}
/>

// In components
toast.success('✅ 3 items added to your closet')
toast.error('Failed to upload. Please try again.')
```

---

### **5. Category Tabs Component**

**Reuse Tailwind patterns from existing app**:

```tsx
const categories = ['All', 'Tops', 'Bottoms', 'Dresses', 'Shoes', 'Outerwear', 'Accessories']

<div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
  {categories.map(cat => (
    <button
      key={cat}
      onClick={() => setActiveCategory(cat)}
      className={`
        px-4 py-2 rounded-full whitespace-nowrap text-sm
        transition-colors
        ${activeCategory === cat
          ? 'bg-[var(--accent-terracotta)] text-white'
          : 'bg-[var(--accent-sand)] text-[var(--text-ink)]'
        }
      `}
    >
      {cat}
    </button>
  ))}
</div>
```

---

### **6. Item Grid Layout**

**Use CSS Grid** (responsive, clean):

```tsx
<div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
  {items.map(item => (
    <Link
      key={item.id}
      href={`/closet/${item.id}?user=${user}`}
      className="
        group
        bg-white
        rounded-lg
        overflow-hidden
        shadow-sm
        hover:shadow-md
        transition-shadow
      "
    >
      <div className="aspect-square relative">
        <img
          src={item.image_path}
          alt={item.name}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-2">
        <p className="text-sm truncate text-[var(--text-ink)]">
          {item.name}
        </p>
      </div>
    </Link>
  ))}
</div>
```

---

### **7. localStorage for Photo Guidelines Flag**

```typescript
// Check if user has seen guidelines
const hasSeenGuidelines = localStorage.getItem(`photo_guidelines_seen_${user}`) === 'true'

// Mark as seen
localStorage.setItem(`photo_guidelines_seen_${user}`, 'true')
```

---

## Backend Endpoints to Implement

**Check if these exist in `/backend/routers/wardrobe.py`**:

### **Get Single Item**
```python
@router.get("/api/wardrobe/{user_id}/items/{item_id}")
async def get_item(user_id: str, item_id: str):
    """Get single wardrobe item with full metadata"""
    # Implementation
    return item_data
```

### **Update Item**
```python
@router.put("/api/wardrobe/{user_id}/items/{item_id}")
async def update_item(
    user_id: str,
    item_id: str,
    data: ItemUpdateRequest
):
    """Update wardrobe item metadata (name, category, colors, etc.)"""
    # Implementation
    # Update wardrobe_metadata.json
    return updated_item
```

---

## Migration Path

**Recommended order**:

1. **Phase 1**: API endpoints
   - Add `getItem()` and `updateItem()` to backend
   - Add client methods to `/lib/api.ts`
   - Test with Postman/curl

2. **Phase 2**: Closet page (no upload yet)
   - Create `/app/closet/page.tsx` with static data
   - Category tabs + item grid
   - Floating button (doesn't work yet)
   - Test navigation from dashboard

3. **Phase 3**: Item detail/edit
   - Create `/app/closet/[item_id]/page.tsx`
   - View mode + edit mode
   - Delete confirmation modal
   - Test editing and deletion

4. **Phase 4**: Upload modal
   - Create `UploadModal.tsx` component
   - Implement EXIF rotation + compression
   - Wire up to closet page
   - Photo guidelines modal

5. **Phase 5**: Live upload status
   - Poll job status API
   - Show progress banner
   - Items fade in as complete

---

## Success Criteria (Updated)

**Must work**:
- ✅ Existing upload API already handles background jobs
- ✅ Existing design system provides all styles needed
- ✅ Dashboard navigation redirects to `/closet` instead of `/upload`
- ✅ Item detail page can fetch, edit, and delete items
- ✅ Upload modal compresses + rotates images before upload
- ✅ Photo guidelines only show once per user
- ✅ EXIF rotation works for Heather's Android photos

**Test with**:
- Heather's sideways Android photos (user will provide)
- Multiple file upload (3-5 images at once)
- Edit item metadata (change colors, category, etc.)
- Delete item with confirmation

---

**This addendum should be read alongside the main spec for complete implementation guidance.**
