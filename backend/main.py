"""
FastAPI Backend for Style Inspo
Main application entry point
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Configure logging for Railway visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    # Startup: Initialize database if DATABASE_URL is configured
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            from db.database import init_db, close_db
            await init_db()
            logging.info("Database initialized")
        except Exception as e:
            logging.warning(f"Database initialization skipped: {e}")
    else:
        logging.info("DATABASE_URL not configured, skipping database initialization")

    # Warm up rembg model (background removal for collages)
    try:
        from services.bg_removal import warm_up_model
        warm_up_model()
    except Exception as e:
        logging.warning(f"rembg warm-up skipped: {e}")

    yield

    # Shutdown: Close database connection
    if database_url:
        try:
            from db.database import close_db
            await close_db()
            logging.info("Database connection closed")
        except Exception as e:
            logging.warning(f"Error closing database: {e}")


# Create FastAPI app
app = FastAPI(
    title="Style Inspo API",
    description="AI-powered personal styling assistant API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
# When allow_credentials=True, must specify exact origins (not "*")
CORS_ORIGINS = [
    "http://localhost:3003",  # Local frontend
    "http://localhost:3000",  # Alternate local port
    "https://styleinspo.vercel.app",  # Production (legacy)
    "https://peichin.me",  # Production (custom domain)
    "https://www.peichin.me",  # Production (custom domain www)
    "https://styling-agent.peichin.me",  # Production (styling-agent subdomain)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api import wardrobe, outfits, user, consider_buying, jobs, visualization, sms, auth, analysis
from primitives import primitives_router

# Register routers - existing API
app.include_router(wardrobe.router, prefix="/api", tags=["wardrobe"])
app.include_router(outfits.router, prefix="/api", tags=["outfits"])
app.include_router(user.router, prefix="/api", tags=["users"])
app.include_router(consider_buying.router, prefix="/api", tags=["consider_buying"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(visualization.router, prefix="/api", tags=["visualization"])

# Register primitives router - agent-first architecture
# Coexists with /api/* via Strangler Fig pattern
app.include_router(primitives_router, prefix="/primitives", tags=["primitives"])

# Register SMS router - Twilio webhook for text-based styling
app.include_router(sms.router, prefix="/api/sms", tags=["sms"])

# Register auth router - magic link authentication
app.include_router(auth.router, prefix="/api", tags=["auth"])

# Register analysis router - daily usage analysis
app.include_router(analysis.router, prefix="/api", tags=["analysis"])

# Register agent-web router - agent-powered outfit generation for web
from api import agent_web
app.include_router(agent_web.router, prefix="/api", tags=["agent_web"])

# Register agent API router - REST endpoint for agent-to-agent calls
from api import agent_api
app.include_router(agent_api.router, prefix="/api", tags=["agent_api"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Style Inspo API is running"}


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


