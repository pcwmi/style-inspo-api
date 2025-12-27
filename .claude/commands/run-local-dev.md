---
description: Start all dev servers and open browser
---

Start all development servers in the background and open the app in your browser:

1. Backend API on port 8000
2. RQ worker for outfit generation jobs
3. Next.js frontend on port 3000
4. Open browser to http://localhost:3000/?user=peichin

Run these commands in the background:

```bash
cd backend && python -m uvicorn main:app --reload --port 8000
```

```bash
cd backend && source venv/bin/activate && rq worker outfits analysis --url redis://localhost:6379/0
```

```bash
cd frontend && npm run dev
```

```bash
sleep 5 && open http://localhost:3000/?user=peichin
```

After starting, you can:
- Check running background processes with /tasks
- Stop servers with the KillShell tool using their shell IDs
- View logs with BashOutput tool
