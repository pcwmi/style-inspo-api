"""
Visualization Manager

Orchestrates outfit visualization generation using AI providers (Runway ML, etc.).
Handles fetching user data, calling providers, and storing results permanently.

Multi-Slot Collage Strategy (Feb 2026):
Instead of compressing all items into 1 collage (346px/item), we split items across
all 3 Runway reference slots with smaller collages (525px/item). A/B testing showed
52% higher per-item resolution produces noticeably better fidelity.

Distribution: 4→2+2, 5→2+2+1, 6→2+2+2, 7→2+2+3, 8+→3+3+2
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

# Collage settings
CANVAS_SIZE = 1080  # Square canvas for Runway
BACKGROUND = (240, 240, 240)  # Neutral gray
PADDING = 10


def _download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL and return PIL Image."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, BACKGROUND)
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
    cell_size = (CANVAS_SIZE - (cols + 1) * PADDING) // cols

    # Create canvas
    canvas = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), BACKGROUND)

    # Place images
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break

        row = idx // cols
        col = idx % cols

        cropped = _crop_to_fill(img, cell_size)

        x = PADDING + col * (cell_size + PADDING)
        y = PADDING + row * (cell_size + PADDING)

        canvas.paste(cropped, (x, y))

    return canvas


def generate_slot_collage(image_urls: List[str]) -> Optional[Image.Image]:
    """
    Generate a collage for a single Runway slot (1-3 items).

    Layout adapts to item count:
    - 1 item: centered, 700px
    - 2 items: side by side, 525px each
    - 3 items: 1x3 row, 346px each

    Canvas: 1080x1080 (Runway native)
    """
    images = []
    for url in image_urls[:3]:  # Max 3 items per slot
        img = _download_image(url)
        if img:
            images.append(img)

    if not images:
        return None

    num_images = len(images)
    canvas = Image.new('RGB', (CANVAS_SIZE, CANVAS_SIZE), BACKGROUND)

    if num_images == 1:
        # Single item: centered, large
        cell_size = 700
        img = _crop_to_fill(images[0], cell_size)
        x = (CANVAS_SIZE - cell_size) // 2
        y = (CANVAS_SIZE - cell_size) // 2
        canvas.paste(img, (x, y))

    elif num_images == 2:
        # 2 items side by side: 525px each
        cell_size = (CANVAS_SIZE - 3 * PADDING) // 2
        y = (CANVAS_SIZE - cell_size) // 2
        for idx, img in enumerate(images):
            cropped = _crop_to_fill(img, cell_size)
            x = PADDING + idx * (cell_size + PADDING)
            canvas.paste(cropped, (x, y))

    else:  # 3 items
        # 3 items in a row: 346px each
        cell_size = (CANVAS_SIZE - 4 * PADDING) // 3
        y = (CANVAS_SIZE - cell_size) // 2
        for idx, img in enumerate(images):
            cropped = _crop_to_fill(img, cell_size)
            x = PADDING + idx * (cell_size + PADDING)
            canvas.paste(cropped, (x, y))

    return canvas


def generate_multi_slot_collages(image_urls: List[str]) -> List[Image.Image]:
    """
    Distribute items across up to 3 Runway slots for maximum fidelity.

    Distribution strategy (fills 3 slots, puts extras in last slot):
    - 4 items: 2 + 2 (2 collages)
    - 5 items: 2 + 2 + 1 (3 collages)
    - 6 items: 2 + 2 + 2 (3 collages)
    - 7 items: 2 + 2 + 3 (3 collages)
    - 8+ items: 3 + 3 + rest (3 collages)

    Returns list of PIL Images (max 3).
    """
    n = len(image_urls)

    if n <= 3:
        # Just use individual images (no collaging needed)
        collages = []
        for url in image_urls:
            img = _download_image(url)
            if img:
                # Create single-item collage for consistency
                collage = generate_slot_collage([url])
                if collage:
                    collages.append(collage)
        return collages

    # Determine distribution
    if n == 4:
        distribution = [2, 2]
    elif n == 5:
        distribution = [2, 2, 1]
    elif n == 6:
        distribution = [2, 2, 2]
    elif n == 7:
        distribution = [2, 2, 3]
    else:  # 8+
        distribution = [3, 3, n - 6]  # First two get 3, last gets remainder

    collages = []
    idx = 0
    for count in distribution:
        slot_urls = image_urls[idx:idx + count]
        collage = generate_slot_collage(slot_urls)
        if collage:
            collages.append(collage)
        idx += count

    return collages[:3]  # Max 3 for Runway


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

        # Multi-slot strategy: distribute items across up to 3 Runway slots
        # This gives 52% higher per-item resolution (525px vs 346px)
        if len(all_garment_images) > 3:
            logger.info(f"Outfit has {len(all_garment_images)} items, using MULTI-SLOT collages")
            collages = generate_multi_slot_collages(all_garment_images)

            if collages:
                # Upload each collage to S3
                garment_images = []
                for i, collage in enumerate(collages):
                    collage_buffer = BytesIO()
                    collage.save(collage_buffer, format='JPEG', quality=90)
                    collage_buffer.seek(0)

                    collage_filename = f"collage_{uuid.uuid4().hex[:8]}_{i+1}.jpg"
                    collage_url = self.storage.save_file(collage_buffer, f"visualizations/{collage_filename}")
                    garment_images.append(collage_url)
                    logger.info(f"Collage {i+1}/{len(collages)} uploaded: {collage_url}")

                logger.info(f"Using {len(garment_images)} multi-slot collages")
            else:
                logger.warning("Multi-slot collage generation failed, falling back to first 3 images")
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

        For 4+ items, uses multi-slot collage strategy to maximize fidelity:
        - 4 items: 2+2 across 2 slots
        - 5 items: 2+2+1 across 3 slots
        - 6 items: 2+2+2 across 3 slots
        - 7 items: 2+2+3 across 3 slots

        Args:
            garment_images: List of garment image URLs (all items supported)
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

        # Store original images for reference
        original_images = garment_images

        # Multi-slot strategy: distribute items across up to 3 Runway slots
        # This gives 52% higher per-item resolution (525px vs 346px)
        if len(garment_images) > 3:
            logger.info(f"Using MULTI-SLOT: creating collages from {len(garment_images)} items")
            collages = generate_multi_slot_collages(garment_images)

            if collages:
                # Upload each collage to S3
                garment_images = []
                for i, collage in enumerate(collages):
                    collage_buffer = BytesIO()
                    collage.save(collage_buffer, format='JPEG', quality=90)
                    collage_buffer.seek(0)

                    collage_filename = f"collage_{uuid.uuid4().hex[:8]}_{i+1}.jpg"
                    collage_url = self.storage.save_file(collage_buffer, f"visualizations/{collage_filename}")
                    garment_images.append(collage_url)
                    logger.info(f"Collage {i+1}/{len(collages)} uploaded: {collage_url}")

                logger.info(f"Using {len(garment_images)} multi-slot collages")
            else:
                logger.warning("Multi-slot collage generation failed, falling back to first 3 images")
                garment_images = original_images[:3]
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
