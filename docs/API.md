# OpenSessionScribe API Documentation

This document covers the Python API for programmatic usage of OpenSessionScribe components.

## Core Components

### ProcessingPipeline

The main orchestration class for end-to-end processing.

```python
from opensessionscribe import ProcessingPipeline, Config

# Create configuration
config = Config(
    whisper_model="large-v3",
    enable_slides=True,
    enable_descriptions=True,
    ocr_engine="paddle",
    vlm_model="qwen2-vl"
)

# Initialize pipeline
pipeline = ProcessingPipeline(config)

# Process a URL
package = pipeline.process_url(
    url="https://youtube.com/watch?v=example",
    output_dir="./output"
)

# Access results
print(f"Processed {len(package.transcript.segments)} segments")
print(f"Extracted {len(package.slides)} slides")
```

### Configuration

Flexible configuration system with auto-detection and YAML support.

```python
from opensessionscribe.config import Config

# Auto-detect optimal settings
config = Config.auto_detect()

# Manual configuration
config = Config(
    # Hardware
    force_cpu=False,
    device="auto",  # auto, cuda, mps, cpu
    
    # Models
    whisper_model="large-v3",
    diarization_model="pyannote/speaker-diarization-3.1",
    ocr_engine="paddle",
    vlm_model="qwen2-vl",
    
    # Processing
    enable_slides=True,
    enable_descriptions=True,
    offline_only=True,
    
    # Paths
    models_dir="~/.opensessionscribe/models",
    cache_dir="~/.opensessionscribe/cache"
)

# Load from YAML
config = Config.from_yaml("config.yaml")

# Create default config file
Config.create_default_config("config.yaml")
```

### Hardware Detection

Automatic hardware capability detection and optimization.

```python
from opensessionscribe.hardware import HardwareDetector

# Get hardware summary
summary = HardwareDetector.get_hardware_summary()
print(f"GPU: {summary['gpu']['type']}")
print(f"RAM: {summary['memory']['total_gb']} GB")
print(f"Recommended Whisper model: {summary['recommendations']['whisper_model']}")

# Detect specific capabilities
has_cuda = HardwareDetector.detect_gpu()['cuda_available']
has_mps = HardwareDetector.detect_gpu()['mps_available']
```

## Individual Components

### Speech Recognition (WhisperX)

```python
from opensessionscribe.asr import WhisperXAdapter
from opensessionscribe.config import Config

config = Config(whisper_model="large-v3")
asr = WhisperXAdapter(config)

# Transcribe audio file
result = asr.transcribe("audio.wav")

print(f"Language: {result['language']}")
print(f"Segments: {len(result['segments'])}")
print(f"Words: {len(result['word_segments'])}")

# Access segments
for segment in result['segments']:
    print(f"[{segment['start']:.1f}s-{segment['end']:.1f}s]: {segment['text']}")

# Cleanup models
asr.cleanup()
```

### Speaker Diarization (PyAnnote)

```python
from opensessionscribe.diarize import PyAnnoteAdapter
from opensessionscribe.config import Config

config = Config(diarization_model="pyannote/speaker-diarization-3.1")
diarizer = PyAnnoteAdapter(config)

# Perform diarization
result = diarizer.diarize("audio.wav")

print(f"Found {result['total_speakers']} speakers")
print(f"Speakers: {result['speakers']}")

# Merge with transcript
transcript_segments = [...]  # From WhisperX
diarization_segments = result['segments']

merged = diarizer.merge_transcript_diarization(
    transcript_segments, 
    diarization_segments
)

# Each merged segment has speaker label
for segment in merged:
    print(f"{segment['speaker']}: {segment['text']}")
```

### Slide Processing

```python
from opensessionscribe.slides import SlideProcessor
from opensessionscribe.config import Config

config = Config(
    enable_slides=True,
    enable_descriptions=True,
    ocr_engine="paddle",
    vlm_model="qwen2-vl"
)

processor = SlideProcessor(config)

# Process video for slides
slides = processor.process_video("video.mp4", "./output")

for slide in slides:
    print(f"Slide {slide.index} at {slide.timestamp}s")
    if slide.ocr:
        print(f"  OCR: {slide.ocr.text[:100]}...")
    if slide.description:
        print(f"  Description: {slide.description[:100]}...")
```

#### Individual Slide Components

```python
from opensessionscribe.slides import SlideDetector, OCRProcessor, VLMDescriber

# Slide detection
detector = SlideDetector(config)
timestamps = detector.detect_slides("video.mp4")
print(f"Found slides at: {timestamps}")

# Extract specific frame
detector.extract_frame("video.mp4", 30.0, "slide.jpg")

# OCR processing
ocr = OCRProcessor(config)
result = ocr.process_image("slide.jpg")
print(f"OCR Text: {result.text}")
print(f"Confidence: {result.confidence}")

# VLM descriptions
vlm = VLMDescriber(config)
description = vlm.describe_slide("slide.jpg", result.text)
print(f"Description: {description['description']}")
print(f"Bullets: {description['bullets']}")
```

### Media Download

```python
from opensessionscribe.ingest import MediaDownloader
from opensessionscribe.config import Config

downloader = MediaDownloader(Config())

# Get video info without downloading
info = downloader.get_info("https://youtube.com/watch?v=example")
print(f"Title: {info['title']}")
print(f"Duration: {info['duration']} seconds")

# Download and prepare for processing
media_info = downloader.download("https://youtube.com/watch?v=example", "./output")
print(f"Downloaded: {media_info['media_path']}")
print(f"Audio extracted: {media_info['audio_path']}")
print(f"Has video: {media_info['has_video']}")
```

