"""
Screenshot Collage Module
Creates 920px-wide collages from multiple screenshots
"""

from PIL import Image, ImageDraw, ImageFont
import io
import os
import math
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from .utils import validate_image, ensure_aspect_ratio

class ScreenshotCollage:
    # itch.io inline image specifications
    MAX_WIDTH = 920
    MIN_GUTTER = 4
    MAX_GUTTER = 32
    DEFAULT_GUTTER = 12

    # Layout presets
    LAYOUTS = {
        'Grid': 'grid',
        'Masonry': 'masonry',
        'Linear': 'linear'
    }

    def __init__(self):
        pass

    def _calculate_grid_layout(self, image_count: int, target_width: int,
                              gutter: int) -> Tuple[int, int, List[Tuple[int, int]]]:
        """Calculate optimal grid layout"""
        if image_count <= 2:
            cols = image_count
            rows = 1
        elif image_count <= 4:
            cols = 2
            rows = 2
        elif image_count <= 6:
            cols = 3
            rows = 2
        elif image_count <= 9:
            cols = 3
            rows = 3
        else:
            cols = 4
            rows = math.ceil(image_count / 4)

        # Calculate cell dimensions
        total_gutter_width = (cols - 1) * gutter
        cell_width = (target_width - total_gutter_width) // cols

        # Calculate positions
        positions = []
        for row in range(rows):
            for col in range(cols):
                if len(positions) >= image_count:
                    break
                x = col * (cell_width + gutter)
                y = row * (cell_width + gutter)  # Assuming square cells
                positions.append((x, y))

        total_height = rows * cell_width + (rows - 1) * gutter

        return cell_width, total_height, positions

    def _calculate_masonry_layout(self, images: List[Image.Image], target_width: int,
                                 gutter: int, max_cols: int = 3) -> Tuple[int, List[Tuple[int, int, int, int]]]:
        """Calculate masonry layout preserving aspect ratios"""
        if not images:
            return 0, []

        # Determine number of columns
        cols = min(len(images), max_cols)
        col_width = (target_width - (cols - 1) * gutter) // cols

        # Track column heights
        col_heights = [0] * cols
        layout_rects = []

        for img in images:
            # Find shortest column
            min_col = col_heights.index(min(col_heights))

            # Calculate scaled height maintaining aspect ratio
            aspect_ratio = img.height / img.width
            scaled_height = int(col_width * aspect_ratio)

            # Position rectangle
            x = min_col * (col_width + gutter)
            y = col_heights[min_col]

            layout_rects.append((x, y, col_width, scaled_height))

            # Update column height
            col_heights[min_col] += scaled_height + gutter

        total_height = max(col_heights) - gutter  # Remove last gutter
        return total_height, layout_rects

    def _calculate_linear_layout(self, images: List[Image.Image], target_width: int,
                                gutter: int) -> Tuple[int, List[Tuple[int, int, int, int]]]:
        """Calculate linear (single column) layout"""
        if not images:
            return 0, []

        layout_rects = []
        current_y = 0

        for img in images:
            # Scale to fit width
            aspect_ratio = img.height / img.width
            scaled_height = int(target_width * aspect_ratio)

            layout_rects.append((0, current_y, target_width, scaled_height))
            current_y += scaled_height + gutter

        total_height = current_y - gutter  # Remove last gutter
        return total_height, layout_rects

    def create_collage(self, image_paths: List[str], output_path: str,
                      layout: str = 'Grid', gutter: int = DEFAULT_GUTTER,
                      max_width: int = MAX_WIDTH, add_captions: bool = False,
                      caption_height: int = 30) -> str:
        """Create screenshot collage"""
        if not image_paths:
            raise ValueError("No images provided")

        if gutter < self.MIN_GUTTER or gutter > self.MAX_GUTTER:
            gutter = self.DEFAULT_GUTTER

        # Load and validate images
        images = []
        valid_paths = []

        for path in image_paths:
            if validate_image(path):
                try:
                    img = Image.open(path)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    images.append(img)
                    valid_paths.append(path)
                except Exception:
                    continue

        if not images:
            raise ValueError("No valid images found")

        # Calculate layout
        if layout == 'Masonry':
            total_height, layout_rects = self._calculate_masonry_layout(images, max_width, gutter)
        elif layout == 'Linear':
            total_height, layout_rects = self._calculate_linear_layout(images, max_width, gutter)
        else:  # Grid
            cell_width, total_height, positions = self._calculate_grid_layout(len(images), max_width, gutter)
            # Convert positions to rects
            layout_rects = [(x, y, cell_width, cell_width) for x, y in positions]

        # Add caption space if needed
        if add_captions:
            total_height += len(images) * caption_height

        # Create collage canvas
        collage = Image.new('RGBA', (max_width, total_height), (255, 255, 255, 0))

        # Place images
        for i, (img, rect) in enumerate(zip(images, layout_rects)):
            x, y, w, h = rect

            # Resize image to fit rectangle
            img_resized = img.resize((w, h), Image.Resampling.LANCZOS)

            # Paste image
            collage.paste(img_resized, (x, y), img_resized if img_resized.mode == 'RGBA' else None)

            # Add caption if requested
            if add_captions:
                caption_y = y + h
                filename = os.path.splitext(os.path.basename(valid_paths[i]))[0]
                self._add_caption(collage, filename, x, caption_y, w, caption_height)

        # Save collage
        collage.save(output_path, 'PNG')
        return output_path

    def _add_caption(self, collage: Image.Image, text: str, x: int, y: int,
                    width: int, height: int):
        """Add caption to collage"""
        draw = ImageDraw.Draw(collage)

        # Try to load a font, fallback to default
        try:
            font = ImageFont.truetype('arial.ttf', 12)
        except:
            font = ImageFont.load_default()

        # Calculate text position (center)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2

        # Draw background rectangle
        draw.rectangle([x, y, x + width, y + height], fill=(0, 0, 0, 128))

        # Draw text
        draw.text((text_x, text_y), text, fill='white', font=font)

    def generate_preview(self, collage_data: Dict[str, Any], preview_size: Tuple[int, int]) -> Optional[bytes]:
        """Generate preview collage for GUI"""
        try:
            images = collage_data.get('images', [])
            if not images:
                return None

            layout = collage_data.get('layout', 'Grid')
            gutter = collage_data.get('gutter', self.DEFAULT_GUTTER)

            # Load preview images (smaller versions)
            preview_images = []
            for path in images[:6]:  # Limit to 6 for preview
                try:
                    img = Image.open(path)
                    # Scale down for preview
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    preview_images.append(img)
                except:
                    continue

            if not preview_images:
                return None

            # Calculate preview layout
            preview_width = preview_size[0]
            scale_factor = preview_width / self.MAX_WIDTH
            scaled_gutter = max(1, int(gutter * scale_factor))

            if layout == 'Masonry':
                total_height, layout_rects = self._calculate_masonry_layout(
                    preview_images, preview_width, scaled_gutter
                )
            elif layout == 'Linear':
                total_height, layout_rects = self._calculate_linear_layout(
                    preview_images, preview_width, scaled_gutter
                )
            else:  # Grid
                cell_width, total_height, positions = self._calculate_grid_layout(
                    len(preview_images), preview_width, scaled_gutter
                )
                layout_rects = [(x, y, cell_width, cell_width) for x, y in positions]

            # Limit height for preview
            max_preview_height = preview_size[1]
            if total_height > max_preview_height:
                scale_factor = max_preview_height / total_height
                total_height = max_preview_height
                layout_rects = [(int(x * scale_factor), int(y * scale_factor),
                               int(w * scale_factor), int(h * scale_factor))
                              for x, y, w, h in layout_rects]

            # Create preview collage
            preview = Image.new('RGBA', (preview_width, int(total_height)), (255, 255, 255, 255))

            # Place images
            for img, rect in zip(preview_images, layout_rects):
                x, y, w, h = rect
                if w > 0 and h > 0:
                    img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
                    preview.paste(img_resized, (x, y), img_resized if img_resized.mode == 'RGBA' else None)

            # Convert to bytes for PySimpleGUI
            bio = io.BytesIO()
            preview.save(bio, format='PNG')
            return bio.getvalue()

        except Exception:
            return None
