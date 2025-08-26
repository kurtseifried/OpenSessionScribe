# OpenSessionScribe — Revised Implementation Plan

## Overview

Python-based system using best-of-breed open source tools (yt-dlp, WhisperX, pyannote, etc.) to convert podcasts, webinars, and videos into structured JSON packages with transcripts, speaker diarization, and slide analysis.

## Three-Phase Implementation

### Phase 1: URL Processing Pipeline
**Goal**: Core processing pipeline that takes URLs and produces structured output

**Input Sources**:
- Any URL supported by yt-dlp (YouTube, Vimeo, podcasts, etc.)
- RSS/podcast feeds

**Output Structure**:
```
project_folder/
├── media.mp4                 # Downloaded video/audio file
├── transcript.json           # Complete package JSON
└── slides/                   # Extracted slide images
    ├── slide_001.jpg
    ├── slide_002.jpg
    └── ...
```

**Processing Flow** (Sequential):
1. **Ingest**: yt-dlp downloads media, extract/normalize audio
2. **Transcript**: WhisperX ASR → speaker diarization → merge
3. **Slides**: Scene detection → frame extraction → deduplication → OCR → VLM descriptions

**Hardware Detection & Model Selection**:
- **GPU Available** (CUDA/MPS): Whisper large-v3, full pyannote models
- **High RAM** (16GB+, CPU-only): Whisper medium, standard models  
- **Lower Specs**: Whisper small/base, lighter models
- **CLI Override**: `--whisper-model`, `--force-cpu`, etc.

### Phase 2: Local File Support + Web Interface
**Goal**: Expand input sources and add basic web UI

**Additional Inputs**:
- Local video files (MP4, AVI, etc.)
- Local audio files (MP3, WAV, etc.) 
- Web upload interface

**Web UI**:
- Simple upload form
- Job queue with progress
- Download processed results

### Phase 3: Interactive Editor
**Goal**: Three-pane editor for manual cleanup and refinement

**Features**:
- **Left**: Media player with waveform
- **Middle**: Editable transcript with speaker labels
- **Right**: Slide viewer with OCR text editing
- Real-time sync between panes
- Export refined results

## Technical Stack

**Core Dependencies**:
- `yt-dlp` - Media download
- `whisperx` - ASR + forced alignment  
- `pyannote.audio` - Speaker diarization
- `PySceneDetect` - Slide detection
- `PaddleOCR` - OCR (primary)
- `tesseract` - OCR (fallback)
- `ollama` - Local VLM for slide descriptions
- `ffmpeg` - Audio/video processing

**Framework**:
- `FastAPI` - Web API (Phase 2+)
- `Typer` - CLI interface
- `Pydantic` - Data validation/schemas
- `Dramatiq + Redis` - Background jobs (Phase 2+)

## Data Model

### Core JSON Structure
```json
{
  "schema_version": "0.1",
  "source": {
    "type": "podcast|webinar|video",
    "url": "https://...",
    "downloaded_at": "2025-08-26T...",
    "media_file": "media.mp4",
    "duration_sec": 4567.8
  },
  "transcript": {
    "model": "whisperx-large-v3",
    "diarization_model": "pyannote/speaker-diarization-3.1", 
    "language": "en",
    "segments": [
      {
        "id": "seg_000001",
        "start": 12.34,
        "end": 18.90,
        "speaker": "SPEAKER_01", 
        "text": "Hello everyone...",
        "words": [
          {"start": 12.34, "end": 12.60, "text": "Hello", "conf": 0.98}
        ]
      }
    ]
  },
  "slides": [
    {
      "index": 1,
      "timestamp": 613.2,
      "image_path": "slides/slide_001.jpg",
      "phash": "c87af3...",
      "ocr": {
        "engine": "paddleocr",
        "text": "Slide content here...",
        "confidence": 0.92
      },
      "description": "Chart showing quarterly revenue growth",
      "chart_info": {
        "type": "bar",
        "trend": "upward growth"
      }
    }
  ],
  "manifest": {
    "hashes": [
      {"path": "transcript.json", "sha256": "..."},
      {"path": "slides/slide_001.jpg", "sha256": "..."}
    ]
  }
}
```

## CLI Interface (Phase 1)

### Basic Commands
```bash
# Process YouTube video
opensessionscribe process https://youtu.be/VIDEO_ID --output ./results/

# Process podcast
opensessionscribe process https://podcast.com/feed.xml --episode-latest --output ./results/

# With model override
opensessionscribe process URL --whisper-model medium --output ./results/
```

### Configuration Options
```bash
--whisper-model small|medium|large-v3    # ASR model size
--diarization-model pyannote/speaker-diarization-3.1
--ocr-engine paddle|tesseract             # OCR backend
--vlm qwen2.5-vl|llava                    # VLM for descriptions
--slides/--no-slides                      # Enable/disable slide processing
--force-cpu                               # Disable GPU acceleration
--output DIR                              # Output directory
--offline-only                            # Block network after download
```

## Hardware Detection Logic

```python
def detect_optimal_config():
    has_gpu = detect_cuda() or detect_mps()
    ram_gb = get_system_ram() 
    cpu_cores = get_cpu_count()
    
    if has_gpu and ram_gb >= 8:
        return Config(whisper="large-v3", diarization="full")
    elif ram_gb >= 16:
        return Config(whisper="medium", diarization="standard") 
    else:
        return Config(whisper="small", diarization="light")
```

## Project Structure

```
OpenSessionScribe/
├── opensessionscribe/           # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── hardware.py             # Hardware detection
│   ├── pipeline.py             # Main processing pipeline
│   ├── ingest/                 # yt-dlp integration
│   ├── asr/                    # WhisperX adapter  
│   ├── diarize/               # pyannote integration
│   ├── slides/                # Scene detection, OCR, VLM
│   ├── schemas/               # Pydantic models
│   └── utils/                 # Helpers, ffmpeg, hashing
├── cli/                       # Typer CLI (Phase 1)
├── webapp/                    # FastAPI web UI (Phase 2+)
├── tests/                     # pytest test suite
├── pyproject.toml
├── Dockerfile
└── README.md
```

## Success Criteria

### Phase 1
- [ ] Process YouTube video → complete JSON + slides
- [ ] Process podcast → transcript with speaker diarization  
- [ ] Hardware auto-detection working
- [ ] CLI with basic options functional
- [ ] Deterministic output with checksums

### Phase 2  
- [ ] Upload local files via web interface
- [ ] Background job processing with progress
- [ ] Download results as ZIP

### Phase 3
- [ ] Three-pane editor functional
- [ ] Real-time transcript editing
- [ ] Slide OCR correction interface
- [ ] Export edited results

## Development Priority

1. **Core pipeline skeleton** - basic structure, config, hardware detection
2. **Ingest module** - yt-dlp integration, audio normalization
3. **ASR + diarization** - WhisperX + pyannote integration  
4. **Slide processing** - scene detection, OCR, VLM descriptions
5. **CLI interface** - Typer commands, argument parsing
6. **Testing & validation** - unit tests, sample processing
7. **Phase 2 prep** - FastAPI foundation, job queue setup

## Risk Mitigation

- **Model compatibility**: Pin exact versions, provide fallback options
- **Hardware variability**: Extensive auto-detection + manual overrides
- **Processing failures**: Graceful degradation, partial results, detailed logs
- **Output determinism**: Fixed seeds, checksums, schema validation