"""
Visualization Manager

Orchestrates outfit visualization generation using AI providers (Runway ML, etc.).
Handles fetching user data, calling providers, and storing results permanently.
"""

import logging
import os
import requests
from typing import Dict
from io import BytesIO

from services.storage_manager import StorageManager
from services.saved_outfits_manager import SavedOutfitsManager
from services.user_profile_manager import UserProfileManager
from .factory import VisualizationProviderFactory
from .providers.base import ImageGenerationRequest

logger = logging.getLogger(__name__)


class VisualizationManager:
    """
    Manages outfit visualization generation workflow.

    Responsibilities:
    - Fetch outfit and user data
    - Generate visualizations with user-specific model descriptors
    - Download and store visualization images permanently
    - Update outfit records with visualization URLs
    """

    def __init__(self, user_id: str):
        """
        Initialize VisualizationManager for a specific user.

        Args:
            user_id: User identifier
        """
        self.user_id = user_id
        storage_type = os.getenv("STORAGE_TYPE", "local")
        self.storage = StorageManager(storage_type=storage_type, user_id=user_id)
        self.outfit_manager = SavedOutfitsManager(user_id=user_id)
        self.profile_manager = UserProfileManager(user_id=user_id)
        self.provider_factory = VisualizationProviderFactory()

    def visualize_outfit(self, outfit_id: str, provider_name: str = "runway") -> Dict:
        """
        Generate visualization for a saved outfit.

        Workflow:
        1. Fetch outfit data
        2. Fetch user's model descriptor from profile
        3. Prepare ImageGenerationRequest with garment images
        4. Generate with provider (returns temporary URL)
        5. Download image from temporary URL
        6. Upload to permanent storage
        7. Update outfit with permanent URL
        8. Return result

        Args:
            outfit_id: ID of the saved outfit to visualize
            provider_name: Visualization provider (default: "runway")

        Returns:
            Dict with:
                - success: bool
                - image_url: str (permanent storage URL)
                - generation_time: float
                - provider: str
                - metadata: dict

        Raises:
            ValueError: If outfit not found or provider not available
            Exception: If visualization generation fails
        """
        logger.info(f"Starting visualization for outfit {outfit_id}, user {self.user_id}")

        # 1. Fetch outfit
        outfit = self.outfit_manager.get_outfit_by_id(outfit_id)
        if not outfit:
            raise ValueError(f"Outfit {outfit_id} not found for user {self.user_id}")

        logger.info(f"Fetched outfit {outfit_id}")

        # 2. Fetch user's model descriptor
        profile = self.profile_manager.get_profile(self.user_id)
        model_descriptor = profile.get('model_descriptor', '') if profile else ''

        logger.info(f"User model descriptor: {'set' if model_descriptor else 'not set'}")

        # 3. Prepare request
        outfit_data = outfit['outfit_data']
        outfit_items = outfit_data.get('items', [])

        # Extract garment image paths (Runway API accepts max 3 reference images)
        garment_images = [item.get('image_path') for item in outfit_items if item.get('image_path')][:3]

        # Fallback for SMS-saved outfits (legacy format with image_urls)
        if not garment_images:
            garment_images = outfit_data.get('image_urls', [])[:3]

        if not garment_images:
            raise ValueError(f"Outfit {outfit_id} has no garment images")

        if len(outfit_items) > 3:
            logger.info(f"Outfit has {len(outfit_items)} items, using first 3 images for visualization")

        # Build prompt text from item names
        item_names = [item.get('name', '') for item in outfit_items if item.get('name')]
        prompt_text = ", ".join(item_names)

        request = ImageGenerationRequest(
            garment_images=garment_images,
            prompt_text=prompt_text,
            style_profile=profile or {},
            styling_notes=outfit_data.get('styling_notes', ''),
            mode="model"  # Using relatable model, not personal photo
        )

        logger.info(f"Prepared request with {len(garment_images)} images")

        # 4. Generate with provider (returns temporary URL)
        provider = self.provider_factory.create_provider(provider_name)

        if not provider:
            raise ValueError(f"Provider {provider_name} not found")

        if not provider.is_configured():
            raise ValueError(f"Provider {provider_name} not configured (missing API key)")

        logger.info(f"Calling {provider.get_provider_name()} provider...")
        result = provider.generate_image(request, model_descriptor=model_descriptor)

        if not result.success:
            raise Exception(f"Visualization failed: {result.error_message}")

        logger.info(f"Provider returned temporary URL: {result.image_url[:50]}...")

        # 5. Download from temporary URL
        logger.info("Downloading image from temporary URL...")
        response = requests.get(result.image_url, timeout=30)
        response.raise_for_status()
        image_data = response.content

        logger.info(f"Downloaded {len(image_data)} bytes")

        # 6. Upload to permanent storage
        viz_filename = f"visualizations/{outfit_id}.jpg"
        logger.info(f"Uploading to permanent storage: {viz_filename}")

        # Wrap bytes in BytesIO for file-like interface
        image_file = BytesIO(image_data)
        permanent_url = self.storage.save_file(
            file_obj=image_file,
            filename=viz_filename
        )

        logger.info(f"Permanent URL: {permanent_url}")

        # 7. Update outfit with permanent URL
        self.outfit_manager.update_outfit_visualization(outfit_id, permanent_url)

        logger.info(f"Updated outfit {outfit_id} with visualization URL")

        # 8. Return result
        return {
            'success': True,
            'image_url': permanent_url,  # Permanent URL, not temporary
            'generation_time': result.generation_time,
            'provider': result.provider,
            'metadata': result.metadata
        }

    def visualize_from_images(self, garment_images: list, provider_name: str = "runway") -> Dict:
        """
        Generate visualization directly from image URLs (for SMS flow).

        Unlike visualize_outfit(), this doesn't require a saved outfit.
        Used when we have image URLs but no outfit_id (e.g., SMS collage).

        Args:
            garment_images: List of garment image URLs (max 3 used)
            provider_name: Visualization provider (default: "runway")

        Returns:
            Dict with:
                - visualization_url: str (permanent storage URL)
                - success: bool
                - generation_time: float
        """
        import uuid

        logger.info(f"Starting visualization from {len(garment_images)} images for user {self.user_id}")

        if not garment_images:
            logger.warning("No garment images provided")
            return {"success": False, "error": "No garment images"}

        # Limit to 3 images (Runway API limit)
        garment_images = garment_images[:3]

        # Fetch user's model descriptor
        profile = self.profile_manager.get_profile(self.user_id)
        model_descriptor = profile.get('model_descriptor', '') if profile else ''

        if not model_descriptor:
            logger.warning(f"User {self.user_id} has no model descriptor, using default")
            model_descriptor = "A person wearing the outfit"

        logger.info(f"Model descriptor: {model_descriptor[:50]}...")

        # Build request
        request = ImageGenerationRequest(
            garment_images=garment_images,
            prompt_text="",  # No specific items, just visualize what's in images
            style_profile=profile or {},
            styling_notes="",
            mode="model"
        )

        # Generate with provider
        provider = self.provider_factory.create_provider(provider_name)

        if not provider or not provider.is_configured():
            logger.warning(f"Provider {provider_name} not available")
            return {"success": False, "error": f"Provider {provider_name} not available"}

        logger.info(f"Calling {provider.get_provider_name()} provider...")
        result = provider.generate_image(request, model_descriptor=model_descriptor)

        if not result.success:
            logger.error(f"Visualization failed: {result.error_message}")
            return {"success": False, "error": result.error_message}

        logger.info(f"Provider returned temporary URL")

        # Download from temporary URL
        response = requests.get(result.image_url, timeout=30)
        response.raise_for_status()
        image_data = response.content

        # Compress image to reduce file size (prevents Twilio timeout on large files)
        from PIL import Image
        img = Image.open(BytesIO(image_data))
        # Resize to max 1080px on longest side (good for mobile, much smaller file)
        max_size = 1080
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        # Compress with quality=75 (good balance of size vs quality)
        compressed = BytesIO()
        img.save(compressed, format='JPEG', quality=75, optimize=True)
        compressed.seek(0)
        image_data = compressed.read()

        # Upload to permanent storage with unique ID
        viz_id = str(uuid.uuid4())[:8]
        viz_filename = f"visualizations/sms_{viz_id}.jpg"

        image_file = BytesIO(image_data)
        permanent_url = self.storage.save_file(
            file_obj=image_file,
            filename=viz_filename
        )

        logger.info(f"Visualization saved: {permanent_url}")

        return {
            'success': True,
            'visualization_url': permanent_url,
            'generation_time': result.generation_time,
            'provider': result.provider
        }
