"""
Visualization Provider Base Interface

Unified interface for outfit visualization providers (Runway ML, Fashn.ai, etc.)
Supports both AI-generated styling inspiration and virtual try-on.

Provider Swapping:
- Easy to add new providers by implementing ImageGenerationProvider
- Each provider interprets fields based on their capabilities
- Manager layer handles provider selection based on use case

Future extensibility notes:
- provider_specific_params field reserved for provider-unique options
- Consider adding supports_feature() method if providers diverge significantly
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


@dataclass
class ImageGenerationRequest:
    """
    Universal request structure for outfit visualization providers.

    Fields:
    - garment_images: Required - paths/URLs to garment photos (provider max varies)
    - prompt_text: Optional - text description of desired output
    - style_profile: Optional - Style Inspo style profile dict (three_words, daily_emotion)
    - styling_notes: Optional - how to style/combine items
    - user_photo: Optional - path/URL to user's photo for virtual try-on
    - mode: Optional - "model" (generic) or "personal" (user photo) - provider-specific
    - provider_specific_params: Optional - provider-unique parameters
    """
    garment_images: List[str]
    prompt_text: Optional[str] = None
    style_profile: Optional[Dict] = None
    styling_notes: Optional[str] = None
    user_photo: Optional[str] = None
    mode: str = "model"  # "model" or "personal"
    provider_specific_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageGenerationResult:
    """
    Universal result structure from visualization providers.

    Fields:
    - success: Whether generation succeeded
    - image_url: Generated image URL (temporary or permanent)
    - error_message: Error details if success=False
    - generation_time: Seconds taken to generate
    - provider: Provider name for analytics/logging
    - metadata: Provider-specific metadata (model used, etc.)
    """
    success: bool
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ImageGenerationProvider(ABC):
    """
    Abstract base class for outfit visualization providers.

    All providers must implement:
    - is_configured(): Check API credentials availability
    - generate_image(): Generate visualization (handles async internally)
    - get_provider_name(): Return provider name for logging

    Example implementations:
    - RunwayProvider: AI styling inspiration with relatable models
    - FashnProvider: Virtual try-on with user photo
    - ReplicateProvider: Various models via Replicate API
    """

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if provider is configured with necessary credentials.

        Returns:
            True if API keys/config are available, False otherwise
        """
        pass

    @abstractmethod
    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """
        Generate outfit visualization image.

        Providers handle async operations internally (polling, webhooks, etc.)
        and return final result.

        Args:
            request: ImageGenerationRequest with garment images and parameters

        Returns:
            ImageGenerationResult with success status and image URL or error
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Return provider name for logging and analytics.

        Returns:
            Provider name (e.g., "Runway ML", "Fashn.ai")
        """
        pass
