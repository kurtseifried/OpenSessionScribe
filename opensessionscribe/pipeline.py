"""Main processing pipeline orchestration."""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .config import Config
from .schemas.package import Package
from .ingest.downloader import MediaDownloader
from .asr.whisperx_adapter import WhisperXAdapter
from .diarize.pyannote_adapter import PyAnnoteAdapter
from .slides.detector import SlideDetector
from .slides.ocr_processor import OCRProcessor
from .slides.vlm_describer import VLMDescriber


logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Main pipeline for processing podcasts and webinars."""
    
    def __init__(self, config: Config):
        self.config = config
        self.downloader = MediaDownloader(config)
        self.asr = WhisperXAdapter(config)
        self.diarizer = PyAnnoteAdapter(config)
        self.slide_detector = SlideDetector(config)
        self.ocr = OCRProcessor(config)
        self.vlm = VLMDescriber(config)
    
    def process_url(self, url: str, output_dir: Path) -> Package:
        """Process a URL (YouTube, podcast, etc.) into a complete package."""
        logger.info(f"Processing URL: {url}")
        
        # Phase 1: Download and prepare media
        media_info = self.downloader.download(url, output_dir)
        
        # Phase 2: Process transcript
        transcript_data = self._process_transcript(media_info)
        
        # Phase 3: Process slides (if video)
        slides_data = []
        if media_info.get("has_video") and self.config.enable_slides:
            slides_data = self._process_slides(media_info, output_dir)
        
        # Phase 4: Create final package
        package = self._create_package(url, media_info, transcript_data, slides_data)
        
        # Phase 5: Export and validate
        self._export_package(package, output_dir)
        
        return package
    
    def _process_transcript(self, media_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio for transcript and speaker diarization."""
        audio_path = media_info["audio_path"]
        
        # Run ASR
        logger.info("Running speech recognition...")
        transcript = self.asr.transcribe(audio_path)
        
        # Run diarization
        logger.info("Running speaker diarization...")
        diarization = self.diarizer.diarize(audio_path)
        
        # Merge transcript and diarization
        logger.info("Merging transcript with speaker labels...")
        merged = self._merge_transcript_diarization(transcript, diarization)
        
        return merged
    
    def _process_slides(self, media_info: Dict[str, Any], output_dir: Path) -> list:
        """Process video for slides, OCR, and descriptions."""
        video_path = media_info["video_path"]
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)
        
        # Detect slide changes
        logger.info("Detecting slide changes...")
        timestamps = self.slide_detector.detect_slides(video_path)
        
        slides_data = []
        for i, timestamp in enumerate(timestamps):
            # Extract frame
            slide_path = slides_dir / f"slide_{i+1:03d}.jpg"
            self.slide_detector.extract_frame(video_path, timestamp, slide_path)
            
            # Run OCR
            ocr_result = self.ocr.process_image(slide_path)
            
            # Generate description (if enabled)
            description = None
            if self.config.enable_descriptions:
                description = self.vlm.describe_slide(slide_path, ocr_result.get("text", ""))
            
            slides_data.append({
                "index": i + 1,
                "timestamp": timestamp,
                "image_path": str(slide_path.relative_to(output_dir)),
                "ocr": ocr_result,
                "description": description
            })
        
        return slides_data
    
    def _merge_transcript_diarization(self, transcript: dict, diarization: dict) -> dict:
        """Merge ASR transcript with speaker diarization labels."""
        # TODO: Implement alignment algorithm
        # Map ASR word timestamps to diarization speaker segments
        # Group consecutive words with same speaker into segments
        pass
    
    def _create_package(self, url: str, media_info: dict, transcript: dict, slides: list) -> Package:
        """Create final Package object."""
        # TODO: Build complete Package with all data
        pass
    
    def _export_package(self, package: Package, output_dir: Path) -> None:
        """Export package to JSON and generate manifest."""
        # TODO: Write package.json, generate checksums, create manifest
        pass