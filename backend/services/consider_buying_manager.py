"""
Consider Buying Manager - Manage items user is considering purchasing
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from services.storage_manager import StorageManager
from services.image_analyzer import create_image_analyzer

logger = logging.getLogger(__name__)


def colors_are_similar(colors1: List[str], colors2: List[str]) -> bool:
    """Check if two color lists are similar"""
    # Define color families
    color_families = {
        'neutrals': ['black', 'white', 'grey', 'gray', 'charcoal', 'cream', 'beige', 'taupe', 'ivory'],
        'blues': ['navy', 'blue', 'light blue', 'denim', 'cobalt', 'royal blue'],
        'reds': ['red', 'burgundy', 'wine', 'maroon', 'pink', 'rose'],
        'greens': ['green', 'olive', 'forest', 'emerald', 'mint'],
        'yellows': ['yellow', 'gold', 'mustard', 'ochre'],
        'purples': ['purple', 'lavender', 'plum', 'violet'],
        'browns': ['brown', 'tan', 'camel', 'chocolate', 'coffee'],
    }

    # Normalize colors
    colors1_lower = [c.lower() for c in colors1]
    colors2_lower = [c.lower() for c in colors2]

    # Check for exact matches
    for color1 in colors1_lower:
        if color1 in colors2_lower:
            return True

    # Check for same family matches
    for family in color_families.values():
        family_matches_1 = [c for c in colors1_lower if c in family]
        family_matches_2 = [c for c in colors2_lower if c in family]
        if family_matches_1 and family_matches_2:
            return True

    return False


def are_items_similar(item1: Dict, item2: Dict) -> Tuple[bool, float, str]:
    """
    Check similarity based on physical attributes only

    Returns: (is_similar, similarity_score, reason)

    Similarity criteria:
    - MUST match: subcategory
    - MUST match: color (similar)
    - Score on: silhouette (30%), fabric (30%), sleeve_length/waist_level (20%)
    - Threshold: 60% or higher = similar
    """
    attrs1 = item1.get('structured_attrs', {})
    attrs2 = item2.get('structured_attrs', {})

    styling1 = item1.get('styling_details', {})
    styling2 = item2.get('styling_details', {})

    # MUST match: subcategory
    if attrs1.get('subcategory') != attrs2.get('subcategory'):
        return False, 0.0, "Different subcategory"

    # MUST match: color (similar)
    colors1 = styling1.get('colors', [])
    colors2 = styling2.get('colors', [])
    if not colors_are_similar(colors1, colors2):
        return False, 0.0, "Different colors"

    # Calculate similarity score
    score = 0.0
    matching_attrs = []

    # Silhouette (30%)
    if attrs1.get('silhouette') == attrs2.get('silhouette'):
        score += 0.3
        matching_attrs.append('silhouette')

    # Fabric (30%)
    if attrs1.get('fabric') == attrs2.get('fabric'):
        score += 0.3
        matching_attrs.append('fabric')

    # Sleeve length for tops (20%)
    if styling1.get('category') == 'tops':
        if attrs1.get('sleeve_length') == attrs2.get('sleeve_length'):
            score += 0.2
            matching_attrs.append('sleeve length')

    # Waist level for bottoms (20%)
    if styling1.get('category') == 'bottoms':
        if attrs1.get('waist_level') == attrs2.get('waist_level'):
            score += 0.2
            matching_attrs.append('waist level')

    # For other categories, give partial credit for cut similarity
    if styling1.get('category') not in ['tops', 'bottoms']:
        cut1 = styling1.get('cut', '').lower()
        cut2 = styling2.get('cut', '').lower()
        if cut1 and cut2:
            words1 = set(cut1.split())
            words2 = set(cut2.split())
            if words1 & words2:  # Any word overlap
                overlap_ratio = len(words1 & words2) / max(len(words1), len(words2))
                if overlap_ratio > 0.5:
                    score += 0.2
                    matching_attrs.append('cut details')

    # Consider similar if score >= 0.6 (60%)
    is_similar = score >= 0.6
    reason = f"Matching: {', '.join(matching_attrs)}" if matching_attrs else "No significant matches"

    return is_similar, score, reason


class ConsiderBuyingManager:
    """Manage items user is considering purchasing"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.storage = StorageManager(storage_type=os.getenv("STORAGE_TYPE", "local"), user_id=user_id)
        self.metadata_file = "consider_buying.json"
        self.decisions_file = "buying_decisions.json"

        # Load existing data
        self.consider_buying_data = self._load_consider_buying_data()
        self.decisions_data = self._load_decisions_data()

    def _load_consider_buying_data(self) -> Dict:
        """Load consider_buying.json"""
        try:
            return self.storage.load_json(self.metadata_file)
        except:
            return {"items": []}

    def _load_decisions_data(self) -> Dict:
        """Load buying_decisions.json"""
        default_data = {
            "decisions": [],
            "stats": {
                "total_considered": 0,
                "total_bought": 0,
                "total_passed": 0,
                "total_deciding_later": 0,
                "total_saved": 0.0
            }
        }
        
        try:
            data = self.storage.load_json(self.decisions_file)
            # Ensure stats key exists even if loaded from file (migration/fallback)
            if "stats" not in data:
                data["stats"] = default_data["stats"]
            if "decisions" not in data:
                data["decisions"] = default_data["decisions"]
            return data
        except:
            return default_data

    def _save_consider_buying_data(self):
        """Save consider_buying.json"""
        self.storage.save_json(self.consider_buying_data, self.metadata_file)

    def _save_decisions_data(self):
        """Save buying_decisions.json"""
        self.storage.save_json(self.decisions_data, self.decisions_file)

    def add_item(self, analysis_data: Dict, image, price: Optional[float] = None, source_url: Optional[str] = None) -> Dict:
        """
        Add item to consider_buying bucket

        Returns: item_data with id
        """
        # Generate unique ID
        item_id = f"consider_{uuid.uuid4().hex[:12]}"

        # Save image to consider_buying/ folder
        image_filename = f"{item_id}.jpg"
        # image is a SpooledTemporaryFile (UploadFile.file), so use save_file
        # But save_file doesn't support subfolder yet? 
        # Wait, I updated StorageManager to support subfolder for save_image, but did I update save_file?
        # Let me check StorageManager again.
        # I only updated save_image and _save_to_local/_save_to_s3 for images.
        # I need to update save_file too or just use save_image by opening it as PIL image.
        # Opening as PIL image is safer for validation anyway.
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            image.seek(0)  # Ensure we're at the start of the file
            pil_image = Image.open(image)
            
            # Convert RGBA to RGB if needed (for JPEG saving)
            if pil_image.mode in ('RGBA', 'P'):
                pil_image = pil_image.convert('RGB')
                
            image_path = self.storage.save_image(pil_image, image_filename, subfolder="consider_buying")
        except Exception as e:
            # Fallback for non-image files or errors?
            # For now assume it's an image as per type hint
            raise ValueError(f"Invalid image file: {e}")

        # Create item data
        item_data = {
            "id": item_id,
            "added_date": datetime.now().isoformat(),
            "status": "considering",
            "source_url": source_url,
            "price": price,
            "styling_details": {
                "name": analysis_data.get('name', 'Unnamed Item'),
                "category": analysis_data.get('category', 'tops'),
                "sub_category": analysis_data.get('sub_category', 'Unknown'),
                "colors": analysis_data.get('colors', ['Unknown']) if isinstance(analysis_data.get('colors'), list) else [analysis_data.get('colors', 'Unknown')],
                "cut": analysis_data.get('cut', 'Unknown'),
                "texture": analysis_data.get('texture', 'Unknown'),
                "style": analysis_data.get('style', 'casual'),
                "fit": analysis_data.get('fit', 'Unknown'),
                "brand": analysis_data.get('brand'),
                "trend_status": analysis_data.get('trend_status', 'Unknown'),
                "styling_notes": analysis_data.get('styling_notes', '')
            },
            "structured_attrs": {
                "subcategory": analysis_data.get('sub_category', 'Unknown'),
                "fabric": analysis_data.get('fabric', 'unknown'),
                "silhouette": analysis_data.get('fit', 'Unknown').lower() if analysis_data.get('fit') else 'unknown',
                "sleeve_length": analysis_data.get('sleeve_length'),
                "waist_level": analysis_data.get('waist_level'),
            },
            "image_path": image_path,
            "similar_items_in_wardrobe": []
        }

        # Add to consider_buying data
        self.consider_buying_data["items"].append(item_data)
        self._save_consider_buying_data()

        # Update stats
        self.decisions_data["stats"]["total_considered"] += 1
        self._save_decisions_data()

        return item_data

    def find_similar_items(self, consider_item: Dict, wardrobe_items: List[Dict]) -> List[Dict]:
        """
        Find similar items in wardrobe

        Returns: List of dicts with {item, similarity_score, reason}
        """
        similar = []

        for wardrobe_item in wardrobe_items:
            is_similar, score, reason = are_items_similar(consider_item, wardrobe_item)

            if is_similar:
                similar.append({
                    'item': wardrobe_item,
                    'similarity_score': score,
                    'reason': reason
                })

        # Sort by similarity score (highest first)
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)

        return similar[:5]  # Return top 5

    def record_decision(self, item_id: str, decision: str, reason: Optional[str] = None):
        """
        Record user's buying decision

        decision: "bought" | "passed" | "later"
        """
        # Find item in consider_buying
        item = next((i for i in self.consider_buying_data["items"] if i["id"] == item_id), None)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Record decision
        decision_record = {
            "item_id": item_id,
            "decision": decision,
            "decision_date": datetime.now().isoformat(),
            "reason": reason,
            "price_saved": item.get("price", 0) if decision == "passed" else 0
        }

        self.decisions_data["decisions"].append(decision_record)

        # Update stats
        stats = self.decisions_data["stats"]
        if decision == "bought":
            stats["total_bought"] += 1
        elif decision == "passed":
            stats["total_passed"] += 1
            stats["total_saved"] += item.get("price", 0)
        elif decision == "later":
            stats["total_deciding_later"] += 1

        self._save_decisions_data()

        # Update item status - map "later" to "considering" for UI consistency
        if decision == "later":
            item["status"] = "considering"
        else:
            item["status"] = decision
        self._save_consider_buying_data()

        return decision_record

    def get_items(self, status: Optional[str] = None) -> List[Dict]:
        """Get items, optionally filtered by status"""
        items = self.consider_buying_data.get("items", [])

        if status:
            return [i for i in items if i.get("status") == status]

        return items

    def get_stats(self) -> Dict:
        """Get buying decision stats"""
        return self.decisions_data.get("stats", {})

    def update_considering_item(self, item_id: str, updates: Dict) -> Optional[Dict]:
        """Update metadata for an existing considering item"""
        try:
            items = self.consider_buying_data.get("items", [])

            for item in items:
                if item.get("id") == item_id:
                    # Update styling details
                    if "styling_details" not in item:
                        item["styling_details"] = {}

                    # Allow updating specific fields in styling_details
                    allowed_fields = [
                        "name", "category", "sub_category", "colors",
                        "cut", "texture", "style", "fit", "brand",
                        "trend_status", "styling_notes"
                    ]

                    for field in allowed_fields:
                        if field in updates:
                            item["styling_details"][field] = updates[field]

                    # Handle fabric update (stored in structured_attrs)
                    if "fabric" in updates:
                        if "structured_attrs" not in item:
                            item["structured_attrs"] = {}
                        item["structured_attrs"]["fabric"] = updates["fabric"]

                    # Update price and source_url if provided
                    if "price" in updates:
                        item["price"] = updates["price"]
                    if "source_url" in updates:
                        item["source_url"] = updates["source_url"]

                    # Update last modified timestamp
                    item["last_updated"] = datetime.now().isoformat()

                    self._save_consider_buying_data()
                    return item

            return None

        except Exception as e:
            logger.error(f"Error updating considering item {item_id}: {str(e)}")
            return None

    def rotate_considering_item_image(self, item_id: str, degrees: int = 90) -> Optional[str]:
        """
        Rotate a considering item's image by the specified degrees (clockwise).
        Returns the new image path/URL if successful, None otherwise.
        """
        try:
            items = self.consider_buying_data.get("items", [])
            target_item = None

            for item in items:
                if item.get("id") == item_id:
                    target_item = item
                    break

            if not target_item:
                logger.error(f"Considering item {item_id} not found for rotation")
                return None

            # Get current image path
            current_path = target_item.get("image_path")
            if not current_path:
                logger.error(f"No image path found for considering item {item_id}")
                return None

            # Load image using storage manager
            image_data = self.storage.load_file(current_path, subfolder="consider_buying")
            if not image_data:
                logger.error(f"Could not load image data from {current_path}")
                return None

            # Rotate image
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(image_data))

            # Rotate clockwise (negative angle for PIL rotate)
            # PIL rotate is counter-clockwise, so -90 is 90 degrees clockwise
            rotated_img = img.rotate(-degrees, expand=True)

            # Save rotated image
            # For S3, we'll generate a new filename to avoid caching issues

            filename = os.path.basename(current_path)
            if self.storage.storage_type == "s3":
                # Generate new filename for cache busting
                name, ext = os.path.splitext(filename)
                # Remove old timestamp if present (simple heuristic)
                if "_" in name and len(name.split("_")[-1]) > 8:
                    name = "_".join(name.split("_")[:-1])

                new_filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
            else:
                new_filename = filename

            new_path = self.storage.save_image(rotated_img, new_filename, subfolder="consider_buying")

            # Update metadata
            target_item["image_path"] = new_path
            target_item["last_updated"] = datetime.now().isoformat()

            # If S3 and filename changed, try to delete old file
            if self.storage.storage_type == "s3" and new_path != current_path:
                try:
                    self.storage.delete_file(current_path, subfolder="consider_buying")
                except Exception as e:
                    logger.warning(f"Failed to delete old image {current_path}: {e}")

            self._save_consider_buying_data()

            return new_path

        except Exception as e:
            logger.error(f"Error rotating considering item image: {str(e)}")
            return None

    def delete_item(self, item_id: str):
        """Delete item from consider_buying"""
        items = self.consider_buying_data.get("items", [])
        item = next((i for i in items if i["id"] == item_id), None)

        if item:
            # Delete image
            image_path = item.get("image_path")
            if image_path:
                # TODO: Implement storage.delete_file()
                pass

            # Remove from list
            items.remove(item)
            self._save_consider_buying_data()
