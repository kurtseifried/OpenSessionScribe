"""Integrated slide processing pipeline."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from ..config import Config
from ..schemas.package import Slide
from .detector import SlideDetector
from .ocr_processor import OCRProcessor
from .vlm_describer import VLMDescriber


logger = logging.getLogger(__name__)


class SlideProcessor:
    """Complete slide processing pipeline."""
    
    def __init__(self, config: Config):
        self.config = config
        self.detector = SlideDetector(config)
        self.ocr = OCRProcessor(config) if config.enable_slides else None
        self.vlm = VLMDescriber(config) if config.enable_descriptions else None
    
    def process_video(self, video_path: Path, output_dir: Path) -> List[Slide]:
        """Process video to extract slides with OCR and descriptions."""
        if not self.config.enable_slides:
            logger.info("Slide processing disabled")
            return []
        
        logger.info(f"Processing slides from {video_path}")
        
        # Create slides directory
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(exist_ok=True)
        
        try:
            # Step 1: Detect slide change timestamps
            logger.info("Detecting slide changes...")
            timestamps = self.detector.detect_slides(video_path)
            logger.info(f"Found {len(timestamps)} potential slides")
            
            if not timestamps:
                logger.warning("No slides detected")
                return []
            
            # Step 2: Extract frames
            logger.info("Extracting slide frames...")
            slide_paths = []
            for i, timestamp in enumerate(timestamps):
                slide_path = slides_dir / f"slide_{i:03d}.jpg"
                if self.detector.extract_frame(video_path, timestamp, slide_path):
                    slide_paths.append(slide_path)
                else:
                    logger.warning(f"Failed to extract frame at {timestamp}s")
            
            if not slide_paths:
                logger.error("Failed to extract any slide frames")
                return []
            
            # Step 3: Deduplicate slides
            logger.info("Removing duplicate slides...")
            unique_slides = self.detector.deduplicate_slides(slide_paths)
            logger.info(f"Kept {len(unique_slides)} unique slides")
            
            # Step 4: Auto-crop detection (optional)
            crop_coords = None
            if len(unique_slides) >= 3:
                logger.info("Analyzing slides for auto-crop region...")
                crop_coords = self.detector.auto_crop_slides(unique_slides)
            
            # Step 5: Process each slide
            slides_data = []
            for i, slide_path in enumerate(unique_slides):
                logger.info(f"Processing slide {i+1}/{len(unique_slides)}: {slide_path.name}")
                
                slide_data = self._process_single_slide(
                    slide_path, 
                    timestamps[i] if i < len(timestamps) else 0,
                    crop_coords
                )
                slide_data.index = i
                slides_data.append(slide_data)
            
            logger.info(f"Slide processing complete: {len(slides_data)} slides processed")
            return slides_data
            
        except Exception as e:
            logger.error(f"Slide processing failed: {e}")
            return []
    
    def _process_single_slide(
        self, 
        slide_path: Path, 
        timestamp: float, 
        crop_coords: Optional[Dict[str, int]] = None
    ) -> Slide:
        """Process a single slide with OCR and description."""
        slide_data = Slide(
            index=0,  # Will be set by caller
            timestamp=timestamp,
            image_path=str(slide_path),
            crop=crop_coords,
            ocr=None,
            description=None
        )
        
        try:
            # OCR processing
            if self.ocr:
                logger.debug(f"Running OCR on {slide_path.name}")
                ocr_result = self.ocr.process_image(slide_path)
                slide_data.ocr = ocr_result
            
            # VLM description
            if self.vlm:
                logger.debug(f"Generating description for {slide_path.name}")
                ocr_text = slide_data.ocr.text if slide_data.ocr else ""
                description_result = self.vlm.describe_slide(slide_path, ocr_text)
                if description_result:
                    slide_data.description = description_result.get('description')
                    slide_data.bullets = description_result.get('bullets')
                    if description_result.get('chart_info'):
                        chart = description_result['chart_info']
                        from ..schemas.package import ChartInfo
                        slide_data.chart = ChartInfo(
                            type=chart.get('type', 'unknown'),
                            trend=chart.get('trend')
                        )
                    slide_data.ascii_art = description_result.get('ascii_art')
            
        except Exception as e:
            logger.error(f"Error processing slide {slide_path}: {e}")
        
        return slide_data
    
    def reprocess_slide(self, slide_path: Path, custom_prompt: str = "") -> Slide:
        """Reprocess a single slide (for editor use)."""
        logger.info(f"Reprocessing slide: {slide_path}")
        
        slide_data = Slide(
            index=0,
            timestamp=0,  # Unknown for reprocessing
            image_path=str(slide_path),
            ocr=None,
            description=None
        )
        
        try:
            # Re-run OCR
            if self.ocr:
                ocr_result = self.ocr.process_image(slide_path)
                slide_data.ocr = ocr_result
            
            # Re-run VLM with custom prompt if provided
            if self.vlm:
                ocr_text = slide_data.ocr.text if slide_data.ocr else ""
                if custom_prompt:
                    description_result = self.vlm.redescribe_slide(slide_path, ocr_text, custom_prompt)
                else:
                    description_result = self.vlm.describe_slide(slide_path, ocr_text)
                
                if description_result:
                    slide_data.description = description_result.get('description')
        
        except Exception as e:
            logger.error(f"Error reprocessing slide {slide_path}: {e}")
        
        return slide_data
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check availability of slide processing dependencies."""
        deps = {
            "ffmpeg": True,  # Assume available if we got this far
            "scenedetect": SlideDetector.check_scenedetect(),
            "paddleocr": OCRProcessor.check_paddleocr() if self.ocr else False,
            "tesseract": OCRProcessor.check_tesseract() if self.ocr else False,
            "ollama": self.vlm.check_ollama_running() if self.vlm else False,
            "vlm_model": self.vlm.check_model_available(self.config.vlm_model) if self.vlm else False
        }
        
        return deps
    
    def cleanup(self) -> None:
        """Clean up loaded models to free memory."""
        if hasattr(self.ocr, 'paddle_ocr') and self.ocr.paddle_ocr:
            del self.ocr.paddle_ocr
            self.ocr.paddle_ocr = None
        
        # VLM is stateless (HTTP requests)
        logger.info("Slide processing models cleaned up")