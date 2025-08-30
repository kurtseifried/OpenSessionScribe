"""OCR processing for slides using PaddleOCR and Tesseract."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import subprocess

from ..config import Config
from ..schemas.package import OCRResult


logger = logging.getLogger(__name__)


class OCRProcessor:
    """Process slide images with OCR."""
    
    def __init__(self, config: Config):
        self.config = config
        self.paddle_ocr = None
        self.tesseract_available = None
    
    def load_engines(self) -> None:
        """Initialize OCR engines."""
        logger.info(f"Loading OCR engines (primary: {self.config.ocr_engine})")
        
        # Initialize PaddleOCR if requested and available
        if self.config.ocr_engine == "paddle" and self.check_paddleocr():
            try:
                from paddleocr import PaddleOCR
                # Use CPU or GPU based on config
                use_gpu = self.config.device == "cuda" and not self.config.force_cpu
                self.paddle_ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='en',
                    use_gpu=use_gpu
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PaddleOCR: {e}")
                logger.info("Falling back to Tesseract")
                self.config.ocr_engine = "tesseract"
        
        # Check Tesseract availability
        self.tesseract_available = self.check_tesseract()
        if not self.tesseract_available and self.config.ocr_engine == "tesseract":
            logger.error("Tesseract not available but configured as OCR engine")
            raise RuntimeError("No OCR engine available")
    
    def process_image(self, image_path: Path) -> OCRResult:
        """Extract text from slide image using OCR."""
        if self.paddle_ocr is None:
            self.load_engines()
        
        logger.info(f"Running OCR on {image_path}")
        
        if self.config.ocr_engine == "paddle":
            return self._paddle_ocr(image_path)
        else:
            return self._tesseract_ocr(image_path)
    
    def _paddle_ocr(self, image_path: Path) -> OCRResult:
        """Process image with PaddleOCR."""
        if self.paddle_ocr is None:
            raise RuntimeError("PaddleOCR not initialized")
        
        try:
            # Run PaddleOCR detection and recognition
            result = self.paddle_ocr.ocr(str(image_path), cls=True)
            
            # Extract text blocks with positions and confidence
            blocks = []
            all_text = []
            total_confidence = 0.0
            
            if result and result[0]:  # PaddleOCR returns nested list
                for line in result[0]:
                    if len(line) >= 2:
                        bbox, (text, confidence) = line
                        
                        # Convert bbox to standard format
                        x_coords = [point[0] for point in bbox]
                        y_coords = [point[1] for point in bbox]
                        
                        block = {
                            "text": text,
                            "confidence": float(confidence),
                            "bbox": {
                                "x": int(min(x_coords)),
                                "y": int(min(y_coords)),
                                "width": int(max(x_coords) - min(x_coords)),
                                "height": int(max(y_coords) - min(y_coords))
                            }
                        }
                        
                        blocks.append(block)
                        all_text.append(text)
                        total_confidence += confidence
            
            # Calculate average confidence
            avg_confidence = total_confidence / len(blocks) if blocks else 0.0
            
            # Join text with appropriate spacing
            combined_text = "\n".join(all_text)
            
            logger.debug(f"PaddleOCR extracted {len(blocks)} text blocks")
            
            return OCRResult(
                engine="paddleocr",
                text=combined_text,
                confidence=avg_confidence,
                blocks=blocks
            )
            
        except Exception as e:
            logger.error(f"PaddleOCR processing failed: {e}")
            # Fallback to empty result rather than crashing
            return OCRResult(
                engine="paddleocr",
                text="",
                confidence=0.0,
                blocks=[]
            )
    
    def _tesseract_ocr(self, image_path: Path) -> OCRResult:
        """Process image with Tesseract (fallback)."""
        if not self.tesseract_available:
            raise RuntimeError("Tesseract not available")
        
        try:
            # Use tesseract with TSV output for position data
            cmd = [
                "tesseract",
                str(image_path),
                "stdout",
                "-c", "tessedit_create_tsv=1",
                "--psm", "3",  # Fully automatic page segmentation
                "-l", "eng"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Tesseract failed: {result.stderr}")
                raise RuntimeError(f"Tesseract OCR failed: {result.stderr}")
            
            # Parse TSV output
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:  # No data
                return OCRResult(
                    engine="tesseract",
                    text="",
                    confidence=0.0,
                    blocks=[]
                )
            
            # Skip header line
            blocks = []
            all_text = []
            confidences = []
            
            for line in lines[1:]:
                fields = line.split('\t')
                if len(fields) >= 12:
                    level, page_num, block_num, par_num, line_num, word_num = map(int, fields[:6])
                    left, top, width, height = map(int, fields[6:10])
                    conf = int(fields[10]) if fields[10].isdigit() else 0
                    text = fields[11] if len(fields) > 11 else ""
                    
                    # Only process word-level text (level 5) with reasonable confidence
                    if level == 5 and text.strip() and conf > 30:
                        block = {
                            "text": text,
                            "confidence": conf / 100.0,  # Convert to 0-1 scale
                            "bbox": {
                                "x": left,
                                "y": top,
                                "width": width,
                                "height": height
                            }
                        }
                        
                        blocks.append(block)
                        all_text.append(text)
                        confidences.append(conf / 100.0)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Join text with spaces
            combined_text = " ".join(all_text)
            
            logger.debug(f"Tesseract extracted {len(blocks)} text blocks")
            
            return OCRResult(
                engine="tesseract",
                text=combined_text,
                confidence=avg_confidence,
                blocks=blocks
            )
            
        except Exception as e:
            logger.error(f"Tesseract processing failed: {e}")
            return OCRResult(
                engine="tesseract",
                text="",
                confidence=0.0,
                blocks=[]
            )
    
    def process_region(self, image_path: Path, bbox: Dict[str, int]) -> OCRResult:
        """Process specific region of image (for editor re-OCR)."""
        try:
            from PIL import Image
            
            # Load and crop image to bounding box
            image = Image.open(image_path)
            crop_box = (
                bbox['x'],
                bbox['y'],
                bbox['x'] + bbox['width'],
                bbox['y'] + bbox['height']
            )
            cropped = image.crop(crop_box)
            
            # Save cropped image temporarily
            temp_path = image_path.parent / f"temp_crop_{image_path.stem}.png"
            cropped.save(temp_path)
            
            try:
                # Process cropped region
                result = self.process_image(temp_path)
                return result
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
            
        except Exception as e:
            logger.error(f"Region OCR processing failed: {e}")
            return OCRResult(
                engine=self.config.ocr_engine,
                text="",
                confidence=0.0,
                blocks=[]
            )
    
    @staticmethod
    def check_paddleocr() -> bool:
        """Check if PaddleOCR is available."""
        try:
            import paddleocr
            return True
        except ImportError:
            return False
    
    @staticmethod
    def check_tesseract() -> bool:
        """Check if Tesseract is available."""
        try:
            result = subprocess.run(
                ["tesseract", "--version"], 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False