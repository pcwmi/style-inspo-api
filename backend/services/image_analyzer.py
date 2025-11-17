"""
Image Analysis for Clothing Items
Provides both mock and GPT-4V implementations for analyzing wardrobe photos.
"""

import os
import json
import base64
import random
import time
import logging
from io import BytesIO
from PIL import Image
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Register HEIF/HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC support optional

class ImageAnalyzer(ABC):
    """Abstract base class for image analysis implementations"""

    @abstractmethod
    def analyze_clothing_item(self, image_file) -> Dict[str, str]:
        """Analyze clothing item and return detailed metadata"""
        pass

class MockImageAnalyzer(ImageAnalyzer):
    """Mock implementation for testing and fallback"""

    def analyze_clothing_item(self, image_file) -> Dict[str, str]:
        """Return realistic mock data for testing"""

        # Sample mock responses
        mock_items = [
            {
                "name": "White cotton crew neck t-shirt",
                "category": "tops",
                "colors": "white",
                "cut": "classic crew neck, short sleeves",
                "texture": "soft cotton jersey",
                "style": "casual minimalist",
                "fit": "relaxed fit",
                "brand": None,
                "trend_status": "classic timeless staple",
                "styling_notes": "Versatile basic that pairs with everything. Perfect foundation piece for layering or wearing solo with jeans or trousers."
            },
            {
                "name": "Black leather ankle boots",
                "category": "shoes",
                "colors": "black",
                "cut": "pointed toe, block heel",
                "texture": "smooth leather with slight sheen",
                "style": "edgy minimalist",
                "fit": "structured, fitted",
                "brand": None,
                "trend_status": "classic with trending pointed toe detail",
                "styling_notes": "Statement shoe that elevates any outfit. Works with dresses, jeans, or tailored pieces for instant sophistication."
            },
            {
                "name": "High-waisted wide leg jeans",
                "category": "bottoms",
                "colors": "medium blue denim",
                "cut": "high-waisted, wide leg silhouette",
                "texture": "structured denim with slight stretch",
                "style": "vintage-inspired casual",
                "fit": "fitted at waist, flowing through legs",
                "brand": None,
                "trend_status": "trending - popular among Gen-Z influencers",
                "styling_notes": "Flattering silhouette that elongates legs. Perfect for creating effortless cool-girl looks with crop tops or tucked-in blouses."
            }
        ]

        # Return random mock item
        return random.choice(mock_items)

