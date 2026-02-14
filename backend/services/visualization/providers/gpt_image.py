"""
GPT Image Provider

Implementation of ImageGenerationProvider for OpenAI's GPT Image 1 API.
Supports multi-image input (up to 10 reference images) for fashion try-on visualization.

Key advantage over Runway: accepts up to 10 input images (vs Runway's 3),
so we can skip collaging and send individual garment photos for better fidelity.

Configuration:
- OPENAI_API_KEY (required, already used for outfit generation)
"""

import os
import io
import time
import base64
import logging
import requests
from typing import Dict, List, Optional
from PIL import Image
from openai import OpenAI
from .base import (
    ImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult
)

logger = logging.getLogger(__name__)


class GPTImageProvider(ImageGenerationProvider):
    """
    OpenAI GPT Image 1 Provider.

    Uses images.edit() with multiple input images for outfit visualization.
    Max 10 reference images — enough for most outfits without collaging.
    """

    MAX_REFERENCE_IMAGES = 10

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def is_configured(self) -> bool:
        return self.api_key is not None

    def get_provider_name(self) -> str:
        return "GPT Image"

    def generate_image(self, request: ImageGenerationRequest, model_descriptor: str = None, model: str = None) -> ImageGenerationResult:
        """
        Generate outfit visualization using OpenAI GPT Image 1.

        Uses images.edit() with multiple garment photos as input.
        """
        if not self.is_configured():
            return ImageGenerationResult(
                success=False,
                error_message="OpenAI API key not configured.",
                provider="GPT Image"
            )

        try:
            start_time = time.time()

            # Build prompt
            descriptor = model_descriptor or ""
            prompt = self._create_prompt(request, descriptor)
            logger.info(f"GPT Image prompt ({len(prompt)} chars): {prompt[:200]}...")

            # Download garment images as file-like objects
            image_files = self._prepare_images(request)
            if not image_files:
                return ImageGenerationResult(
                    success=False,
                    error_message="No valid garment images to process",
                    provider="GPT Image"
                )

            logger.info(f"Sending {len(image_files)} images to GPT Image")

            # Call OpenAI images.edit with multiple inputs
            quality = "low"  # "low" for speed, "high" for max quality
            result = self.client.images.edit(
                model="gpt-image-1",
                image=image_files,
                prompt=prompt,
                size="1024x1536",  # Portrait
                quality=quality,
            )

            generation_time = time.time() - start_time

            # Extract base64 image data
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            # Save to temp file and return as data URL
            # (Visualization manager will download and store permanently)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                img = Image.open(io.BytesIO(image_bytes))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(f, format='JPEG', quality=90)
                temp_path = f.name

            logger.info(f"GPT Image generation complete in {generation_time:.1f}s")

            return ImageGenerationResult(
                success=True,
                image_url=temp_path,  # Local temp file path
                generation_time=generation_time,
                provider="GPT Image",
                metadata={
                    "model": "gpt-image-1",
                    "num_input_images": len(image_files),
                    "size": "1024x1536",
                    "temp_file": True,
                }
            )

        except Exception as e:
            logger.error(f"GPT Image error: {e}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time if 'start_time' in dir() else None,
                provider="GPT Image"
            )

    def _create_prompt(self, request: ImageGenerationRequest, model_descriptor: str = "") -> str:
        """Create prompt for GPT Image outfit visualization."""
        # Build outfit description
        item_names = request.prompt_text if request.prompt_text else ""

        descriptor_block = f"{model_descriptor}\n\n" if model_descriptor else ""

        prompt = (
            f"{descriptor_block}"
            f"A single confident woman, full-body shot, wearing an outfit composed of: {item_names}.\n\n"
            f"The input images show the individual garment pieces. "
            f"Generate a fashion editorial photo of the model wearing ALL of these items together as a complete outfit.\n\n"
        )

        if request.styling_notes:
            prompt += f"Styling: {request.styling_notes[:200]}\n\n"

        prompt += (
            "ONE person only. Full body from head to toe. "
            "Use each garment exactly once. Do not add extra items. "
            "Fashion photography, editorial style, clean background, professional lighting."
        )

        return prompt.strip()

    def _prepare_images(self, request: ImageGenerationRequest) -> List:
        """Download garment images and return as file-like objects for OpenAI API.

        OpenAI requires files with proper names for mimetype detection.
        We convert all images to JPEG and wrap in named BytesIO objects.
        """
        image_files = []

        for i, image_path in enumerate((request.garment_images or [])[:self.MAX_REFERENCE_IMAGES]):
            try:
                if image_path.startswith(('http://', 'https://')):
                    response = requests.get(image_path, timeout=15)
                    response.raise_for_status()
                    image_data = response.content
                else:
                    with open(image_path, 'rb') as f:
                        image_data = f.read()

                # Convert to JPEG to ensure consistent mimetype
                img = Image.open(io.BytesIO(image_data))
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                buf.seek(0)
                buf.name = f"garment_{i}.jpg"  # OpenAI needs filename for mimetype

                image_files.append(buf)
            except Exception as e:
                logger.warning(f"Failed to load image {image_path}: {e}")
                continue

        return image_files
