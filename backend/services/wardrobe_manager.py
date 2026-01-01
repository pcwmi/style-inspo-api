"""
Wardrobe Manager - Core business logic (no Streamlit dependencies)
Handles wardrobe item CRUD operations and metadata management
"""

import os
import json
import io
from PIL import Image, ImageOps
import uuid
from typing import Dict, List, Optional
import datetime
import logging

from services.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class WardrobeManager:
    """Manages wardrobe items with photo uploads and metadata"""

    def __init__(self, base_path: str = "wardrobe_photos", user_id: str = "default"):
        self.user_id = user_id
        
        # Initialize storage manager (local or S3 based on env var)
        # Normalize storage_type: handle empty strings or invalid values
        storage_type = os.getenv("STORAGE_TYPE", "local")
        if not storage_type or storage_type.strip() == "":
            storage_type = "local"
        self.storage = StorageManager(storage_type=storage_type, user_id=user_id)
        
        # Scope base_path by user_id for multi-user support
        self.base_path = os.path.join(base_path, user_id)
        self.items_path = os.path.join(self.base_path, "items")
        self.metadata_file = os.path.join(self.base_path, "wardrobe_metadata.json")

        # Ensure directories exist (only for local storage)
        if storage_type == "local":
            os.makedirs(self.items_path, exist_ok=True)

        # Load existing wardrobe data
        self.wardrobe_data = self.load_wardrobe_data()

    def load_wardrobe_data(self) -> Dict:
        """Load wardrobe metadata from JSON file"""
        try:
            data = self.storage.load_json("wardrobe_metadata.json")
            
            # Handle legacy format conversion
            if "regular_wear" in data or "styling_challenges" in data:
                logger.info("Migrating wardrobe data to new format...")
                migrated_data = self._convert_legacy_format(data)
                # Save the migrated data back to file
                self.wardrobe_data = migrated_data
                self.save_wardrobe_data()
                logger.info("Wardrobe data migrated successfully!")
                return migrated_data
            return data
        except Exception as e:
            logger.error(f"Error loading wardrobe data: {e}")
            return {
                "items": [],
                "schema_version": "2.0",
                "last_updated": None
            }

    def save_wardrobe_data(self):
        """Save wardrobe metadata to JSON file"""
        self.storage.save_json(self.wardrobe_data, "wardrobe_metadata.json")

    def add_wardrobe_item(self,
                         uploaded_file,
                         analysis_data: Dict,
                         is_styling_challenge: bool = False,
                         challenge_reason: str = "") -> Optional[Dict]:
        """Add a new wardrobe item and return structured metadata"""

        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)

            # Generate unique filename
            unique_filename = f"{uuid.uuid4().hex}.jpg"  # Always save as JPEG for S3

            # Load and process image
            image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(image)  # Fix orientation before saving

            # Convert RGBA to RGB for JPEG compatibility (PNG with transparency -> JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = rgb_image
            elif image.mode != 'RGB':
                # Convert any other mode to RGB
                image = image.convert('RGB')

            # Save image using storage manager (returns URL for S3, path for local)
            save_path = self.storage.save_image(image, unique_filename)

            # Create structured item metadata
            item_data = {
                "id": uuid.uuid4().hex[:12],  # Clean, shorter ID
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
                    "styling_notes": analysis_data.get('styling_notes', ''),
                    "design_details": analysis_data.get('design_details', 'solid/plain')
                },
                "structured_attrs": {
                    "subcategory": analysis_data.get('sub_category', 'Unknown'),
                    "fabric": analysis_data.get('fabric', 'unknown'),
                    "silhouette": analysis_data.get('fit', 'Unknown').lower() if analysis_data.get('fit') else 'unknown',
                    "sleeve_length": analysis_data.get('sleeve_length'),
                    "waist_level": analysis_data.get('waist_level'),
                },
                "usage_metadata": {
                    "is_styling_challenge": is_styling_challenge,
                    "challenge_reason": challenge_reason if is_styling_challenge else "",
                    "tags": [],
                    "wear_frequency": "unknown",
                    "favorite": False,
                    "seasonal": None
                },
                "system_metadata": {
                    "image_path": save_path,  # Will be URL for S3, path for local
                    "original_filename": getattr(uploaded_file, 'name', 'unknown'),
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_updated": datetime.datetime.now().isoformat(),
                    "file_size": os.path.getsize(save_path) if os.path.exists(save_path) and not save_path.startswith("http") else 0,
                    "source": "unknown",
                    "processed_at": None
                }
            }

            # Add to items array
            # CRITICAL: Reload data to prevent race condition when multiple workers run concurrently
            self.wardrobe_data = self.load_wardrobe_data()
            self.wardrobe_data["items"].append(item_data)
            self.wardrobe_data["last_updated"] = datetime.datetime.now().isoformat()
            self.save_wardrobe_data()

            return item_data

        except Exception as e:
            logger.error(f"Error adding item: {str(e)}")
            return None

    def update_wardrobe_item(self, item_id: str, updates: Dict) -> Optional[Dict]:
        """Update metadata for an existing wardrobe item"""
        try:
            items = self.wardrobe_data.get("items", [])
            
            for item in items:
                if item.get("id") == item_id:
                    # Update styling details
                    if "styling_details" not in item:
                        item["styling_details"] = {}
                    
                    # Allow updating specific fields in styling_details
                    allowed_fields = [
                        "name", "category", "sub_category", "colors",
                        "cut", "texture", "style", "fit", "brand",
                        "trend_status", "styling_notes", "design_details"
                    ]
                    
                    for field in allowed_fields:
                        if field in updates:
                            item["styling_details"][field] = updates[field]
                    
                    # Handle fabric update (stored in structured_attrs)
                    if "fabric" in updates:
                        if "structured_attrs" not in item:
                            item["structured_attrs"] = {}
                        item["structured_attrs"]["fabric"] = updates["fabric"]
                            
                    # Update system metadata
                    if "system_metadata" not in item:
                        item["system_metadata"] = {}
                    
                    item["system_metadata"]["last_updated"] = datetime.datetime.now().isoformat()
                    self.wardrobe_data["last_updated"] = datetime.datetime.now().isoformat()
                    
                    self.save_wardrobe_data()
                    return item
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating item {item_id}: {str(e)}")
            return None

    def get_wardrobe_items(self, filter_type: str = "all") -> List[Dict]:
        """Get wardrobe items with flexible filtering"""
        items = self.wardrobe_data.get("items", [])

        if filter_type == "all":
            return items
        elif filter_type == "styling_challenges":
            return [item for item in items if item.get("usage_metadata", {}).get("is_styling_challenge", False)]
        elif filter_type == "regular_wear":
            return [item for item in items if not item.get("usage_metadata", {}).get("is_styling_challenge", False)]
        else:
            return items

    def delete_wardrobe_item(self, item_id: str) -> bool:
        """Delete a wardrobe item by ID"""
        try:
            items = self.wardrobe_data.get("items", [])
            item_to_remove = None

            for item in items:
                current_item_id = item.get("id", "unknown")
                if current_item_id == item_id:
                    item_to_remove = item
                    break

            if item_to_remove:
                # Remove image file (only if local - S3 handles its own cleanup)
                image_path = item_to_remove.get("system_metadata", {}).get("image_path") or item_to_remove.get("image_path")
                if image_path and not image_path.startswith("http") and os.path.exists(image_path):
                    os.remove(image_path)

                # Remove from data
                items.remove(item_to_remove)
                self.wardrobe_data["last_updated"] = datetime.datetime.now().isoformat()
                self.save_wardrobe_data()
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            return False

    def toggle_styling_challenge(self, item_id: str, is_challenge: bool = None, challenge_reason: str = "") -> bool:
        """Toggle or set styling challenge status for an item"""
        try:
            # Handle legacy format (regular_wear/styling_challenges arrays)
            if "regular_wear" in self.wardrobe_data or "styling_challenges" in self.wardrobe_data:
                return self._toggle_legacy_format(item_id, is_challenge, challenge_reason)
            
            # Handle new format (unified items array)
            items = self.wardrobe_data.get("items", [])

            for item in items:
                current_item_id = item.get("id", "unknown")
                if current_item_id == item_id:
                    # Toggle if no explicit value provided
                    if is_challenge is None:
                        current_status = item.get("usage_metadata", {}).get("is_styling_challenge", False)
                        is_challenge = not current_status

                    # Update usage metadata
                    if "usage_metadata" not in item:
                        item["usage_metadata"] = {}

                    item["usage_metadata"]["is_styling_challenge"] = is_challenge
                    item["usage_metadata"]["challenge_reason"] = challenge_reason if is_challenge else ""

                    # Update timestamp
                    if "system_metadata" not in item:
                        item["system_metadata"] = {}
                    item["system_metadata"]["last_updated"] = datetime.datetime.now().isoformat()
                    self.wardrobe_data["last_updated"] = datetime.datetime.now().isoformat()

                    self.save_wardrobe_data()
                    return True

            return False

        except Exception as e:
            logger.error(f"Error updating styling challenge status: {str(e)}")
            return False

    def rotate_item_image(self, item_id: str, degrees: int = 90) -> Optional[str]:
        """
        Rotate an item's image by the specified degrees (clockwise).
        Returns the new image path/URL if successful, None otherwise.
        """
        try:
            items = self.wardrobe_data.get("items", [])
            target_item = None

            for item in items:
                if item.get("id") == item_id:
                    target_item = item
                    break
            
            if not target_item:
                logger.error(f"Item {item_id} not found for rotation")
                return None

            # Get current image path
            current_path = target_item.get("system_metadata", {}).get("image_path")
            if not current_path:
                logger.error(f"No image path found for item {item_id}")
                return None

            # Load image using storage manager
            image_data = self.storage.load_file(current_path)
            if not image_data:
                logger.error(f"Could not load image data from {current_path}")
                return None

            # Rotate image
            from io import BytesIO
            img = Image.open(BytesIO(image_data))
            img = ImageOps.exif_transpose(img)  # Apply EXIF orientation before rotating

            # Rotate clockwise (negative angle for PIL rotate)
            # PIL rotate is counter-clockwise, so -90 is 90 degrees clockwise
            rotated_img = img.rotate(-degrees, expand=True)
            
            # Save rotated image
            # We overwrite the existing file if possible, or create a new one
            # For S3, we'll generate a new filename to avoid caching issues
            
            filename = os.path.basename(current_path)
            if self.storage.storage_type == "s3":
                # Generate new filename for cache busting
                name, ext = os.path.splitext(filename)
                # Remove old timestamp if present (simple heuristic)
                if "_" in name and len(name.split("_")[-1]) > 8:
                    name = "_".join(name.split("_")[:-1])
                
                new_filename = f"{name}_{int(datetime.datetime.now().timestamp())}{ext}"
            else:
                new_filename = filename

            new_path = self.storage.save_image(rotated_img, new_filename)
            
            # Update metadata
            if "system_metadata" not in target_item:
                target_item["system_metadata"] = {}
            
            target_item["system_metadata"]["image_path"] = new_path
            target_item["system_metadata"]["last_updated"] = datetime.datetime.now().isoformat()
            
            # If S3 and filename changed, try to delete old file
            if self.storage.storage_type == "s3" and new_path != current_path:
                try:
                    self.storage.delete_file(current_path)
                except Exception as e:
                    logger.warning(f"Failed to delete old image {current_path}: {e}")

            self.wardrobe_data["last_updated"] = datetime.datetime.now().isoformat()
            self.save_wardrobe_data()
            
            return new_path

        except Exception as e:
            logger.error(f"Error rotating item image: {str(e)}")
            return None

    def _toggle_legacy_format(self, item_id: str, is_challenge: bool = None, challenge_reason: str = "") -> bool:
        """Handle toggle for legacy format (regular_wear/styling_challenges arrays)"""
        try:
            # Find item in regular_wear array
            regular_items = self.wardrobe_data.get("regular_wear", [])
            for i, item in enumerate(regular_items):
                if item.get("id") == item_id:
                    if is_challenge is None:
                        is_challenge = True
                    
                    if is_challenge:
                        item["challenge_reason"] = challenge_reason
                        self.wardrobe_data.setdefault("styling_challenges", []).append(item)
                        self.wardrobe_data["regular_wear"].pop(i)
                    
                    self.save_wardrobe_data()
                    return True
            
            # Find item in styling_challenges array
            challenge_items = self.wardrobe_data.get("styling_challenges", [])
            for i, item in enumerate(challenge_items):
                if item.get("id") == item_id:
                    if is_challenge is None:
                        is_challenge = False
                    
                    if not is_challenge:
                        if "challenge_reason" in item:
                            del item["challenge_reason"]
                        self.wardrobe_data.setdefault("regular_wear", []).append(item)
                        self.wardrobe_data["styling_challenges"].pop(i)
                    else:
                        item["challenge_reason"] = challenge_reason
                    
                    self.save_wardrobe_data()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating legacy styling challenge status: {str(e)}")
            return False

    def _convert_legacy_format(self, legacy_data: Dict) -> Dict:
        """Convert old regular_wear/styling_challenges format to new structured format"""
        new_items = []

        # Convert regular_wear items
        for item in legacy_data.get("regular_wear", []):
            new_item = self._convert_legacy_item(item, is_styling_challenge=False)
            new_items.append(new_item)

        # Convert styling_challenges items
        for item in legacy_data.get("styling_challenges", []):
            new_item = self._convert_legacy_item(item, is_styling_challenge=True)
            new_items.append(new_item)

        return {
            "items": new_items,
            "schema_version": "2.0",
            "last_updated": datetime.datetime.now().isoformat(),
            "migrated_from": "1.0"
        }

    def _convert_legacy_item(self, legacy_item: Dict, is_styling_challenge: bool) -> Dict:
        """Convert a single legacy item to new structured format"""
        # Extract styling details
        styling_details = {
            "name": legacy_item.get("name", "Unnamed Item"),
            "category": legacy_item.get("category", "tops"),
            "sub_category": legacy_item.get("sub_category", "Unknown"),
            "colors": [legacy_item.get("colors", legacy_item.get("color", "Unknown"))] if isinstance(legacy_item.get("colors", legacy_item.get("color")), str) else legacy_item.get("colors", ["Unknown"]),
            "cut": legacy_item.get("cut", "Unknown"),
            "texture": legacy_item.get("texture", "Unknown"),
            "style": legacy_item.get("style", "casual"),
            "fit": legacy_item.get("fit", "Unknown"),
            "brand": legacy_item.get("brand"),
            "trend_status": legacy_item.get("trend_status", "Unknown"),
            "styling_notes": legacy_item.get("styling_notes", "")
        }

        # Extract usage metadata
        usage_metadata = {
            "is_styling_challenge": is_styling_challenge,
            "challenge_reason": legacy_item.get("challenge_reason", ""),
            "tags": [],
            "wear_frequency": "unknown",
            "favorite": False,
            "seasonal": None
        }

        # Extract system metadata
        system_metadata = {
            "image_path": legacy_item.get("image_path", ""),
            "original_filename": legacy_item.get("original_filename", ""),
            "created_at": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat(),
            "file_size": 0
        }

        return {
            "id": uuid.uuid4().hex[:12],
            "styling_details": styling_details,
            "usage_metadata": usage_metadata,
            "system_metadata": system_metadata
        }


