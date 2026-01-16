"""
Visualization Service

Provides outfit visualization through AI image generation providers.
Supports multiple providers (Runway ML, Fashn.ai, etc.) via factory pattern.

Quick start:
    from services.visualization import VisualizationProviderFactory, ImageGenerationRequest

    factory = VisualizationProviderFactory()
    provider = factory.create_provider("runway")

    if provider.is_configured():
        request = ImageGenerationRequest(
            garment_images=["path/to/item1.jpg", "path/to/item2.jpg"],
            prompt_text="Black turtleneck, high-waisted jeans",
            style_profile={"three_words": {...}},
            mode="model"
        )
        result = provider.generate_image(request)

        if result.success:
            print(f"Generated: {result.image_url}")
"""

from .factory import VisualizationProviderFactory
from .providers.base import (
    ImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult
)

__all__ = [
    'VisualizationProviderFactory',
    'ImageGenerationProvider',
    'ImageGenerationRequest',
    'ImageGenerationResult',
]