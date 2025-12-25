"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# Wardrobe Models
class WardrobeItemResponse(BaseModel):
    """Wardrobe item response schema"""
    id: str
    styling_details: Dict[str, Any]
    usage_metadata: Dict[str, Any]
    system_metadata: Dict[str, Any]


class WardrobeResponse(BaseModel):
    """Wardrobe list response"""
    items: List[WardrobeItemResponse]
    count: int


# Outfit Generation Models
class OutfitRequest(BaseModel):
    """Request to generate outfits"""
    user_id: str
    occasions: List[str] = Field(default_factory=list)
    weather_condition: Optional[str] = None
    temperature_range: Optional[str] = None
    mode: str = Field(default="occasion", pattern="^(occasion|complete)$")
    anchor_items: Optional[List[str]] = None  # Item IDs for "complete my look" mode
    mock: bool = False
    prompt_version: Optional[str] = None  # Optional prompt version override
    include_reasoning: bool = False  # Include raw AI reasoning in response


class OutfitItem(BaseModel):
    """Single item in an outfit"""
    name: str
    category: str
    image_path: Optional[str] = None


class OutfitContext(BaseModel):
    """Context in which the outfit was generated"""
    occasions: List[str]
    weather_condition: Optional[str] = None
    temperature_range: Optional[str] = None


class OutfitCombination(BaseModel):
    """A complete outfit combination"""
    items: List[OutfitItem]
    styling_notes: str
    why_it_works: str
    confidence_level: str
    vibe_keywords: List[str]
    constitution_principles: Optional[Dict[str, Any]] = None
    context: Optional[OutfitContext] = None


class OutfitGenerationResponse(BaseModel):
    """Response when starting outfit generation"""
    job_id: str
    status: str
    estimated_time: int = 30  # seconds
    prompt_version: str  # Prompt version used for generation


# Job Status Models
class JobStatusResponse(BaseModel):
    """Job status response"""
    status: str  # "queued", "processing", "complete", "failed"
    progress: Optional[int] = None  # 0-100
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Save/Dislike Models
class SaveOutfitRequest(BaseModel):
    """Request to save an outfit"""
    user_id: str
    outfit: Dict[str, Any]
    feedback: Optional[List[str]] = None


class DislikeOutfitRequest(BaseModel):
    """Request to dislike an outfit"""
    user_id: str
    outfit: Dict[str, Any]
    reason: str


# User Profile Models
class ProfileUpdate(BaseModel):
    """User profile update request"""
    three_words: Optional[Dict[str, str]] = None
    daily_emotion: Optional[Dict[str, str]] = None


class ProfileResponse(BaseModel):
    """User profile response"""
    user_id: str
    three_words: Optional[Dict[str, str]] = None
    daily_emotion: Optional[Dict[str, str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


