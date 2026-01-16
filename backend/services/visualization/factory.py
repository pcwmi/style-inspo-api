"""
Visualization Provider Factory

Creates appropriate visualization provider based on configuration or explicit selection.
Follows same pattern as services/ai/factory.py for consistency.
"""

from typing import Optional
from .providers.base import ImageGenerationProvider


class VisualizationProviderFactory:
    """
    Factory to create visualization provider instances.

    Supports:
    - Runway ML (AI styling inspiration with relatable models)
    - Future: Fashn.ai, Replicate, etc.

    Usage:
        factory = VisualizationProviderFactory()
        provider = factory.create_provider("runway")
        if provider.is_configured():
            result = provider.generate_image(request)
    """

    @staticmethod
    def create_provider(provider_name: str = None) -> Optional[ImageGenerationProvider]:
        """
        Create provider instance.

        Returns provider even if not configured - callers should check
        is_configured() before using.

        Args:
            provider_name: "runway", "fashn", "replicate", or None for auto-detect

        Returns:
            Provider instance (may be unconfigured) or None if provider not found

        Raises:
            ImportError: If provider module not found
        """
        if provider_name == "runway" or provider_name is None:
            from .providers.runway import RunwayProvider
            return RunwayProvider()

        # Future provider implementations:
        # if provider_name == "fashn":
        #     from .providers.fashn import FashnProvider
        #     return FashnProvider()
        #
        # if provider_name == "replicate":
        #     from .providers.replicate import ReplicateProvider
        #     return ReplicateProvider()

        return None  # Provider type not found


    @staticmethod
    def get_available_providers() -> list[str]:
        """
        Return list of available provider names.

        Returns:
            List of provider name strings
        """
        return ["runway"]  # Update as new providers are added


    @staticmethod
    def get_default_provider() -> str:
        """
        Return default provider name.

        Returns:
            Default provider name
        """
        return "runway"
