"""FFmpeg utilities for audio/video processing."""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging


logger = logging.getLogger(__name__)


class FFmpegProcessor:
    """Wrapper for FFmpeg operations."""
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """Check if FFmpeg is available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def extract_audio(video_path: Path, output_path: Path, sample_rate: int = 16000) -> None:
        """Extract audio from video file."""
        logger.info(f"Extracting audio: {video_path} -> {output_path}")
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ac", "1",  # Mono
            "-ar", str(sample_rate),  # Sample rate
            "-y",  # Overwrite output
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug(f"FFmpeg audio extraction completed")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")
    
    @staticmethod
    def get_media_info(file_path: Path) -> Dict[str, Any]:
        """Get media file information using ffprobe."""
        logger.debug(f"Getting media info: {file_path}")
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            # Extract useful information
            format_info = probe_data.get('format', {})
            streams = probe_data.get('streams', [])
            
            # Find video and audio streams
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            
            info = {
                "duration": float(format_info.get('duration', 0)),
                "size_bytes": int(format_info.get('size', 0)),
                "bitrate": int(format_info.get('bit_rate', 0)),
                "format_name": format_info.get('format_name', ''),
            }
            
            if video_stream:
                info.update({
                    "video": {
                        "codec": video_stream.get('codec_name', ''),
                        "width": int(video_stream.get('width', 0)),
                        "height": int(video_stream.get('height', 0)),
                        "fps": eval(video_stream.get('r_frame_rate', '0/1'))  # Convert fraction to float
                    }
                })
            
            if audio_stream:
                info.update({
                    "audio": {
                        "codec": audio_stream.get('codec_name', ''),
                        "channels": int(audio_stream.get('channels', 0)),
                        "sample_rate": int(audio_stream.get('sample_rate', 0))
                    }
                })
            
            logger.debug(f"Media info: duration={info['duration']}s, has_video={'video' in info}")
            return info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            raise RuntimeError(f"Failed to get media info: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe JSON: {e}")
            raise RuntimeError(f"Failed to parse media info: {e}")
    
    @staticmethod
    def extract_frame(video_path: Path, timestamp: float, output_path: Path, width: Optional[int] = None) -> None:
        """Extract single frame at timestamp."""
        logger.debug(f"Extracting frame at {timestamp}s: {video_path} -> {output_path}")
        
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),  # Seek to timestamp
            "-i", str(video_path),
            "-vframes", "1",  # Extract 1 frame
            "-q:v", "2",  # High quality
            "-y",  # Overwrite output
        ]
        
        # Add scaling if width specified
        if width:
            cmd.extend(["-vf", f"scale={width}:-1"])  # Keep aspect ratio
        
        cmd.append(str(output_path))
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug(f"Frame extracted successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Frame extraction failed: {e.stderr}")
            raise RuntimeError(f"Frame extraction failed: {e.stderr}")
    
    @staticmethod
    def create_thumbnail_strip(video_path: Path, output_path: Path, count: int = 20) -> None:
        """Create thumbnail strip for video preview."""
        logger.debug(f"Creating thumbnail strip: {count} frames")
        
        # Get video duration first
        info = FFmpegProcessor.get_media_info(video_path)
        duration = info.get('duration', 0)
        
        if duration == 0:
            raise RuntimeError("Cannot create thumbnails: video duration is 0")
        
        # Create filter for extracting evenly spaced frames
        interval = duration / count
        filter_select = f"select='not(mod(n,{int(interval * 30)}))'"
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vf", f"{filter_select},scale=160:90,tile={count}x1",
            "-frames:v", "1",
            "-y",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug(f"Thumbnail strip created: {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Thumbnail creation failed: {e.stderr}")
            raise RuntimeError(f"Thumbnail creation failed: {e.stderr}")
    
    @staticmethod
    def check_ffprobe() -> bool:
        """Check if ffprobe is available."""
        try:
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False