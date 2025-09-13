"""
GIF Optimizer Module
Optimizes GIFs and converts MP4s to GIFs with size targets
"""

from PIL import Image, ImageSequence
import imageio
import io
import os
import subprocess
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from .utils import validate_image, check_ffmpeg

class GIFOptimizer:
    # Size targets in MB
    SIZE_PRESETS = {
        'Small': 1,
        'Medium': 3,
        'Large': 6,
        'X-Large': 10
    }

    def __init__(self):
        self.ffmpeg_available = check_ffmpeg()

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get video information using ffprobe"""
        if not self.ffmpeg_available:
            return {}

        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)

                video_stream = next(
                    (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
                    {}
                )

                return {
                    'duration': float(video_stream.get('duration', 0)),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1'))
                }
        except Exception:
            pass

        return {}

    def _extract_frames_ffmpeg(self, video_path: str, output_dir: str,
                              max_frames: int = None, fps: float = None) -> List[str]:
        """Extract frames from video using ffmpeg"""
        if not self.ffmpeg_available:
            return []

        frame_paths = []
        try:
            cmd = ['ffmpeg', '-i', video_path, '-y']

            if fps:
                cmd.extend(['-vf', f'fps={fps}'])

            if max_frames:
                cmd.extend(['-frames:v', str(max_frames)])

            frame_pattern = os.path.join(output_dir, 'frame_%04d.png')
            cmd.append(frame_pattern)

            subprocess.run(cmd, capture_output=True, timeout=60)

            # Collect generated frames
            for i in range(1, max_frames + 1 if max_frames else 1000):
                frame_path = os.path.join(output_dir, f'frame_{i:04d}.png')
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)
                else:
                    break

        except Exception:
            pass

        return frame_paths

    def _extract_frames_imageio(self, video_path: str) -> List[np.ndarray]:
        """Extract frames using imageio (fallback)"""
        try:
            reader = imageio.get_reader(video_path)
            frames = []

            for i, frame in enumerate(reader):
                frames.append(frame)
                if i > 100:  # Limit frames to prevent memory issues
                    break

            reader.close()
            return frames

        except Exception:
            return []

    def _quantize_colors(self, image: Image.Image, max_colors: int = 256) -> Image.Image:
        """Quantize image colors using median cut"""
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Use PIL's built-in quantization
        quantized = image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        return quantized.convert('RGB')

    def _calculate_target_dimensions(self, width: int, height: int,
                                   target_file_size: int, frame_count: int) -> Tuple[int, int]:
        """Calculate target dimensions to meet file size"""
        # Estimate bytes per pixel (rough approximation)
        bytes_per_pixel = 1.5  # GIF compression estimate
        target_pixels_per_frame = (target_file_size * 1024 * 1024) / (frame_count * bytes_per_pixel)

        current_pixels = width * height
        if current_pixels <= target_pixels_per_frame:
            return width, height

        # Calculate scale factor
        scale_factor = (target_pixels_per_frame / current_pixels) ** 0.5

        new_width = max(160, int(width * scale_factor))  # Minimum 160px width
        new_height = max(120, int(height * scale_factor))  # Minimum 120px height

        return new_width, new_height

    def optimize_gif(self, input_path: str, output_path: str,
                    target_size_mb: float = 3.0, quality: int = 80,
                    max_colors: int = 256, dither: bool = False) -> str:
        """Optimize existing GIF"""
        try:
            # Load GIF
            gif = Image.open(input_path)

            if not getattr(gif, 'is_animated', False):
                raise ValueError("Input is not an animated GIF")

            frames = []
            durations = []

            # Extract frames and timing
            for frame in ImageSequence.Iterator(gif):
                frames.append(frame.copy())
                durations.append(frame.info.get('duration', 100))

            if not frames:
                raise ValueError("No frames found in GIF")

            # Calculate target dimensions
            original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            if original_size <= target_size_mb:
                # Already small enough, just copy
                import shutil
                shutil.copy2(input_path, output_path)
                return output_path

            target_width, target_height = self._calculate_target_dimensions(
                gif.width, gif.height, int(target_size_mb), len(frames)
            )

            # Process frames
            optimized_frames = []
            for frame in frames:
                # Resize
                resized = frame.resize((target_width, target_height), Image.Resampling.LANCZOS)

                # Quantize colors
                if max_colors < 256:
                    resized = self._quantize_colors(resized, max_colors)

                optimized_frames.append(resized)

            # Frame decimation if still too large
            if len(optimized_frames) > 50:  # Reduce frame count
                step = len(optimized_frames) // 50
                optimized_frames = optimized_frames[::max(1, step)]
                durations = durations[::max(1, step)]

            # Save optimized GIF
            if optimized_frames:
                optimized_frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=optimized_frames[1:],
                    duration=durations,
                    loop=0,
                    optimize=True,
                    quality=quality
                )

            return output_path

        except Exception as e:
            raise ValueError(f"GIF optimization failed: {e}")

    def convert_video_to_gif(self, video_path: str, output_path: str,
                           target_size_mb: float = 3.0, quality: int = 80,
                           start_time: float = 0, duration: float = None,
                           fps: float = None) -> str:
        """Convert MP4/video to optimized GIF"""
        try:
            # Get video info
            video_info = self._get_video_info(video_path)

            if not video_info:
                # Fallback to imageio for basic conversion
                return self._convert_video_imageio(video_path, output_path, target_size_mb)

            # Calculate optimal settings
            video_duration = duration or video_info.get('duration', 10)
            video_fps = fps or min(video_info.get('fps', 15), 15)  # Cap at 15fps for size

            # Estimate frame count
            frame_count = int(video_duration * video_fps)
            if frame_count > 100:
                video_fps = 100 / video_duration  # Limit to 100 frames max
                frame_count = 100

            # Calculate target dimensions
            target_width, target_height = self._calculate_target_dimensions(
                video_info['width'], video_info['height'], int(target_size_mb), frame_count
            )

            # Use ffmpeg if available for better quality
            if self.ffmpeg_available:
                return self._convert_video_ffmpeg(
                    video_path, output_path, target_width, target_height,
                    video_fps, start_time, video_duration, quality
                )
            else:
                return self._convert_video_imageio(video_path, output_path, target_size_mb)

        except Exception as e:
            raise ValueError(f"Video to GIF conversion failed: {e}")

    def _convert_video_ffmpeg(self, video_path: str, output_path: str,
                             width: int, height: int, fps: float,
                             start_time: float, duration: float, quality: int) -> str:
        """Convert video using ffmpeg"""
        try:
            cmd = [
                'ffmpeg', '-i', video_path, '-y',
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f'fps={fps},scale={width}:{height}:flags=lanczos',
                '-q:v', str(100 - quality),  # Convert quality to ffmpeg scale
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=120)

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                raise ValueError("FFmpeg conversion failed")

        except Exception as e:
            raise ValueError(f"FFmpeg conversion error: {e}")

    def _convert_video_imageio(self, video_path: str, output_path: str,
                              target_size_mb: float) -> str:
        """Convert video using imageio (fallback)"""
        try:
            # Extract frames
            frames = self._extract_frames_imageio(video_path)

            if not frames:
                raise ValueError("Could not extract frames from video")

            # Limit frame count for size
            max_frames = min(len(frames), 50)
            frames = frames[:max_frames]

            # Convert to PIL Images and resize
            pil_frames = []
            first_frame = Image.fromarray(frames[0])

            # Calculate target size
            target_width, target_height = self._calculate_target_dimensions(
                first_frame.width, first_frame.height, int(target_size_mb), len(frames)
            )

            for frame_array in frames:
                pil_frame = Image.fromarray(frame_array)
                resized = pil_frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
                pil_frames.append(resized)

            # Save as GIF
            if pil_frames:
                pil_frames[0].save(
                    output_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=200,  # 5fps
                    loop=0,
                    optimize=True
                )

            return output_path

        except Exception as e:
            raise ValueError(f"ImageIO conversion failed: {e}")

    def get_preview_frame(self, media_path: str, preview_size: Tuple[int, int]) -> Optional[bytes]:
        """Get preview frame from GIF or video"""
        try:
            if media_path.lower().endswith('.gif'):
                # Get first frame of GIF
                gif = Image.open(media_path)
                first_frame = gif.copy()
            else:
                # Try to extract first frame of video
                if self.ffmpeg_available:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        frames = self._extract_frames_ffmpeg(media_path, temp_dir, max_frames=1)
                        if frames:
                            first_frame = Image.open(frames[0])
                        else:
                            return None
                else:
                    # Use imageio
                    frames = self._extract_frames_imageio(media_path)
                    if frames:
                        first_frame = Image.fromarray(frames[0])
                    else:
                        return None

            # Scale for preview
            first_frame.thumbnail(preview_size, Image.Resampling.LANCZOS)

            # Convert to bytes
            bio = io.BytesIO()
            first_frame.save(bio, format='PNG')
            return bio.getvalue()

        except Exception:
            return None
