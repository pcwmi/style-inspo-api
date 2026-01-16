"""
FastAPI Backend for Style Inspo
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Style Inspo API",
    description="AI-powered personal styling assistant API",
    version="1.0.0"
)

# CORS configuration
# Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api import wardrobe, outfits, user, consider_buying, jobs, visualization

# Register routers
app.include_router(wardrobe.router, prefix="/api", tags=["wardrobe"])
app.include_router(outfits.router, prefix="/api", tags=["outfits"])
app.include_router(user.router, prefix="/api", tags=["users"])
app.include_router(consider_buying.router, prefix="/api", tags=["consider_buying"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(visualization.router, prefix="/api", tags=["visualization"])


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


