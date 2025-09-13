"""
Cover Generator Module
Generates itch.io compliant cover images (630x500, 315:250 aspect ratio)
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from PIL.ImageDraw import ImageDraw as DrawType
import io
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

from .utils import get_asset_path, ensure_aspect_ratio

class CoverGenerator:
    # itch.io cover specifications
    COVER_WIDTH = 630
    COVER_HEIGHT = 500
    ASPECT_RATIO = (315, 250)  # 1.26:1

    # Safe zones (margins from edges)
    SAFE_ZONE_MARGIN = 40
    TITLE_AREA_TOP = 60
    TITLE_AREA_HEIGHT = 120

    def __init__(self):
        self.default_fonts = self._load_default_fonts()
        self.template_backgrounds = self._load_template_backgrounds()

    def _load_default_fonts(self) -> Dict[str, str]:
        """Load available system and bundled fonts"""
        fonts = {
            'Arial': None,
            'Helvetica': None,
            'Times New Roman': None,
            'Impact': None
        }

        # Try to load system fonts first
        try:
            fonts['Arial'] = ImageFont.truetype('arial.ttf', 48)
        except:
            try:
                fonts['Arial'] = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 48)
            except:
                pass

        # Load bundled fonts from assets
        assets_fonts = get_asset_path('fonts')
        if assets_fonts.exists():
            for font_file in assets_fonts.glob('*.ttf'):
                font_name = font_file.stem
                try:
                    fonts[font_name] = str(font_file)
                except Exception:
                    pass

        return fonts

    def _load_template_backgrounds(self) -> list:
        """Load template background images"""
        backgrounds = []
        assets_bg = get_asset_path('backgrounds')
        if assets_bg.exists():
            for bg_file in assets_bg.glob('*.png'):
                backgrounds.append(str(bg_file))
        return backgrounds

    def _get_font(self, font_name: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Get font object with fallback to default"""
        try:
            if font_name in self.default_fonts and self.default_fonts[font_name]:
                if isinstance(self.default_fonts[font_name], str):
                    # Font file path
                    return ImageFont.truetype(self.default_fonts[font_name], size)
                else:
                    # Font object
                    return self.default_fonts[font_name].font_variant(size=size)
        except Exception:
            pass

        # Fallback to default font
        try:
            return ImageFont.truetype('arial.ttf', size)
        except:
            return ImageFont.load_default()

    def _create_gradient_background(self, color1: str, color2: str) -> Image.Image:
        """Create gradient background"""
        img = Image.new('RGB', (self.COVER_WIDTH, self.COVER_HEIGHT))
        draw = ImageDraw.Draw(img)

        # Convert hex colors to RGB
        if color1.startswith('#'):
            color1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
        if color2.startswith('#'):
            color2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))

        # Create vertical gradient
        for y in range(self.COVER_HEIGHT):
            ratio = y / self.COVER_HEIGHT
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, y), (self.COVER_WIDTH, y)], fill=(r, g, b))

        return img

    def _create_blurred_background(self, image_path: str) -> Image.Image:
        """Create blurred background from source image"""
        try:
            source_img = Image.open(image_path)

            # Resize to cover dimensions while maintaining aspect ratio
            source_img = source_img.resize((self.COVER_WIDTH, self.COVER_HEIGHT), Image.Resampling.LANCZOS)

            # Apply blur
            blurred = source_img.filter(ImageFilter.GaussianBlur(radius=8))

            # Darken for text readability
            enhancer = ImageEnhance.Brightness(blurred)
            blurred = enhancer.enhance(0.6)

            return blurred
        except Exception:
            # Fallback to solid color
            return self._create_solid_background('#2c3e50')

    def _create_solid_background(self, color: str) -> Image.Image:
        """Create solid color background"""
        if color.startswith('#'):
            color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))

        return Image.new('RGB', (self.COVER_WIDTH, self.COVER_HEIGHT), color)

    def _draw_safe_zone_overlay(self, draw: DrawType, show_guides: bool = False):
        """Draw safe zone guides (for preview only)"""
        if not show_guides:
            return

        margin = self.SAFE_ZONE_MARGIN

        # Draw safe zone rectangle
        draw.rectangle([
            (margin, margin),
            (self.COVER_WIDTH - margin, self.COVER_HEIGHT - margin)
        ], outline='red', width=2)

        # Draw title area
        draw.rectangle([
            (margin, self.TITLE_AREA_TOP),
            (self.COVER_WIDTH - margin, self.TITLE_AREA_TOP + self.TITLE_AREA_HEIGHT)
        ], outline='yellow', width=1)

    def _calculate_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Calculate text bounding box size"""
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _fit_text_to_width(self, text: str, font_name: str, max_width: int,
                          max_size: int = 72, min_size: int = 24, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Auto-fit text to specified width"""
        for size in range(max_size, min_size - 1, -2):
            font = self._get_font(font_name, size, bold)
            text_width, _ = self._calculate_text_size(text, font)
            if text_width <= max_width:
                return font

        return self._get_font(font_name, min_size, bold)

    def _draw_text_with_effects(self, draw: DrawType, text: str, position: Tuple[int, int],
                               font: ImageFont.FreeTypeFont, fill: str = 'white',
                               stroke_width: int = 2, stroke_fill: str = 'black',
                               shadow: bool = True, shadow_offset: Tuple[int, int] = (3, 3)):
        """Draw text with stroke and shadow effects"""
        x, y = position

        # Draw shadow
        if shadow:
            shadow_x, shadow_y = shadow_offset
            draw.text((x + shadow_x, y + shadow_y), text, font=font, fill='black')

        # Draw stroke
        if stroke_width > 0:
            draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            draw.text((x, y), text, font=font, fill=fill)

    def generate_cover(self, title: str, studio: str = "", version: str = "",
                      output_dir: str = ".", export_png: bool = True, export_jpg: bool = False,
                      include_metadata: bool = True, background_type: str = "Solid Color",
                      background_color: str = "#2c3e50", font: str = "Arial",
                      bold: bool = True, shadow: bool = True,
                      logo_path: Optional[str] = None, filename_stem: Optional[str] = None) -> str:
        """Generate complete cover image"""

        # Create background
        if background_type == "Gradient":
            img = self._create_gradient_background(background_color, '#34495e')
        elif background_type == "Image Blur" and logo_path:
            img = self._create_blurred_background(logo_path)
        else:
            img = self._create_solid_background(background_color)

        draw = ImageDraw.Draw(img)

        # Calculate safe text area
        text_area_width = self.COVER_WIDTH - (2 * self.SAFE_ZONE_MARGIN)

        # Title text
        title_font = self._fit_text_to_width(title, font, text_area_width, 72, 32, bold)
        title_width, title_height = self._calculate_text_size(title, title_font)
        title_x = (self.COVER_WIDTH - title_width) // 2
        title_y = self.TITLE_AREA_TOP + (self.TITLE_AREA_HEIGHT - title_height) // 2

        self._draw_text_with_effects(
            draw, title, (title_x, title_y), title_font,
            fill='white', shadow=shadow
        )

        # Studio text
        if studio:
            studio_font = self._get_font(font, 28, False)
            studio_width, studio_height = self._calculate_text_size(studio, studio_font)
            studio_x = (self.COVER_WIDTH - studio_width) // 2
            studio_y = title_y + title_height + 20

            self._draw_text_with_effects(
                draw, studio, (studio_x, studio_y), studio_font,
                fill='#ecf0f1', shadow=shadow, shadow_offset=(2, 2)
            )

        # Version text (bottom right)
        if version:
            version_font = self._get_font(font, 20, False)
            version_width, version_height = self._calculate_text_size(f"v{version}", version_font)
            version_x = self.COVER_WIDTH - version_width - self.SAFE_ZONE_MARGIN
            version_y = self.COVER_HEIGHT - version_height - self.SAFE_ZONE_MARGIN

            self._draw_text_with_effects(
                draw, f"v{version}", (version_x, version_y), version_font,
                fill='#bdc3c7', shadow=False, stroke_width=1
            )

        # Add logo if provided
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path)
                # Resize logo to fit in corner (max 120x120)
                logo.thumbnail((120, 120), Image.Resampling.LANCZOS)
                logo_x = self.SAFE_ZONE_MARGIN
                logo_y = self.COVER_HEIGHT - logo.height - self.SAFE_ZONE_MARGIN
                img.paste(logo, (logo_x, logo_y), logo if logo.mode == 'RGBA' else None)
            except Exception:
                pass

        # Verify aspect ratio
        if not ensure_aspect_ratio(img.size, self.ASPECT_RATIO):
            raise ValueError(f"Generated cover does not meet aspect ratio requirements: {self.ASPECT_RATIO}")

        # Save image(s)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename_stem:
            base_filename = filename_stem
        else:
            base_filename = f"cover-630x500_{timestamp}"
        output_paths = []

        # Add metadata if requested
        metadata = {}
        if include_metadata:
            metadata = {
                'Title': title,
                'Studio': studio,
                'Version': version,
                'Generated': timestamp,
                'Tool': 'ItchPage Wizard v1.0.0'
            }

        # Export PNG
        if export_png:
            png_path = os.path.join(output_dir, f"{base_filename}.png")
            img.save(png_path, 'PNG', pnginfo=self._create_png_metadata(metadata) if metadata else None)
            output_paths.append(png_path)

        # Export JPG
        if export_jpg:
            jpg_path = os.path.join(output_dir, f"{base_filename}.jpg")
            # Convert RGBA to RGB for JPG
            if img.mode == 'RGBA':
                jpg_img = Image.new('RGB', img.size, (255, 255, 255))
                jpg_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = jpg_img
            img.save(jpg_path, 'JPEG', quality=95, exif=self._create_jpg_metadata(metadata) if metadata else None)
            output_paths.append(jpg_path)

        return output_paths[0] if output_paths else None

    def _create_png_metadata(self, metadata: Dict[str, str]):
        """Create PNG metadata"""
        from PIL.PngImagePlugin import PngInfo
        pnginfo = PngInfo()
        for key, value in metadata.items():
            pnginfo.add_text(key, str(value))
        return pnginfo

    def _create_jpg_metadata(self, metadata: Dict[str, str]):
        """Create JPG EXIF metadata"""
        # Simplified metadata for JPG
        return None

    def generate_preview(self, cover_data: Dict[str, Any], preview_size: Tuple[int, int]) -> Optional[bytes]:
        """Generate preview image for GUI"""
        try:
            # Create a smaller version for preview
            preview_width, preview_height = preview_size
            scale_factor = min(preview_width / self.COVER_WIDTH, preview_height / self.COVER_HEIGHT)

            # Generate full cover first
            temp_cover = self._generate_cover_image(cover_data)

            # Scale down for preview
            preview_img = temp_cover.resize(
                (int(self.COVER_WIDTH * scale_factor), int(self.COVER_HEIGHT * scale_factor)),
                Image.Resampling.LANCZOS
            )

            # Convert to bytes for PySimpleGUI
            bio = io.BytesIO()
            preview_img.save(bio, format='PNG')
            return bio.getvalue()

        except Exception:
            return None

    def _generate_cover_image(self, data: Dict[str, Any]) -> Image.Image:
        """Generate cover image from data dict (helper for preview)"""
        # Create background
        bg_type = data.get('background_type', 'Solid Color')
        bg_color = data.get('background_color', '#2c3e50')

        if bg_type == "Gradient":
            img = self._create_gradient_background(bg_color, '#34495e')
        else:
            img = self._create_solid_background(bg_color)

        draw = ImageDraw.Draw(img)

        # Add text
        title = data.get('title', '')
        studio = data.get('studio', '')
        font_name = data.get('font', 'Arial')
        bold = data.get('bold', True)
        shadow = data.get('shadow', True)

        if title:
            text_area_width = self.COVER_WIDTH - (2 * self.SAFE_ZONE_MARGIN)
            title_font = self._fit_text_to_width(title, font_name, text_area_width, 72, 32, bold)
            title_width, title_height = self._calculate_text_size(title, title_font)
            title_x = (self.COVER_WIDTH - title_width) // 2
            title_y = self.TITLE_AREA_TOP + (self.TITLE_AREA_HEIGHT - title_height) // 2

            self._draw_text_with_effects(
                draw, title, (title_x, title_y), title_font,
                fill='white', shadow=shadow
            )

            if studio:
                studio_font = self._get_font(font_name, 28, False)
                studio_width, studio_height = self._calculate_text_size(studio, studio_font)
                studio_x = (self.COVER_WIDTH - studio_width) // 2
                studio_y = title_y + title_height + 20

                self._draw_text_with_effects(
                    draw, studio, (studio_x, studio_y), studio_font,
                    fill='#ecf0f1', shadow=shadow, shadow_offset=(2, 2)
                )

        return img
