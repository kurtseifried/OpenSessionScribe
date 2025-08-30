"""Slide change detection and frame extraction."""

from pathlib import Path
from typing import List, Dict, Optional
import logging
import subprocess
import json

from ..config import Config
from ..utils.ffmpeg import FFmpegProcessor


logger = logging.getLogger(__name__)


class SlideDetector:
    """Detect slide changes in video and extract keyframes."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def detect_slides(self, video_path: Path) -> List[float]:
        """Detect slide change timestamps in video."""
        logger.info(f"Detecting slide changes in {video_path}")
        
        try:
            if self.check_scenedetect():
                return self._detect_with_scenedetect(video_path)
            else:
                logger.warning("PySceneDetect not available, using FFmpeg-based detection")
                return self._detect_with_ffmpeg(video_path)
        except Exception as e:
            logger.error(f"Slide detection failed: {e}")
            # Fallback: extract frames at regular intervals
            return self._fallback_intervals(video_path)
    
    def extract_frame(self, video_path: Path, timestamp: float, output_path: Path) -> bool:
        """Extract frame at specific timestamp."""
        logger.debug(f"Extracting frame at {timestamp}s from {video_path}")
        
        try:
            ffmpeg = FFmpegProcessor()
            
            # Add small offset to avoid transition blur
            seek_time = max(0, timestamp + 0.5)
            
            # Use ffmpeg to extract high-quality frame
            cmd = [
                "ffmpeg",
                "-ss", str(seek_time),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",  # High quality
                "-y",  # Overwrite output
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.debug(f"Frame extracted successfully to {output_path}")
                return True
            else:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return False
    
    def deduplicate_slides(self, slide_paths: List[Path]) -> List[Path]:
        """Remove duplicate slides using perceptual hashing."""
        logger.info(f"Deduplicating {len(slide_paths)} slides")
        
        try:
            import imagehash
            from PIL import Image
            
            unique_slides = []
            hashes = []
            threshold = 8  # Hamming distance threshold
            
            for slide_path in slide_paths:
                try:
                    # Load image and compute perceptual hash
                    image = Image.open(slide_path)
                    phash = imagehash.phash(image)
                    
                    # Check if similar hash exists
                    is_duplicate = False
                    for existing_hash in hashes:
                        if phash - existing_hash < threshold:
                            is_duplicate = True
                            logger.debug(f"Duplicate slide detected: {slide_path}")
                            break
                    
                    if not is_duplicate:
                        unique_slides.append(slide_path)
                        hashes.append(phash)
                    
                except Exception as e:
                    logger.warning(f"Failed to process slide {slide_path}: {e}")
                    # Keep the slide if we can't process it
                    unique_slides.append(slide_path)
            
            logger.info(f"Kept {len(unique_slides)} unique slides from {len(slide_paths)} total")
            return unique_slides
            
        except ImportError:
            logger.warning("imagehash not available, skipping deduplication")
            return slide_paths
    
    def auto_crop_slides(self, slide_paths: List[Path]) -> Optional[Dict[str, int]]:
        """Detect stable slide region and return crop coordinates."""
        logger.info(f"Analyzing {len(slide_paths)} slides for auto-crop region")
        
        try:
            import cv2
            import numpy as np
            from PIL import Image
            
            if len(slide_paths) < 3:
                logger.warning("Need at least 3 slides for auto-crop analysis")
                return None
            
            # Sample up to 10 slides for analysis
            sample_paths = slide_paths[:min(10, len(slide_paths))]
            edges_list = []
            
            for slide_path in sample_paths:
                try:
                    # Load image and convert to grayscale
                    image = cv2.imread(str(slide_path))
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    
                    # Detect edges
                    edges = cv2.Canny(gray, 50, 150)
                    edges_list.append(edges)
                    
                except Exception as e:
                    logger.warning(f"Failed to process slide {slide_path}: {e}")
            
            if not edges_list:
                return None
            
            # Find common edge regions across slides
            # Sum all edge maps and find stable regions
            combined_edges = np.sum(edges_list, axis=0)
            
            # Find bounding box of consistent content
            rows = np.any(combined_edges > len(edges_list) * 0.3, axis=1)
            cols = np.any(combined_edges > len(edges_list) * 0.3, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                return None
            
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            # Add some padding
            height, width = combined_edges.shape
            padding = 20
            rmin = max(0, rmin - padding)
            rmax = min(height, rmax + padding)
            cmin = max(0, cmin - padding)
            cmax = min(width, cmax + padding)
            
            crop_coords = {
                "x": int(cmin),
                "y": int(rmin),
                "width": int(cmax - cmin),
                "height": int(rmax - rmin)
            }
            
            logger.info(f"Auto-crop region detected: {crop_coords}")
            return crop_coords
            
        except ImportError:
            logger.warning("OpenCV not available for auto-crop analysis")
            return None
        except Exception as e:
            logger.error(f"Auto-crop analysis failed: {e}")
            return None
    
    def _detect_with_scenedetect(self, video_path: Path) -> List[float]:
        """Use PySceneDetect for accurate slide detection."""
        try:
            from scenedetect import VideoManager, SceneManager
            from scenedetect.detectors import ContentDetector
            
            # Initialize video manager and scene manager
            video_manager = VideoManager([str(video_path)])
            scene_manager = SceneManager()
            
            # Configure content detector for slide changes
            # Higher threshold for slides (less sensitive to minor changes)
            scene_manager.add_detector(ContentDetector(threshold=30.0))
            
            # Process video
            video_manager.set_duration()
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            
            # Extract scene timestamps
            scene_list = scene_manager.get_scene_list()
            timestamps = []
            
            for scene in scene_list:
                start_time = scene[0].get_seconds()
                timestamps.append(start_time)
            
            # Filter out very short segments (< 5 seconds)
            filtered_timestamps = [timestamps[0]] if timestamps else []
            for i in range(1, len(timestamps)):
                if timestamps[i] - timestamps[i-1] > 5.0:
                    filtered_timestamps.append(timestamps[i])
            
            logger.info(f"Detected {len(filtered_timestamps)} slide changes using PySceneDetect")
            
            # If no scenes detected, use fallback intervals for basic frame extraction
            if not filtered_timestamps:
                logger.info("No scene changes detected, falling back to interval extraction")
                return self._fallback_intervals(video_path)
            
            return filtered_timestamps
            
        except Exception as e:
            logger.error(f"PySceneDetect detection failed: {e}")
            raise
    
    def _detect_with_ffmpeg(self, video_path: Path) -> List[float]:
        """Use FFmpeg scene detection as fallback."""
        try:
            # Use ffmpeg scene detection filter
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-filter:v", "select='gt(scene,0.3)',showinfo",
                "-f", "null",
                "-"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse scene change timestamps from output
            timestamps = []
            for line in result.stderr.split('\n'):
                if 'pts_time:' in line:
                    try:
                        # Extract timestamp from showinfo output
                        pts_start = line.find('pts_time:') + 9
                        pts_end = line.find(' ', pts_start)
                        timestamp = float(line[pts_start:pts_end])
                        timestamps.append(timestamp)
                    except (ValueError, IndexError):
                        continue
            
            # Filter and sort timestamps
            timestamps = sorted(set(timestamps))
            
            # Filter out very short segments
            filtered_timestamps = [timestamps[0]] if timestamps else []
            for i in range(1, len(timestamps)):
                if timestamps[i] - timestamps[i-1] > 3.0:
                    filtered_timestamps.append(timestamps[i])
            
            logger.info(f"Detected {len(filtered_timestamps)} slide changes using FFmpeg")
            return filtered_timestamps
            
        except Exception as e:
            logger.error(f"FFmpeg scene detection failed: {e}")
            return []
    
    def _fallback_intervals(self, video_path: Path) -> List[float]:
        """Fallback: extract frames at regular intervals."""
        try:
            ffmpeg = FFmpegProcessor()
            info = ffmpeg.get_media_info(video_path)
            
            duration = info.get('duration', 0)
            if duration <= 0:
                return []
            
            # Extract frame every 30 seconds for short videos, 60s for longer ones
            interval = 30 if duration < 600 else 60
            timestamps = []
            
            current = 0
            while current < duration:
                timestamps.append(current)
                current += interval
            
            logger.info(f"Using fallback intervals: {len(timestamps)} frames every {interval}s")
            return timestamps
            
        except Exception as e:
            logger.error(f"Fallback interval detection failed: {e}")
            return [0]  # At least extract one frame
    
    @staticmethod
    def check_scenedetect() -> bool:
        """Check if PySceneDetect is available."""
        try:
            import scenedetect
            return True
        except ImportError:
            return False