## Data Structures

### Package Schema

```python
from opensessionscribe.schemas.package import Package, Source, Transcript, Slide

# Complete package structure
package = Package(
    schema_version="0.1",
    source=Source(
        type="video",
        url="https://youtube.com/watch?v=example",
        downloaded_at=datetime.now(),
        media_file="video.mp4",
        duration_sec=1200.5,
        has_video=True
    ),
    transcript=Transcript(
        model="large-v3",
        diarization_model="pyannote/speaker-diarization-3.1",
        language="en",
        segments=[...]
    ),
    slides=[...],
    speakers=[...],
    manifest=Manifest(hashes=[...])
)

# Serialize to JSON
package_dict = package.model_dump()
```

### Transcript Segments

```python
from opensessionscribe.schemas.package import Segment, Word

segment = Segment(
    id="seg_000001",
    start=0.0,
    end=5.2,
    speaker="SPEAKER_00",
    text="Hello, welcome to this presentation",
    words=[
        Word(start=0.0, end=0.5, text="Hello", conf=0.98),
        Word(start=0.6, end=1.2, text="welcome", conf=0.95),
        # ...
    ]
)
```

### Slide Data

```python
from opensessionscribe.schemas.package import Slide, OCRResult, ChartInfo

slide = Slide(
    index=0,
    timestamp=30.5,
    image_path="slides/slide_000.jpg",
    ocr=OCRResult(
        engine="paddleocr",
        text="Slide Title\nBullet point 1\nBullet point 2",
        confidence=0.89,
        blocks=[
            {
                "text": "Slide Title",
                "confidence": 0.95,
                "bbox": {"x": 100, "y": 50, "width": 300, "height": 40}
            }
        ]
    ),
    description="Overview slide showing key points",
    bullets=["Key point 1", "Key point 2"],
    chart=ChartInfo(type="bar", trend="increasing") if chart_detected else None
)
```

## Utility Functions

### FFmpeg Operations

```python
from opensessionscribe.utils.ffmpeg import FFmpegProcessor

ffmpeg = FFmpegProcessor()

# Extract audio
ffmpeg.extract_audio("video.mp4", "audio.wav", sample_rate=16000)

# Get media information
info = ffmpeg.get_media_info("video.mp4")
print(f"Duration: {info['duration']} seconds")
print(f"Has video: {info['has_video']}")

# Extract single frame
ffmpeg.extract_frame("video.mp4", 30.0, "frame.jpg")
```

### File Operations

```python
from opensessionscribe.utils.files import calculate_checksum, ensure_directory

# Calculate file hash
checksum = calculate_checksum("large_file.mp4")

# Ensure directory exists
ensure_directory("path/to/nested/directory")
```

## Error Handling

All components use structured exceptions:

```python
from opensessionscribe.exceptions import (
    ConfigurationError,
    ModelLoadError,
    ProcessingError,
    DependencyError
)

try:
    pipeline = ProcessingPipeline(config)
    result = pipeline.process_url(url, output_dir)
except ConfigurationError as e:
    print(f"Configuration issue: {e}")
except DependencyError as e:
    print(f"Missing dependency: {e}")
except ProcessingError as e:
    print(f"Processing failed: {e}")
```

## Context Managers

For automatic cleanup:

```python
from opensessionscribe import ProcessingPipeline

with ProcessingPipeline(config) as pipeline:
    result = pipeline.process_url(url, output_dir)
    # Models automatically cleaned up on exit
```

## Logging

Configure logging for debugging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Specific logger
logger = logging.getLogger('opensessionscribe')
logger.setLevel(logging.INFO)
```

## Batch Processing

Process multiple URLs:

```python
urls = [
    "https://youtube.com/watch?v=video1",
    "https://youtube.com/watch?v=video2",
    "https://youtube.com/watch?v=video3"
]

results = []
with ProcessingPipeline(config) as pipeline:
    for i, url in enumerate(urls):
        try:
            output_dir = f"./batch_output/{i:03d}"
            result = pipeline.process_url(url, output_dir)
            results.append(result)
            print(f"✅ Processed {i+1}/{len(urls)}: {result.source.media_file}")
        except Exception as e:
            print(f"❌ Failed {i+1}/{len(urls)}: {e}")

print(f"Completed {len(results)}/{len(urls)} items")
```

## Advanced Configuration

### Custom Model Paths

```python
config = Config(
    whisper_model="/path/to/custom/whisper/model",
    models_dir="/custom/models/directory"
)
```

### Performance Tuning

```python
config = Config(
    # Use smaller model for speed
    whisper_model="medium",
    
    # Disable expensive features
    enable_descriptions=False,
    
    # Force CPU to avoid GPU memory issues
    force_cpu=True,
    
    # Limit OCR to Tesseract (faster startup)
    ocr_engine="tesseract"
)
```

### Custom Processing Hooks

```python
class CustomPipeline(ProcessingPipeline):
    def _process_transcript(self, media_info, output_dir):
        # Custom pre-processing
        result = super()._process_transcript(media_info, output_dir)
        
        # Custom post-processing
        self._custom_transcript_cleanup(result)
        
        return result
    
    def _custom_transcript_cleanup(self, result):
        # Remove segments with low confidence
        result['segments'] = [
            seg for seg in result['segments'] 
            if seg.get('confidence', 0) > 0.5
        ]
```

This API documentation provides comprehensive coverage of programmatic usage. For CLI usage, see the main README.md file.