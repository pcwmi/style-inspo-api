"""
Runway ML Provider

Implementation of ImageGenerationProvider for Runway Gen-4 Image API.
Supports AI-generated styling inspiration with relatable model descriptors.

Validated findings (Jan 2026):
- Relatable model descriptor > personal photo (avoids uncanny valley)
- Relatable model > standard shopping model (better "I could pull this off" feeling)
- Garment fidelity is approximate (fundamental model limitation)
- Best for inspiration, not exact virtual try-on

Configuration:
- RUNWAY_API_KEY (required)
- RUNWAY_MODEL_DESCRIPTOR (optional, for relatable models)
- RUNWAY_PROMPT_STYLE (optional, "control" or "strong_anchoring")
"""

import os
import requests
import time
import base64
import logging
from typing import Dict, List, Optional
from .base import (
    ImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult
)

logger = logging.getLogger(__name__)


class RunwayProvider(ImageGenerationProvider):
    """
    Runway ML Gen-4 Image API Provider.

    Features:
    - Text-to-image with reference images (max 3)
    - Relatable model descriptors for demographic representation
    - Async task polling (30s average generation time)
    - Base64 image encoding for local files and URLs

    Limitations:
    - Garment fidelity approximate (designed for character consistency)
    - 1000 character prompt limit
    - 3 reference image maximum
    """

    def __init__(self):
        self.api_key = os.getenv('RUNWAY_API_KEY')
        self.base_url = "https://api.dev.runwayml.com/v1"
        self.model = "gen4_image"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }

        # Relatable model descriptor (validated in A/B tests)
        # Example: "Model: ~163 cm, ~150 lb, Asian woman, dark wavy chest-length hair..."
        self.model_descriptor: str = os.getenv("RUNWAY_MODEL_DESCRIPTOR", "").strip()

        # Prompt style: "control" (default) or "strong_anchoring"
        # Note: strong_anchoring validated NOT to improve garment fidelity
        self.prompt_style: str = os.getenv("RUNWAY_PROMPT_STYLE", "control").strip()

    def is_configured(self) -> bool:
        """Check if Runway API key is available."""
        return self.api_key is not None

    def get_provider_name(self) -> str:
        """Return provider name for logging."""
        return "Runway ML"

    def generate_image(self, request: ImageGenerationRequest, model_descriptor: str = None) -> ImageGenerationResult:
        """
        Generate outfit visualization using Runway Gen-4 Image API.

        Process:
        1. Create prompt with model descriptor and garment mentions
        2. Encode reference images to base64
        3. Submit async task to Runway
        4. Poll for completion (max 120s timeout)
        5. Return image URL

        Args:
            request: ImageGenerationRequest with garment images and parameters
            model_descriptor: Optional user-level model descriptor (overrides env var)

        Returns:
            ImageGenerationResult with success status and image URL or error
        """
        if not self.is_configured():
            return ImageGenerationResult(
                success=False,
                error_message="Runway API key not configured. Set RUNWAY_API_KEY environment variable.",
                provider="Runway ML"
            )

        try:
            # Use provided descriptor, fallback to env var, then empty string
            descriptor = model_descriptor or os.getenv("RUNWAY_MODEL_DESCRIPTOR", "")

            # Create prompt
            prompt = self._create_outfit_prompt(request, model_descriptor=descriptor)

            logger.info(f"Runway prompt (length: {len(prompt)}): {prompt[:200]}...")

            # Build payload
            payload = {
                "model": self.model,
                "promptText": prompt,
                "ratio": "1920:1080",  # Landscape
            }

            # Add reference images
            reference_images = self._prepare_reference_images(request)
            if reference_images:
                payload["referenceImages"] = reference_images
                logger.info(f"Added {len(reference_images)} reference images")

            # Submit task
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/text_to_image",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            logger.info(f"Runway API response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                task_id = data.get('id')

                if not task_id:
                    return ImageGenerationResult(
                        success=False,
                        error_message=f"No task ID in response: {data}",
                        generation_time=time.time() - start_time,
                        provider="Runway ML"
                    )

                logger.info(f"Runway task created: {task_id}, polling...")

                # Poll for completion
                try:
                    completed_task = self._poll_task(task_id, timeout=120)
                    image_url = self._extract_image_url(completed_task)

                    generation_time = time.time() - start_time
                    logger.info(f"Runway generation complete in {generation_time:.1f}s")

                    return ImageGenerationResult(
                        success=True,
                        image_url=image_url,
                        generation_time=generation_time,
                        provider="Runway ML",
                        metadata={
                            "task_id": task_id,
                            "model": self.model,
                            "model_descriptor_used": bool(descriptor),
                            "user_level_descriptor": bool(model_descriptor)
                        }
                    )
                except Exception as e:
                    logger.error(f"Runway polling failed: {e}")
                    return ImageGenerationResult(
                        success=False,
                        error_message=str(e),
                        generation_time=time.time() - start_time,
                        provider="Runway ML"
                    )
            else:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return ImageGenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=time.time() - start_time,
                    provider="Runway ML"
                )

        except requests.exceptions.Timeout:
            logger.error("Runway API timeout")
            return ImageGenerationResult(
                success=False,
                error_message="API request timed out. Please try again.",
                provider="Runway ML"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Runway network error: {e}")
            return ImageGenerationResult(
                success=False,
                error_message=f"Network error: {str(e)}",
                provider="Runway ML"
            )
        except Exception as e:
            logger.error(f"Runway unexpected error: {e}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                provider="Runway ML"
            )

    def _poll_task(self, task_id: str, timeout: int) -> Dict:
        """
        Poll Runway task for completion.

        Args:
            task_id: Runway task ID
            timeout: Max seconds to poll

        Returns:
            Completed task data with image URL

        Raises:
            TimeoutError: If task doesn't complete within timeout
            Exception: If task fails
        """
        start_time = time.time()
        poll_interval = 2

        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get('status', '').upper()

                logger.debug(f"Runway task {task_id} status: {status}")

                if 'SUCCEED' in status or status == 'COMPLETED':
                    return task_data
                elif 'FAIL' in status or status == 'ERROR':
                    raise Exception(f"Task failed: {task_data}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Task {task_id} timed out after {timeout}s")

    def _extract_image_url(self, task_data: Dict) -> str:
        """
        Extract image URL from completed task data.

        Args:
            task_data: Runway task completion response

        Returns:
            Image URL

        Raises:
            ValueError: If no image URL found in response
        """
        # Try multiple possible field names
        for field in ['output', 'url', 'result', 'imageUrl', 'image_url']:
            if field in task_data:
                output = task_data[field]
                if isinstance(output, list) and len(output) > 0:
                    return output[0]
                elif isinstance(output, str):
                    return output

        raise ValueError(f"No image URL found in task data: {task_data}")

    def _create_outfit_prompt(self, request: ImageGenerationRequest, model_descriptor: str = None) -> str:
        """
        Create detailed prompt for Runway Gen-4 Image.

        Includes:
        - Model descriptor (if provided)
        - Garment mentions with @garment_N tags
        - Style profile (three_words, daily_emotion)
        - Styling notes
        - Duplication guard

        Args:
            request: ImageGenerationRequest with outfit details
            model_descriptor: Optional model descriptor (user-level or env var)

        Returns:
            Formatted prompt string (max 1000 chars for Runway)
        """
        # Extract style information
        three_words = request.style_profile.get('three_words', {}) if request.style_profile else {}
        daily_emotion = request.style_profile.get('daily_emotion', {}) if request.style_profile else {}

        # Build style description
        style_desc = ""
        if three_words.get('current') and three_words.get('aspirational'):
            style_desc = f"Style: {three_words['current']} (aspiring to {three_words['aspirational']}, feeling {three_words.get('feeling', 'confident')})"

        # Build mood description
        mood_desc = ""
        if daily_emotion.get('feeling_now') and daily_emotion.get('want_to_feel'):
            mood_desc = f"Mood: {daily_emotion['feeling_now']} → {daily_emotion['want_to_feel']}"

        # Create outfit description with @garment_N tags
        outfit_items = [s.strip() for s in (request.prompt_text.split(", ") if request.prompt_text else [])]
        num_reference = len(request.garment_images) if request.garment_images else 0
        outfit_with_mentions: List[str] = []

        for i, item in enumerate(outfit_items):
            if i < num_reference:
                # Tag with reference image
                descriptor = f" ({item})" if item else ""
                outfit_with_mentions.append(f"@garment_{i+1}{descriptor}")
            else:
                outfit_with_mentions.append(item)

        # Include extra tags if more reference images than described items
        if num_reference > len(outfit_items):
            for j in range(len(outfit_items), num_reference):
                outfit_with_mentions.append(f"@garment_{j+1}")

        outfit_description = ", ".join(outfit_with_mentions)

        # Build styling section
        styling_section = ""
        if request.styling_notes:
            styling_section = f"Styling: {request.styling_notes}\n\n"

        # Duplication guard (prevent Runway from adding extra accessories)
        duplication_guard = (
            "Use each referenced garment exactly once. "
            "Do not duplicate accessories or add extra items."
        )

        # Build prompt based on mode
        if request.mode == "personal" and request.user_photo:
            # Personal mode: use @person tag
            prompt = (
                f"@person wearing {outfit_description}.\n\n"
                f"{styling_section}"
                f"{style_desc}\n"
                f"{mood_desc}\n\n"
                f"{duplication_guard} "
                "Fashion photography, editorial style, clean background, professional lighting. "
                "Preserve the person's appearance."
            )
        else:
            # Model mode: use provided descriptor (user-level or env var)
            descriptor_block = f"{model_descriptor}\n\n" if model_descriptor else ""

            prompt = (
                f"{descriptor_block}"
                f"A confident woman wearing {outfit_description}.\n\n"
                f"{styling_section}"
                f"{style_desc}\n"
                f"{mood_desc}\n\n"
                f"{duplication_guard} "
                "Fashion photography, editorial style, clean background, professional lighting."
            )

        return prompt.strip()

    def _prepare_reference_images(self, request: ImageGenerationRequest) -> List[Dict]:
        """
        Prepare reference images for Runway API.

        Handles:
        - Local file paths (read from disk)
        - HTTP(S) URLs (download and encode)
        - User photo (@person tag)
        - Garment images (@garment_N tags)

        Args:
            request: ImageGenerationRequest with image paths/URLs

        Returns:
            List of reference image dicts with base64 data URLs and tags
        """
        reference_images = []

        # Add user photo first if in personal mode
        if request.mode == "personal" and request.user_photo:
            try:
                image_data = self._fetch_image_data(request.user_photo)
                data_url = self._encode_image_to_data_url(image_data, request.user_photo)

                reference_images.append({
                    "uri": data_url,
                    "tag": "person"
                })
                logger.info("Added user photo as @person reference")
            except Exception as e:
                logger.warning(f"Failed to process user photo {request.user_photo}: {e}")

        # Add garment images
        if request.garment_images:
            for i, image_path in enumerate(request.garment_images):
                try:
                    image_data = self._fetch_image_data(image_path)
                    data_url = self._encode_image_to_data_url(image_data, image_path)

                    reference_images.append({
                        "uri": data_url,
                        "tag": f"garment_{i+1}"
                    })
                except Exception as e:
                    logger.warning(f"Failed to process garment image {image_path}: {e}")
                    continue

        return reference_images

    def _fetch_image_data(self, image_path: str) -> bytes:
        """
        Fetch image data from local path or URL.

        Args:
            image_path: Local file path or HTTP(S) URL

        Returns:
            Image data as bytes

        Raises:
            Exception: If image cannot be fetched
        """
        if image_path.startswith(('http://', 'https://')):
            # Download from URL
            response = requests.get(image_path, timeout=30)
            response.raise_for_status()
            return response.content
        else:
            # Read from local file
            with open(image_path, 'rb') as f:
                return f.read()

    def _encode_image_to_data_url(self, image_data: bytes, image_path: str) -> str:
        """
        Encode image data to base64 data URL.

        Args:
            image_data: Image bytes
            image_path: Original path (for MIME type detection)

        Returns:
            Data URL string (data:image/jpeg;base64,...)
        """
        base64_data = base64.b64encode(image_data).decode('utf-8')

        # Detect MIME type from extension
        _, ext = os.path.splitext(image_path.lower())
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')

        return f"data:{mime_type};base64,{base64_data}"
