"""Media download using yt-dlp."""

import subprocess
from pathlib import Path
from typing import Dict, Any
import json
import tempfile
import logging

from ..config import Config
from ..utils.ffmpeg import FFmpegProcessor


logger = logging.getLogger(__name__)


class MediaDownloader:
    """Download media from URLs using yt-dlp."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def download(self, url: str, output_dir: Path) -> Dict[str, Any]:
        """Download media from URL and prepare for processing."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download video/audio
        media_info = self._download_media(url, output_dir)
        
        # Extract/normalize audio for ASR
        audio_path = self._prepare_audio(media_info, output_dir)
        media_info["audio_path"] = audio_path
        
        return media_info
    
    def _download_media(self, url: str, output_dir: Path) -> Dict[str, Any]:
        """Use yt-dlp to download media."""
        logger.info(f"Downloading media from: {url}")
        
        # Get video info first
        info = self.get_info(url)
        
        # Determine output format and filename
        title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
        safe_title = ''.join(c for c in title if c.isalnum() or c in ' -_.')[:100]
        
        # Download with yt-dlp
        output_template = str(output_dir / f"{safe_title}.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--format", "best[ext=mp4]/best",  # Prefer mp4, fallback to best
            "--output", output_template,
            "--write-info-json",
            "--no-playlist",
            url
        ]
        
        if self.config.offline_only:
            # Don't update yt-dlp if offline mode
            cmd.append("--no-check-updates")
        
        logger.debug(f"Running yt-dlp: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.debug(f"yt-dlp output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp failed: {e.stderr}")
            raise RuntimeError(f"Failed to download {url}: {e.stderr}")
        
        # Find downloaded file
        media_files = list(output_dir.glob(f"{safe_title}.*"))
        media_files = [f for f in media_files if f.suffix in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.wav']]
        
        if not media_files:
            raise RuntimeError(f"No media file found after download")
        
        media_path = media_files[0]
        logger.info(f"Downloaded: {media_path}")
        
        # Get media info using ffmpeg
        media_info = FFmpegProcessor.get_media_info(media_path)
        media_info.update({
            "url": url,
            "title": info.get('title', ''),
            "uploader": info.get('uploader', ''),
            "description": info.get('description', ''),
            "upload_date": info.get('upload_date', ''),
            "media_path": media_path,
            "has_video": 'video' in media_info
        })
        
        return media_info
    
    def _prepare_audio(self, media_info: Dict[str, Any], output_dir: Path) -> Path:
        """Extract and normalize audio for ASR processing."""
        media_path = media_info["media_path"]
        audio_output = output_dir / "audio.wav"
        
        logger.info(f"Extracting audio: {media_path} -> {audio_output}")
        
        try:
            FFmpegProcessor.extract_audio(media_path, audio_output, sample_rate=16000)
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            raise RuntimeError(f"Failed to extract audio from {media_path}: {e}")
        
        logger.info(f"Audio prepared: {audio_output}")
        return audio_output
    
    def get_info(self, url: str) -> Dict[str, Any]:
        """Get media information without downloading."""
        logger.debug(f"Getting info for: {url}")
        
        cmd = [
            "yt-dlp",
            "--dump-single-json",
            "--no-playlist",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            logger.debug(f"Got info: title='{info.get('title', 'N/A')}', duration={info.get('duration', 0)}s")
            return info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get info for {url}: {e.stderr}")
            raise RuntimeError(f"Failed to get info for {url}: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse yt-dlp JSON output: {e}")
            raise RuntimeError(f"Failed to parse video info: {e}")
    
    @staticmethod
    def check_ytdlp() -> bool:
        """Check if yt-dlp is available."""
        try:
            result = subprocess.run(["yt-dlp", "--version"], 
                                  capture_output=True, text=True, check=True)
            logger.debug(f"yt-dlp version: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False