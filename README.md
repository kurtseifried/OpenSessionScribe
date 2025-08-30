# OpenSessionScribe

A local podcast and webinar processing toolkit that transforms audio/video content into structured, searchable packages with transcription, speaker diarization, and slide analysis.

## Features

### Phase 1 (Current) - Core Processing Pipeline
- **🎥 Media Download**: Supports YouTube and any yt-dlp compatible sources
- **🎙️ Speech Recognition**: WhisperX with word-level timestamps and forced alignment
- **👥 Speaker Diarization**: PyAnnote with intelligent fallbacks
- **📽️ Slide Processing**: Automatic detection, OCR, and VLM descriptions
- **📦 Package Generation**: Structured JSON output with file integrity manifest
- **🔧 Hardware Optimization**: Auto-detects GPU/MPS/CPU for optimal performance
- **🚀 CLI Interface**: Complete command-line toolkit for all operations

### Upcoming Phases
- **Phase 2**: Web interface for file uploads and processing management
- **Phase 3**: Interactive editor for transcript/slide cleanup and enhancement

## Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg
- yt-dlp
- (Optional) CUDA GPU for accelerated processing

### Installation

#### Option 1: Quick Setup (Recommended)
```bash
# Clone repository
git clone https://github.com/kurtseifried/OpenSessionScribe.git
cd OpenSessionScribe

# Run setup script (macOS/Linux)
./scripts/setup.sh
```

#### Option 2: Docker
```bash
# Build and run with Docker
docker build -t opensessionscribe .
docker run -v $(pwd)/output:/app/output opensessionscribe \
    process "https://youtube.com/watch?v=example"
```

#### Option 3: Manual Installation
```bash
# Install system dependencies (macOS with Homebrew)
brew install ffmpeg yt-dlp tesseract

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -m cli.main check
```

### Basic Usage

#### Process a URL (Complete Pipeline)
```bash
# Basic processing - audio + transcript + slides
python -m cli.main process "https://youtube.com/watch?v=example" \
    --output ./my_output

# Advanced options
python -m cli.main process "https://youtube.com/watch?v=example" \
    --output ./my_output \
    --whisper-model large-v3 \
    --ocr-engine paddle \
    --vlm-model qwen2-vl \
    --verbose
```

#### Test Individual Components
```bash
# Check system capabilities
python -m cli.main hardware

# Test transcription only
python -m cli.main transcribe audio_file.wav

# Test speaker diarization
python -m cli.main diarize audio_file.wav

# Test slide processing
python -m cli.main slides video_file.mp4

# Combined transcription + diarization
python -m cli.main process_combined audio_file.wav
```

## Output Structure

OpenSessionScribe generates a structured package for each processed item:

```
my_output/
├── package.json              # Main structured output (see schema below)
├── My Video Title.mp4        # Original downloaded media
├── audio.wav                 # Extracted audio (16kHz, mono)
├── transcript_raw.json       # Raw WhisperX output
├── diarization_raw.json      # Raw PyAnnote output  
├── slides_raw.json           # Raw slide processing data
├── My Video Title.info.json  # Source metadata from yt-dlp
└── slides/                   # Extracted slide images
    ├── slide_000.jpg
    ├── slide_001.jpg
    └── ...
```

### Package Schema

The main `package.json` contains:

```json
{
  "schema_version": "0.1",
  "source": {
    "type": "video|audio",
    "url": "https://...",
    "downloaded_at": "2024-01-01T00:00:00",
    "media_file": "filename.mp4",
    "duration_sec": 1200.5,
    "has_video": true
  },
  "transcript": {
    "model": "large-v3",
    "diarization_model": "pyannote/speaker-diarization-3.1", 
    "language": "en",
    "segments": [
      {
        "id": "seg_000001",
        "start": 0.0,
        "end": 5.2,
        "speaker": "SPEAKER_00",
        "text": "Hello, welcome to...",
        "words": [
          {"start": 0.0, "end": 0.5, "text": "Hello", "conf": 0.98}
        ]
      }
    ]
  },
  "slides": [
    {
      "index": 0,
      "timestamp": 30.5,
      "image_path": "slides/slide_000.jpg",
      "ocr": {
        "engine": "paddleocr",
        "text": "Slide title and content...",
        "confidence": 0.89,
        "blocks": []
      },
      "description": "Overview slide showing...",
      "bullets": ["Key point 1", "Key point 2"]
    }
  ],
  "speakers": [
    {"label": "SPEAKER_00", "name": null, "method": "diarization"}
  ],
  "manifest": {
    "hashes": [
      {"path": "audio.wav", "sha256": "abc123...", "size": 610112}
    ]
  }
}
```

## Configuration

### Hardware Optimization
OpenSessionScribe automatically detects your hardware and optimizes processing:

- **GPU (CUDA)**: Nvidia GPUs for WhisperX and PyAnnote acceleration  
- **GPU (MPS)**: Apple Silicon Macs use Metal Performance Shaders
- **CPU**: Fallback with optimized threading