class GPTVisionAnalyzer(ImageAnalyzer):
    """GPT-4V implementation for detailed fashion analysis"""

    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
        except Exception as e:
            raise Exception(f"Failed to initialize OpenAI client: {str(e)}")

    def encode_image(self, image_file) -> Tuple[str, Dict[str, float]]:
        """Convert image file to base64 string for API with timing"""
        timings = {}
        start_total = time.time()

        if hasattr(image_file, 'seek'):
            image_file.seek(0)

        # Image loading
        start_load = time.time()
        image = Image.open(image_file)
        timings['image_load'] = time.time() - start_load

        # Format conversion
        start_convert = time.time()
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        timings['format_conversion'] = time.time() - start_convert

        # Resizing
        start_resize = time.time()
        original_size = image.size
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        timings['resize'] = time.time() - start_resize
        timings['size_reduction'] = f"{original_size} -> {image.size}"

        # Base64 encoding
        start_encode = time.time()
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        timings['base64_encoding'] = time.time() - start_encode

        timings['total_preprocessing'] = time.time() - start_total

        return base64_image, timings

    def analyze_clothing_item(self, image_file) -> Dict[str, str]:
        """Use GPT-4V to analyze clothing item and return detailed metadata"""

        start_total = time.time()
        timings = {}

        try:
            # Image preprocessing
            base64_image, preprocessing_timings = self.encode_image(image_file)
            timings.update(preprocessing_timings)

            # Create detailed prompt for fashion analysis with sub_category inference
            prompt = """
            Analyze this clothing item as a professional fashion stylist would. Focus on details that help create outfits and understand styling potential.

            Return STRICT JSON with these fields (no extra commentary):
            {
              "name": "Clear descriptive name (e.g. 'Burgundy cable-knit oversized sweater')",
              "category": "One of: tops, bottoms, dresses, outerwear, footwear, accessories, bags",
              "sub_category": "Granular type based on what you SEE (examples: belt, scarf, necklace, earrings, rings, hat, sunglasses, boots, sneakers, loafers, heels, sandals, trousers, culottes, jeans, skirt, shorts, tee, blouse, shirt, knit, tank, camisole, blazer, cardigan, coat, jacket, tote, crossbody, clutch)",
              "colors": "Dominant colors/patterns (e.g. 'navy blue', 'black and white stripes', 'floral with pink roses')",
              "cut": "Design/silhouette (e.g. 'cropped', 'A-line', 'wide-leg', 'boyfriend style')",
              "design_details": "Distinctive features: cutouts, slits, keyholes, hardware, embellishments, straps, ties; 'none' if none",
              "texture": "Materials/fabric feel (e.g. 'smooth leather', 'chunky knit', 'distressed denim')",
              "style": "Aesthetic/vibe (e.g. 'minimalist chic', 'boho vintage', 'edgy street style')",
              "fit": "How it sits on the body (e.g. 'fitted', 'loose', 'oversized', 'structured', 'flowy')",
              "brand": "Any visible brand from tags/labels/logos; null if none",
              "trend_status": "'trendy' or 'classic' with 1 short clause of context",
              "styling_notes": "2 sentences on styling potential",
              "attributes": {"material": "optional", "hardware": "optional", "heel_height": "optional", "silhouette": "optional"},
              "confidence": {"sub_category": 0.0, "category": 0.0}
            }

            - Infer sub_category visually. If uncertain, choose the closest likely type and lower confidence.
            - Keep category broad and consistent with sub_category (e.g., belt => accessories, boots => footwear).
            """

            # API call timing
            start_api = time.time()
            response = self.client.chat.completions.create(
                model="gpt-4o",  # GPT-4 with vision
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600,
                temperature=0.1  # Low temperature for consistent analysis
            )
            timings['api_call'] = time.time() - start_api

            # Token usage tracking
            usage = response.usage
            timings['tokens'] = {
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens
            }

            # Calculate approximate cost (GPT-4o pricing as of 2024)
            prompt_cost = usage.prompt_tokens * 0.005 / 1000  # $0.005 per 1K prompt tokens
            completion_cost = usage.completion_tokens * 0.015 / 1000  # $0.015 per 1K completion tokens
            timings['estimated_cost'] = round(prompt_cost + completion_cost, 4)

            # JSON parsing timing
            start_parse = time.time()
            analysis_text = response.choices[0].message.content

            # Extract JSON from response (handle potential markdown formatting)
            if '```json' in analysis_text:
                json_start = analysis_text.find('```json') + 7
                json_end = analysis_text.find('```', json_start)
                analysis_text = analysis_text[json_start:json_end].strip()
            elif '{' in analysis_text and '}' in analysis_text:
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1
                analysis_text = analysis_text[json_start:json_end]

            analysis = json.loads(analysis_text)
            timings['json_parsing'] = time.time() - start_parse

            # Ensure all required fields are present
            required_fields = ['name', 'category', 'sub_category', 'colors', 'cut', 'design_details', 'texture', 'style', 'fit', 'brand', 'trend_status', 'styling_notes', 'attributes', 'confidence']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = 'Not specified' if field not in ['attributes', 'confidence'] else ({ } if field == 'attributes' else {'sub_category': 0.0, 'category': 0.0})

            # Final timing calculations
            timings['total_analysis'] = time.time() - start_total

            # Log detailed timing for analytics
            logger.info(f"GPT-4V Analysis Timing: {timings}")

            # Add timing info to analysis for UI display
            analysis['_timing_info'] = timings

            return analysis

        except Exception as e:
            print(f"GPT-4V analysis failed: {str(e)}")
            return self._get_fallback_analysis()

    def _get_fallback_analysis(self) -> Dict[str, str]:
        """Fallback analysis if GPT-4V fails"""
        return {
            'name': 'Clothing Item',
            'category': 'tops',
            'colors': 'Unable to detect',
            'cut': 'Unable to detect',
            'texture': 'Unable to detect',
            'style': 'casual',
            'fit': 'Unable to detect',
            'brand': None,
            'trend_status': 'Unable to determine',
            'styling_notes': 'GPT-4V analysis failed. Please add details manually for best styling results.'
        }

    def test_connection(self) -> bool:
        """Test if OpenAI API connection works"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"API connection test failed: {str(e)}")
            return False

# Factory function
def create_image_analyzer(use_real_ai: bool = False) -> ImageAnalyzer:
    """
    Factory function to create appropriate image analyzer

    Args:
        use_real_ai: If True, uses GPT-4V. If False, uses mock analyzer.

    Returns:
        ImageAnalyzer instance
    """
    if use_real_ai:
        try:
            analyzer = GPTVisionAnalyzer()
            # Test connection
            if analyzer.test_connection():
                print("✅ GPT-4V analyzer ready")
                return analyzer
            else:
                print("⚠️  GPT-4V connection failed, falling back to mock")
                return MockImageAnalyzer()
        except Exception as e:
            print(f"⚠️  GPT-4V initialization failed: {str(e)}, using mock")
            return MockImageAnalyzer()
    else:
        print("🎭 Using mock analyzer")
        return MockImageAnalyzer()