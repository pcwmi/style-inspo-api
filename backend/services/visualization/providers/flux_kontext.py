"""
Flux Kontext Pro Provider

Implementation of ImageGenerationProvider for Black Forest Labs' FLUX.1 Kontext [pro]
via fal.ai API. Uses image editing approach — takes a base image and edits garments onto it.

Different from Runway/Flux 2 Pro: Kontext edits an existing image rather than generating
from scratch. This could mean better garment preservation since it's modifying, not imagining.

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


class FluxKontextProvider(ImageGenerationProvider):
    """
    FLUX.1 Kontext [pro] Provider via fal.ai.

    Image editing model — takes one input image and edits it based on prompt.
    For outfit visualization: we send a collage of garments and ask it to
    generate a person wearing them.

    Single input image, so we use the same pre-composite collage approach.
    """

    MAX_REFERENCE_IMAGES = 1  # Kontext takes a single input image

    def __init__(self):
        self.api_key = os.getenv('FAL_KEY')
        self.model_id = "fal-ai/flux-pro/kontext"

    def is_configured(self) -> bool:
        return self.api_key is not None

    def get_provider_name(self) -> str:
        return "Flux Kontext Pro"

    def generate_image(self, request: ImageGenerationRequest, model_descriptor: str = None, model: str = None) -> ImageGenerationResult:
        """
        Generate outfit visualization using Flux Kontext Pro.

        Takes the first garment image (or pre-composited collage) and edits it
        into a person wearing the outfit.
        """
        if not self.is_configured():
            return ImageGenerationResult(
                success=False,
                error_message="FAL_KEY not configured.",
                provider="Flux Kontext Pro"
            )

        try:
            start_time = time.time()

            # Set FAL_KEY for fal_client
            os.environ['FAL_KEY'] = self.api_key

            # Build prompt
            descriptor = model_descriptor or ""
            prompt = self._create_prompt(request, descriptor)
            logger.info(f"Flux Kontext prompt ({len(prompt)} chars): {prompt[:200]}...")

            # Use first garment image (or collage)
            if not request.garment_images:
                return ImageGenerationResult(
                    success=False,
                    error_message="No garment images provided",
                    provider="Flux Kontext Pro"
                )

            image_url = request.garment_images[0]
            logger.info(f"Input image: {image_url[:80]}...")

            # Submit to fal.ai
            handler = fal_client.submit(
                self.model_id,
                arguments={
                    "prompt": prompt,
                    "image_url": image_url,
                    "num_images": 1,
                    "guidance_scale": 3.5,
                    "output_format": "jpeg",
                },
            )

            result = handler.get()
            generation_time = time.time() - start_time

            # Extract image URL from result
            if result and 'images' in result and len(result['images']) > 0:
                output_url = result['images'][0].get('url') or result['images'][0].get('uri', '')
                logger.info(f"Flux Kontext generation complete in {generation_time:.1f}s")

                return ImageGenerationResult(
                    success=True,
                    image_url=output_url,
                    generation_time=generation_time,
                    provider="Flux Kontext Pro",
                    metadata={
                        "model": self.model_id,
                        "seed": result.get('seed'),
                    }
                )
            else:
                return ImageGenerationResult(
                    success=False,
                    error_message=f"No images in response: {result}",
                    generation_time=generation_time,
                    provider="Flux Kontext Pro"
                )

        except Exception as e:
            logger.error(f"Flux Kontext error: {e}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time if 'start_time' in dir() else None,
                provider="Flux Kontext Pro"
            )

    def _create_prompt(self, request: ImageGenerationRequest, model_descriptor: str = "") -> str:
        """Create prompt for Flux Kontext outfit editing."""
        item_names = request.prompt_text if request.prompt_text else "the outfit shown"

        descriptor_block = f"{model_descriptor}\n\n" if model_descriptor else ""

        prompt = (
            f"{descriptor_block}"
            f"Transform this flat-lay of clothing items into a fashion editorial photo "
            f"of a confident woman wearing the outfit: {item_names}.\n\n"
            f"Show a full-body shot of ONE person wearing ALL the garments shown. "
            f"Preserve the exact colors, patterns, and details of each garment. "
        )

        if request.styling_notes:
            prompt += f"Styling: {request.styling_notes[:150]}\n"

        prompt += "Fashion photography, editorial style, clean background, professional lighting."

        return prompt.strip()