Override with:
```bash
python -m cli.main process URL --force-cpu
```

### Model Selection
```bash
# Whisper models (quality vs speed tradeoff)
--whisper-model tiny|base|small|medium|large-v2|large-v3

# OCR engines  
--ocr-engine paddle|tesseract

# VLM models (requires Ollama)
--vlm-model qwen2-vl|llava|bakllava
```

### Advanced Configuration

Create `config.yaml`:
```yaml
# Hardware
force_cpu: false
device: auto  # auto, cuda, mps, cpu

# Models
whisper_model: large-v3
diarization_model: "pyannote/speaker-diarization-3.1"
ocr_engine: paddle  
vlm_model: qwen2-vl

# Processing
enable_slides: true
enable_descriptions: true
offline_only: true

# Paths  
models_dir: ~/.opensessionscribe/models
cache_dir: ~/.opensessionscribe/cache
```

Load with:
```bash
python -m cli.main process URL --config config.yaml
```

## Dependencies

### Required System Dependencies
- **FFmpeg**: Audio/video processing (`brew install ffmpeg`)
- **yt-dlp**: Media download (`brew install yt-dlp`)

### Optional System Dependencies  
- **Tesseract**: OCR fallback (`brew install tesseract`)
- **Ollama**: Local VLM descriptions (`brew install ollama`)

### Python Dependencies
Core packages installed automatically:
- `whisperx`: Speech recognition with alignment
- `pyannote-audio`: Speaker diarization
- `paddleocr`: Primary OCR engine
- `typer`: CLI framework
- `pydantic`: Data validation
- `PyYAML`: Configuration

See `requirements.txt` for complete list.

## Troubleshooting

### Common Issues

#### WhisperX/PyAnnote FFmpeg Library Warnings
```
OSError: dlopen(...libtorio_ffmpeg6.so...) Library not loaded: @rpath/libavutil.58.dylib
```
**Solution**: These are harmless warnings. Processing continues with software fallbacks.

#### PyAnnote Authentication Required
```
WARNING: Pyannote models require authentication. Using simple fallback.
```
**Solution**: For full speaker diarization:
1. Visit https://huggingface.co/pyannote/speaker-diarization-3.1
2. Accept user conditions  
3. Get token from https://huggingface.co/settings/tokens
4. Set: `export HF_TOKEN=your_token_here`

#### PaddleOCR Initialization Failed
```
ERROR: Failed to initialize PaddleOCR: Unknown argument: use_gpu
```
**Solution**: Automatically falls back to Tesseract. Update PaddleOCR or use `--ocr-engine tesseract`.

#### Ollama Not Available
```
❌ ollama service not available
```
**Solution**: 
```bash
# Install and start Ollama
brew install ollama
ollama serve

# Pull VLM model
ollama pull qwen2-vl
```

### Performance Tips

#### Faster Processing
- Use smaller Whisper models: `--whisper-model medium`  
- Disable slides: `--no-slides`
- Disable descriptions: `--no-descriptions`
- Use GPU acceleration (auto-detected)

#### Better Quality  
- Use larger Whisper models: `--whisper-model large-v3`
- Enable full PyAnnote diarization (requires HF token)
- Use PaddleOCR: `--ocr-engine paddle`

### Getting Help

```bash
# General help
python -m cli.main --help

# Command-specific help  
python -m cli.main process --help
python -m cli.main transcribe --help

# System diagnostics
python -m cli.main check
python -m cli.main hardware
```

## Development

### Project Structure
```
opensessionscribe/
├── cli/                  # Command-line interface
├── opensessionscribe/    # Core package
│   ├── asr/             # Speech recognition  
│   ├── diarize/         # Speaker diarization
│   ├── slides/          # Slide processing
│   ├── ingest/          # Media download
│   ├── utils/           # Utilities
│   └── schemas/         # Data models
├── scripts/             # Setup and utility scripts
├── docker/              # Docker configuration
└── docs/                # Documentation
```

### Running Tests
```bash
# System check
python -m cli.main check

# Component tests
python -m cli.main transcribe test_audio.wav
python -m cli.main slides test_video.mp4

# End-to-end test
python -m cli.main process "https://youtube.com/watch?v=jNQXAC9IVRw" \
    --output test_output --verbose
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Roadmap

### Phase 2 - Web Interface (Planned)
- FastAPI web server
- File upload interface  
- Processing queue management
- Results browser

### Phase 3 - Interactive Editor (Planned)  
- Transcript editing with speaker assignment
- Slide reprocessing and description editing
- Export to various formats (SRT, PDF, etc.)
- Speaker enrollment and recognition

### Future Enhancements
- Multi-language support
- Custom model fine-tuning
- Advanced slide template detection
- Integration with popular platforms

---

**OpenSessionScribe** - Transform your audio and video content into structured, searchable knowledge.