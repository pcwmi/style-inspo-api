# Style Inspo Frontend

Next.js frontend for Style Inspo - AI-powered personal styling assistant.

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

Visit http://localhost:3000

## Pages

- `/` - Dashboard (homepage)
- `/occasion?user=peichin` - Occasion-based outfit generation
- `/complete?user=peichin` - Complete my look (anchor pieces)
- `/reveal?user=peichin&job=xxx` - Outfit reveal with job polling
- `/saved?user=peichin` - Saved outfits (coming soon)
- `/upload?user=peichin` - Upload wardrobe items

## Features

- Mobile-first responsive design
- Client-side image compression
- Job polling for outfit generation
- Save/dislike outfit feedback
- Tailwind CSS styling

## Deployment

### Vercel

1. Connect GitHub repo to Vercel
2. Set environment variable: `NEXT_PUBLIC_API_URL`
3. Deploy automatically on push to main

