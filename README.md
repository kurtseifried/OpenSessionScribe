# OpenSessionScribe

Local podcast and webinar processing toolkit that converts audio/video content into structured JSON packages with transcripts, speaker diarization, and slide analysis.

## Features

- 🎙️ **Podcast Processing**: Accurate transcription with speaker diarization
- 🖥️ **Webinar Analysis**: Slide extraction, OCR, and AI-generated descriptions  
- 🔒 **Privacy-First**: 100% local processing after model download
- 🚀 **Hardware Optimized**: Auto-detects GPU/CPU capabilities for optimal performance
- 📊 **Structured Output**: Deterministic JSON with checksums and manifests

## Quick Start

```bash
# Install
pip install opensessionscribe

# Process a YouTube video
opensessionscribe process https://youtu.be/VIDEO_ID --output ./results/

# Process a podcast
opensessionscribe process https://podcast.com/feed.xml --episode-latest --output ./results/

# Check system capabilities
opensessionscribe hardware
```

## Output Structure

```
results/
├── package.json          # Complete transcript + metadata
├── media.mp4             # Downloaded video/audio
├── slides/               # Extracted slide images
│   ├── slide_001.jpg
│   └── slide_002.jpg
└── manifest.json         # File checksums
```

## Installation

### macOS Quick Setup

```bash
# 1. Install system dependencies
./install-deps.sh

# 2. Install Python package
pip install -e .

# 3. Download AI models
./scripts/setup-models.sh

# 4. Verify installation
./scripts/check-deps.py
```

### Manual Installation

**Requirements:**
- Python 3.9+
- FFmpeg (audio/video processing)
- Tesseract OCR (text extraction)
- Ollama (AI descriptions)
- 8GB+ RAM recommended

**Using Homebrew (macOS):**
```bash
brew bundle  # Install from Brewfile
```

**Using package managers (Linux):**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg tesseract-ocr

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

### Development Setup

```bash
git clone https://github.com/kurtseifried/OpenSessionScribe
cd OpenSessionScribe
./install-deps.sh        # Install system deps
pip install -e ".[dev]"  # Install Python package
./scripts/setup-models.sh # Download AI models
```

## Models

OpenSessionScribe uses local models for all processing:

- **ASR**: WhisperX (small/medium/large-v3 based on hardware)
- **Diarization**: pyannote.audio 3.1
- **OCR**: PaddleOCR (primary) + Tesseract (fallback) 
- **VLM**: Ollama (Qwen2.5-VL or LLaVA)

Models are automatically downloaded on first use (requires internet).

## Roadmap

- **Phase 1** ✅: Core URL processing pipeline
- **Phase 2** 🚧: Web interface + local file support
- **Phase 3** 📋: Interactive transcript editor

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.