"""
Flux 2 Pro Provider

Implementation of ImageGenerationProvider for Black Forest Labs' FLUX.2 [pro]
via fal.ai API. Uses multi-reference image editing for outfit visualization.

Key advantage: supports up to 9 reference images (vs Runway's 3), and you can
reference them with @ syntax in prompts for precise garment placement.

Two modes available:
- Text-to-image: "fal-ai/flux-2-pro" (no reference images)
- Multi-ref edit: "fal-ai/flux-2-pro/edit" (our mode — reference images + prompt)

Configuration:
- FAL_KEY (required)
"""

import os
import time
import logging
import fal_client
from typing import Dict, Optional
from .base import (
    ImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult
)

logger = logging.getLogger(__name__)


class Flux2ProProvider(ImageGenerationProvider):
    """
    FLUX.2 [pro] Multi-Reference Edit Provider via fal.ai.

    Uses the edit endpoint with multiple reference images (up to 9).
    Each garment image is referenced with @ syntax in the prompt.
    """

    MAX_REFERENCE_IMAGES = 9

    def __init__(self):
        self.api_key = os.getenv('FAL_KEY')
        self.model_id = "fal-ai/flux-2-pro/edit"

    def is_configured(self) -> bool:
        return self.api_key is not None

    def get_provider_name(self) -> str:
        return "Flux 2 Pro"

    def generate_image(self, request: ImageGenerationRequest, model_descriptor: str = None, model: str = None) -> ImageGenerationResult:
        """
        Generate outfit visualization using Flux 2 Pro multi-reference edit.

        Sends garment images as reference URLs with @ syntax in prompt.
        """
        if not self.is_configured():
            return ImageGenerationResult(
                success=False,
                error_message="FAL_KEY not configured.",
                provider="Flux 2 Pro"
            )

        try:
            start_time = time.time()

            # Set FAL_KEY for fal_client
            os.environ['FAL_KEY'] = self.api_key

            # Build prompt
            descriptor = model_descriptor or ""
            prompt = self._create_prompt(request, descriptor)
            logger.info(f"Flux 2 Pro prompt ({len(prompt)} chars): {prompt[:200]}...")

            # Collect image URLs (up to 9)
            image_urls = []
            for img_path in (request.garment_images or [])[:self.MAX_REFERENCE_IMAGES]:
                if img_path.startswith(('http://', 'https://')):
                    image_urls.append(img_path)
                else:
                    logger.warning(f"Flux 2 Pro requires URLs, skipping local path: {img_path}")

            if not image_urls:
                return ImageGenerationResult(
                    success=False,
                    error_message="No valid image URLs for Flux 2 Pro",
                    provider="Flux 2 Pro"
                )

            logger.info(f"Sending {len(image_urls)} reference images to Flux 2 Pro")

            # Submit to fal.ai edit endpoint
            handler = fal_client.submit(
                self.model_id,
                arguments={
                    "prompt": prompt,
                    "image_urls": image_urls,
                    "image_size": "portrait_4_3",
                    "output_format": "jpeg",
                },
            )

            result = handler.get()
            generation_time = time.time() - start_time

            # Extract image URL from result
            if result and 'images' in result and len(result['images']) > 0:
                output_url = result['images'][0].get('url') or result['images'][0].get('uri', '')
                logger.info(f"Flux 2 Pro generation complete in {generation_time:.1f}s")

                return ImageGenerationResult(
                    success=True,
                    image_url=output_url,
                    generation_time=generation_time,
                    provider="Flux 2 Pro",
                    metadata={
                        "model": self.model_id,
                        "num_reference_images": len(image_urls),
                        "seed": result.get('seed'),
                    }
                )
            else:
                return ImageGenerationResult(
                    success=False,
                    error_message=f"No images in response: {result}",
                    generation_time=generation_time,
                    provider="Flux 2 Pro"
                )

        except Exception as e:
            logger.error(f"Flux 2 Pro error: {e}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time if 'start_time' in dir() else None,
                provider="Flux 2 Pro"
            )

    def _create_prompt(self, request: ImageGenerationRequest, model_descriptor: str = "") -> str:
        """Create prompt for Flux 2 Pro multi-reference edit."""
        item_names = request.prompt_text if request.prompt_text else "the garments shown"

        descriptor_block = f"{model_descriptor}\n\n" if model_descriptor else ""

        prompt = (
            f"{descriptor_block}"
            f"A single confident woman, full-body shot, wearing an outfit composed of: {item_names}.\n\n"
            f"The reference images show the individual garment pieces. "
            f"Generate a fashion editorial photo of the model wearing ALL of these items together.\n\n"
        )

        if request.styling_notes:
            prompt += f"Styling: {request.styling_notes[:200]}\n\n"

        prompt += (
            "ONE person only. Full body from head to toe. "
            "Preserve exact colors, patterns, and textures of each garment. "
            "Do not add extra items or accessories. "
            "Fashion photography, editorial style, clean background, professional lighting."
        )

        return prompt.strip()
