# Style Inspo

AI-powered personal styling from your own closet. Inspired by Allison Bornstein's "Wear it Well" methodology.

**Live app:** [styleinspo.vercel.app](https://styleinspo.vercel.app/)
**Text it for a quick opinion.** Send a message via SMS or WhatsApp -- "what should I wear to dinner tonight?" -- and get an outfit collage back in seconds. Share Instagram screenshots for inspiration and it will recreate the look from pieces you already own.

**Use the web app for deeper exploration.** Browse your wardrobe visually, generate multiple outfit options, save favorites, and build a style identity over time.

The styling agent knows your wardrobe, remembers your feedback, and understands garment physics -- so it won't suggest tucking a chunky knit into slim trousers.

## Architecture

Agent-native design: intelligence lives in prompts, not code. The system exposes 32 CRUD primitives (wardrobe, profile, outfits, feedback, consider-buy) and lets the AI agent reason about what works together. No framework needed -- the agent loop is ~20 lines.

```
User texts "date night outfit"
  → Agent reasons over wardrobe + profile + feedback history
  → Selects items, explains reasoning
  → Generates outfit collage image
  → Sends back via MMS
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| Frontend | Next.js (React/TypeScript) |
| AI | OpenAI GPT |
| Storage | AWS S3 (images), Redis (conversation state) |
| SMS/MMS | Twilio |
| Visualization | fal.ai (Flux), Runway (fallback) |
| Analytics | PostHog |
| Hosting | Railway (backend), Vercel (frontend) |

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # Edit with your API keys
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # Runs on http://localhost:3003
```

### Environment Variables

The backend requires:
- `OPENAI_API_KEY` -- GPT API access
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` -- image storage
- `REDIS_URL` -- conversation state
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` -- SMS/MMS

## Project Structure

```
style-inspo-api/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── agent/               # AI agent loop and prompts
│   ├── api/                 # API routes (wardrobe, outfits, SMS, etc.)
│   ├── primitives/          # CRUD operations (32 primitives)
│   ├── services/            # Collage generation, storage, conversations
│   └── tests/               # Eval harnesses
├── frontend/
│   ├── src/app/             # Next.js pages
│   ├── src/components/      # React components
│   └── src/lib/             # API client, utilities
└── .claude/                 # Claude Code project context
```

## Deployment

- **Backend**: Railway -- push to `main` triggers automatic deploy
- **Frontend**: Vercel -- push to `main` triggers automatic deploy
