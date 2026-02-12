"""
Visualization Manager

Orchestrates outfit visualization generation using AI providers (Runway ML, etc.).
Handles fetching user data, calling providers, and storing results permanently.

Pre-Composite Strategy (Feb 2026):
Instead of sending 3 individual images to Runway (which loses items in 5-7 piece outfits),
we generate a flat-lay collage of ALL items and send that as a single reference image.
A/B testing showed pre-composite works slightly better for multi-item outfits.
"""

import logging
import os
import uuid
import requests
from typing import Dict, List, Optional
from io import BytesIO
from PIL import Image

from services.storage_manager import StorageManager
from services.saved_outfits_manager import SavedOutfitsManager
from services.user_profile_manager import UserProfileManager
from .factory import VisualizationProviderFactory
from .providers.base import ImageGenerationRequest

logger = logging.getLogger(__name__)

# Pre-composite flat-lay settings
FLATLAY_CANVAS_SIZE = 1080  # Square canvas for Runway
FLATLAY_BACKGROUND = (240, 240, 240)  # Neutral gray
FLATLAY_PADDING = 10


def _download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL and return PIL Image."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, FLATLAY_BACKGROUND)
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        return img
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return None


def _crop_to_fill(img: Image.Image, target_size: int) -> Image.Image:
    """Crop and resize image to fill target square."""
    width_ratio = target_size / img.width
    height_ratio = target_size / img.height
    scale = max(width_ratio, height_ratio)

    new_width = int(img.width * scale)
    new_height = int(img.height * scale)
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    left = (new_width - target_size) // 2
    top = (new_height - target_size) // 2
    return resized.crop((left, top, left + target_size, top + target_size))


def generate_flatlay_collage(image_urls: List[str]) -> Optional[Image.Image]:
    """
    Generate a flat-lay collage of ALL outfit items.

    Pre-composite strategy: instead of sending 3 individual images to Runway,
    we create a single collage showing all items. Runway can parse this and
    translate it to a worn outfit, and we don't lose items.

    Layout: Adaptive grid based on item count
    Canvas: 1080x1080 (Runway native)
    """
    images = []
    for url in image_urls:
        img = _download_image(url)
        if img:
            images.append(img)

    if not images:
        return None

    num_images = len(images)

    # Calculate grid size
    if num_images <= 3:
        cols, rows = num_images, 1
    elif num_images <= 4:
        cols, rows = 2, 2
    elif num_images <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 3, 3

    # Calculate cell size
    cell_size = (FLATLAY_CANVAS_SIZE - (cols + 1) * FLATLAY_PADDING) // cols

    # Create canvas
    canvas = Image.new('RGB', (FLATLAY_CANVAS_SIZE, FLATLAY_CANVAS_SIZE), FLATLAY_BACKGROUND)

    # Place images
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        cropped = _crop_to_fill(img, cell_size)

        x = FLATLAY_PADDING + col * (cell_size + FLATLAY_PADDING)
        y = FLATLAY_PADDING + row * (cell_size + FLATLAY_PADDING)

        canvas.paste(cropped, (x, y))

    return canvas


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

        # 1. Fetch outfit with enriched images from wardrobe
        outfit = self.outfit_manager.get_outfit_by_id(outfit_id, enrich_with_current_images=True)
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

        # Extract ALL garment image paths
        all_garment_images = [item.get('image_path') for item in outfit_items if item.get('image_path')]

        # Fallback for SMS-saved outfits (legacy format with image_urls)
        if not all_garment_images:
            all_garment_images = outfit_data.get('image_urls', [])

        if not all_garment_images:
            raise ValueError(f"Outfit {outfit_id} has no garment images")

        # Pre-composite strategy: create flat-lay collage for outfits with 4+ items
        if len(all_garment_images) > 3:
            logger.info(f"Outfit has {len(all_garment_images)} items, using PRE-COMPOSITE flat-lay")
            flatlay = generate_flatlay_collage(all_garment_images)

            if flatlay:
                # Upload collage to S3 and use as single reference
                flatlay_buffer = BytesIO()
                flatlay.save(flatlay_buffer, format='JPEG', quality=90)
                flatlay_buffer.seek(0)

                flatlay_filename = f"flatlay_{uuid.uuid4().hex[:8]}.jpg"
                flatlay_url = self.storage.save_file(flatlay_buffer, f"visualizations/{flatlay_filename}")
                logger.info(f"Flat-lay uploaded: {flatlay_url}")

                garment_images = [flatlay_url]
            else:
                logger.warning("Flat-lay generation failed, falling back to first 3 images")
                garment_images = all_garment_images[:3]
        else:
            garment_images = all_garment_images
            logger.info(f"Outfit has {len(garment_images)} items, using individual images")

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

    def visualize_from_images(self, garment_images: list, provider_name: str = "runway", styling_notes: str = "") -> Dict:
        """
        Generate visualization directly from image URLs (for SMS flow).

        Unlike visualize_outfit(), this doesn't require a saved outfit.
        Used when we have image URLs but no outfit_id (e.g., SMS collage).

        Args:
            garment_images: List of garment image URLs (max 3 used)
            provider_name: Visualization provider (default: "runway")
            styling_notes: Optional styling hint for Runway (e.g., "sweater draped over shoulders")

        Returns:
            Dict with:
                - visualization_url: str (permanent storage URL)
                - success: bool
                - generation_time: float
        """
        logger.info(f"Starting visualization from {len(garment_images)} images for user {self.user_id}")

        if not garment_images:
            logger.warning("No garment images provided")
            return {"success": False, "error": "No garment images"}

        # Pre-composite strategy: create flat-lay collage of ALL items
        # This ensures we don't lose items in 5-7 piece outfits
        use_precomposite = len(garment_images) > 3

        if use_precomposite:
            logger.info(f"Using PRE-COMPOSITE: creating flat-lay of {len(garment_images)} items")
            flatlay = generate_flatlay_collage(garment_images)

            if flatlay:
                # Upload collage to S3 and use as single reference
                flatlay_buffer = BytesIO()
                flatlay.save(flatlay_buffer, format='JPEG', quality=90)
                flatlay_buffer.seek(0)

                flatlay_filename = f"flatlay_{uuid.uuid4().hex[:8]}.jpg"
                flatlay_url = self.storage.save_file(flatlay_buffer, f"visualizations/{flatlay_filename}")
                logger.info(f"Flat-lay uploaded: {flatlay_url}")

                # Use single flatlay as reference
                garment_images = [flatlay_url]
            else:
                logger.warning("Flat-lay generation failed, falling back to smart selection")
                garment_images = garment_images[:2] + [garment_images[-1]]
        else:
            logger.info(f"Using all {len(garment_images)} images for visualization")

        # Fetch user's model descriptor
        profile = self.profile_manager.get_profile(self.user_id)
        model_descriptor = profile.get('model_descriptor', '') if profile else ''

        if not model_descriptor:
            logger.warning(f"User {self.user_id} has no model descriptor, using default")
            model_descriptor = "A person wearing the outfit"

        logger.info(f"Model descriptor: {model_descriptor[:50]}...")
        if styling_notes:
            logger.info(f"Styling notes for Runway: {styling_notes[:80]}...")

        # Build request
        request = ImageGenerationRequest(
            garment_images=garment_images,
            prompt_text="",  # No specific items, just visualize what's in images
            style_profile=profile or {},
            styling_notes=styling_notes,  # Pass styling hint to Runway prompt
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
