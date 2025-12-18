"""
Configuration and environment variables
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings from environment variables"""
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    # Support both S3_BUCKET_NAME (original) and AWS_S3_BUCKET (alternative)
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET_NAME", "style-inspo-wardrobe")
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # "local" or "s3"
    
    # Redis (for RQ job queue)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Runway API (optional)
    RUNWAY_API_KEY: Optional[str] = os.getenv("RUNWAY_API_KEY")
    RUNWAY_MODEL_DESCRIPTOR: Optional[str] = os.getenv("RUNWAY_MODEL_DESCRIPTOR")
    
    # API Configuration
    API_V1_PREFIX: str = "/api"
    
    # Prompt configuration
    PROMPT_VERSION: str = os.getenv("PROMPT_VERSION", "baseline_v1")
    
    @property
    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)
    
    @property
    def is_redis_configured(self) -> bool:
        return bool(self.REDIS_URL and self.REDIS_URL != "redis://localhost:6379/0")


settings = Settings()


def get_settings() -> Settings:
    """Get application settings (singleton pattern for test compatibility)"""
    return settings


