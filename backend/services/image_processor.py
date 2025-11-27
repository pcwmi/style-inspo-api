import io
from PIL import Image
import rembg
import numpy as np

class ImageProcessor:
    def __init__(self):
        pass

    def remove_background(self, image_file) -> bytes:
        """
        Remove background from an image using rembg.
        
        Args:
            image_file: A file-like object containing the image (bytes) or PIL Image
            
        Returns:
            bytes: The processed image in PNG format with transparency
        """
        # Load image
        if isinstance(image_file, bytes):
            input_image = Image.open(io.BytesIO(image_file))
        elif isinstance(image_file, Image.Image):
            input_image = image_file
        else:
            # Assume it's a file-like object
            image_file.seek(0)
            input_image = Image.open(image_file)

        # Convert to numpy array for rembg
        input_array = np.array(input_image)

        # Remove background
        output_array = rembg.remove(input_array)

        # Convert back to PIL Image
        output_image = Image.fromarray(output_array)

        # Save to bytes
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()

# Singleton instance
image_processor = ImageProcessor()
