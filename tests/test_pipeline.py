"""Tests for the main processing pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from opensessionscribe.pipeline import ProcessingPipeline
from opensessionscribe.config import Config


class TestProcessingPipeline:
    """Test the main processing pipeline."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(
            whisper_model="small",
            force_cpu=True,
            enable_slides=True,
            enable_descriptions=False,  # Skip VLM for faster tests
            offline_only=True
        )
    
    @pytest.fixture
    def pipeline(self, config):
        """Create pipeline with mocked adapters."""
        with patch.multiple(
            'opensessionscribe.pipeline',
            MediaDownloader=Mock(),
            WhisperXAdapter=Mock(),
            PyAnnoteAdapter=Mock(),
            SlideDetector=Mock(),
            OCRProcessor=Mock(),
            VLMDescriber=Mock()
        ):
            return ProcessingPipeline(config)
    
    def test_pipeline_initialization(self, pipeline, config):
        """Test pipeline initializes with correct config."""
        assert pipeline.config == config
        assert pipeline.downloader is not None
        assert pipeline.asr is not None
        assert pipeline.diarizer is not None
    
    @patch('opensessionscribe.pipeline.logger')
    def test_process_url_workflow(self, mock_logger, pipeline, tmp_path):
        """Test complete URL processing workflow."""
        # Mock media download
        pipeline.downloader.download.return_value = {
            "video_path": tmp_path / "video.mp4",
            "audio_path": tmp_path / "audio.wav", 
            "has_video": True,
            "duration": 120.0
        }
        
        # Mock transcript processing
        pipeline.asr.transcribe.return_value = {"segments": []}
        pipeline.diarizer.diarize.return_value = {"segments": []}
        
        # Mock slide processing  
        pipeline.slide_detector.detect_slides.return_value = [30.0, 60.0, 90.0]
        pipeline.slide_detector.extract_frame = Mock()
        pipeline.ocr.process_image.return_value = {"text": "Sample slide"}
        
        # TODO: Complete test when methods are implemented
        # result = pipeline.process_url("https://example.com/video", tmp_path)
        # assert result is not None