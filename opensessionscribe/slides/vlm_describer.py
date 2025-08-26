"""VLM-based slide description using Ollama."""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..config import Config


logger = logging.getLogger(__name__)


class VLMDescriber:
    """Generate slide descriptions using local VLM via Ollama."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = None
    
    def load_model(self) -> None:
        """Initialize Ollama client and check model availability."""
        # TODO: Initialize Ollama client
        # TODO: Check if VLM model is available locally
        # TODO: Provide helpful error if model not found
        pass
    
    def describe_slide(self, image_path: Path, ocr_text: str = "") -> Optional[Dict[str, Any]]:
        """Generate description of slide using VLM."""
        if not self.config.enable_descriptions:
            return None
        
        if self.client is None:
            self.load_model()
        
        logger.info(f"Generating description for {image_path}")
        
        # TODO: Send image + OCR text to VLM
        # 1. Prepare prompt with instructions
        # 2. Include OCR text for context
        # 3. Request structured output:
        #    - One-line caption
        #    - 3-5 bullet points
        #    - Chart analysis if present
        #    - Optional ASCII art
        
        return {
            "description": "",
            "bullets": [],
            "chart_info": None,
            "ascii_art": None
        }
    
    def _build_prompt(self, ocr_text: str) -> str:
        """Build VLM prompt for slide description."""
        prompt = """Analyze this slide image and provide:

1. A one-sentence description
2. 3-5 key bullet points
3. If there's a chart/graph:
   - Chart type (bar, line, pie, etc.)
   - Axis labels and units if visible
   - Overall trend or pattern
4. Optional: Simple ASCII art representation (max 80 chars wide)

OCR Text from slide:
{ocr_text}

Respond in JSON format with keys: description, bullets, chart_type, chart_trend, ascii_art"""
        
        return prompt.format(ocr_text=ocr_text or "No text detected")
    
    def redescribe_slide(self, image_path: Path, ocr_text: str, user_prompt: str) -> Dict[str, Any]:
        """Re-generate description with custom prompt (for editor)."""
        # TODO: Allow custom prompts in Phase 3 editor
        # User can request specific focus or style
        pass