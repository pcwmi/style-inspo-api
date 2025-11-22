# How to Run the Background Worker

The Style Inspo API relies on a background worker to process image uploads and generate outfits. If this worker is not running, uploads will stall in the "processing" state.

## Prerequisites
- Redis must be running (`redis-server`).
- Backend virtual environment must be active.

## Running the Worker
Open a new terminal window and run:

```bash
# From the project root
source backend/venv/bin/activate
rq worker analysis --path backend
```

## Troubleshooting
If jobs are still not processing:
1. Check if Redis is running: `redis-cli ping` (should return PONG).
2. Check worker logs for errors.
3. Ensure the `backend` directory is in the python path (the `--path backend` flag handles this).
