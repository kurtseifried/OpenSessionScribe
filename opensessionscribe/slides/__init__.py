"""Slide detection, OCR, and description modules."""

from .processor import SlideProcessor
from .detector import SlideDetector
from .ocr_processor import OCRProcessor
from .vlm_describer import VLMDescriber

__all__ = [
    "SlideProcessor",
    "SlideDetector", 
    "OCRProcessor",
    "VLMDescriber"
]