# OpenSessionScribe Configuration Reference

This document covers all configuration options and best practices for OpenSessionScribe.

## Configuration Methods

### 1. Command Line Arguments

Override any setting directly via CLI:

```bash
python -m cli.main process URL \
    --whisper-model large-v3 \
    --ocr-engine paddle \
    --vlm-model qwen2-vl \
    --force-cpu \
    --no-descriptions \
    --verbose
```

### 2. Configuration Files

Create a YAML configuration file:

```yaml
# config.yaml
hardware:
  force_cpu: false
  device: auto  # auto, cuda, mps, cpu

models:
  whisper_model: large-v3
  diarization_model: "pyannote/speaker-diarization-3.1"
  ocr_engine: paddle
  vlm_model: qwen2-vl

processing:
  enable_slides: true
  enable_descriptions: true
  offline_only: true

paths:
  models_dir: ~/.opensessionscribe/models
  cache_dir: ~/.opensessionscribe/cache
  
logging:
  level: INFO
  verbose: false
```

Load with:
```bash
python -m cli.main process URL --config config.yaml
```

### 3. Environment Variables

Set via environment variables with `OPENSESSIONSCRIBE_` prefix:

```bash
export OPENSESSIONSCRIBE_WHISPER_MODEL=large-v3
export OPENSESSIONSCRIBE_FORCE_CPU=false
export OPENSESSIONSCRIBE_MODELS_DIR=/custom/models/path
```

### 4. Python API

```python
from opensessionscribe.config import Config

config = Config(
    whisper_model="large-v3",
    enable_slides=True,
    force_cpu=False
)
```

## Configuration Options

### Hardware Settings

#### `force_cpu` (bool, default: False)
Force CPU processing even if GPU is available.

```bash
# CLI
--force-cpu

# YAML
hardware:
  force_cpu: true
```

**When to use**: 
- GPU memory issues
- Debugging
- Consistent results across environments

#### `device` (str, default: "auto")
Specify processing device explicitly.

**Options**: `auto`, `cuda`, `mps`, `cpu`

```yaml
hardware:
  device: cuda  # Force CUDA GPU
```

**Notes**:
- `auto`: Automatically detect best available device
- `cuda`: Nvidia GPU with CUDA
- `mps`: Apple Silicon GPU (Metal Performance Shaders)
- `cpu`: CPU processing only

### Model Configuration

#### `whisper_model` (str, default: auto-detected)
Whisper model size for speech recognition.

**Options**: `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`

```bash
# Quality vs Speed comparison
--whisper-model tiny      # Fastest, lowest quality
--whisper-model base      # Good balance for testing
--whisper-model small     # Recommended minimum
--whisper-model medium    # Good quality/speed balance
--whisper-model large-v2  # High quality
--whisper-model large-v3  # Best quality, slower
```

**Hardware Recommendations**:
- **4GB RAM**: `tiny` or `base`
- **8GB RAM**: `small` or `medium` 
- **16GB+ RAM**: `large-v2` or `large-v3`
- **GPU**: Can handle larger models efficiently

#### `diarization_model` (str, default: "pyannote/speaker-diarization-3.1")
PyAnnote model for speaker diarization.

```yaml
models:
  diarization_model: "pyannote/speaker-diarization-3.1"
```

**Note**: Requires HuggingFace authentication for full functionality.

#### `ocr_engine` (str, default: "paddle")
OCR engine for text extraction from slides.

**Options**: `paddle`, `tesseract`

```bash
--ocr-engine paddle     # Higher quality, slower startup
--ocr-engine tesseract  # Faster startup, good quality
```

**Comparison**:
- **PaddleOCR**: Better accuracy, supports more languages, requires more RAM
- **Tesseract**: Faster, lighter, good for English text

#### `vlm_model` (str, default: "qwen2-vl")
Vision-Language Model for slide descriptions.

**Options**: `qwen2-vl`, `qwen2.5-vl`, `llava`, `bakllava`

```bash
--vlm-model qwen2-vl    # Recommended, good balance
--vlm-model llava       # Alternative, different strengths
```

**Requirements**: 
- Requires Ollama service running
- Models must be pulled: `ollama pull qwen2-vl`

### Processing Options

#### `enable_slides` (bool, default: True)
Enable slide extraction and processing from videos.

```bash
--slides / --no-slides
```

**Impact**:
- Disabled: Faster processing, audio-only output
- Enabled: Full video analysis with slide extraction

#### `enable_descriptions` (bool, default: True)
Generate AI descriptions for extracted slides.

```bash
--descriptions / --no-descriptions
```

**Requirements**:
- Requires `enable_slides=True`
- Requires Ollama service and VLM model
- Significantly increases processing time

#### `offline_only` (bool, default: True)
Disable network requests after initial download.

```yaml
processing:
  offline_only: true
```

**Note**: Currently only affects yt-dlp behavior.

### Path Configuration

#### `models_dir` (str, default: "~/.opensessionscribe/models")
Directory for storing AI models.

```yaml
paths:
  models_dir: /custom/models/directory
```

**Requirements**:
- Must be writable
- Needs sufficient space (models can be several GB)

#### `cache_dir` (str, default: "~/.opensessionscribe/cache")
Directory for temporary files and caches.

```yaml
paths:
  cache_dir: /fast/ssd/cache
```

**Recommendations**:
- Use SSD for better performance
- Ensure adequate free space

#### `output_dir` (str, CLI only)
Default output directory for processed packages.

```bash
--output /path/to/output/directory
```

### Logging Configuration

#### `verbose` (bool, default: False)
Enable verbose logging output.

```bash
--verbose  # or -v
```

**Effect**: Shows detailed processing steps, useful for debugging.

#### `log_level` (str, default: "INFO")
Set logging level programmatically.

```python
config = Config(log_level="DEBUG")
```

**Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## Configuration Profiles

### Development Profile

```yaml
# config-dev.yaml
hardware:
  force_cpu: true  # Consistent results

models:
  whisper_model: small  # Faster for testing
  ocr_engine: tesseract

processing:
  enable_slides: true
  enable_descriptions: false  # Skip VLM for speed

logging:
  level: DEBUG
  verbose: true
```

### Production Profile

```yaml
# config-prod.yaml
hardware:
  device: auto  # Use best available

models:
  whisper_model: large-v3  # Best quality
  ocr_engine: paddle

processing:
  enable_slides: true
  enable_descriptions: true

paths:
  models_dir: /opt/opensessionscribe/models
  cache_dir: /tmp/opensessionscribe

logging:
  level: INFO
```

### Fast Processing Profile

```yaml
# config-fast.yaml
models:
  whisper_model: medium  # Balance speed/quality

processing:
  enable_slides: false   # Audio only
  enable_descriptions: false

logging:
  level: WARNING  # Minimal output
```

### High Quality Profile

```yaml
# config-quality.yaml
models:
  whisper_model: large-v3
  ocr_engine: paddle
  vlm_model: qwen2.5-vl

processing:
  enable_slides: true
  enable_descriptions: true

# Ensure HF_TOKEN is set for full PyAnnote
```

## Environment-Specific Configuration

### Docker Configuration

```yaml
# docker-config.yaml
paths:
  models_dir: /app/.opensessionscribe/models
  cache_dir: /app/.opensessionscribe/cache

hardware:
  device: cpu  # Unless NVIDIA Docker runtime

processing:
  offline_only: true  # No network after download
```

### CI/CD Configuration

```yaml
# ci-config.yaml
hardware:
  force_cpu: true

models:
  whisper_model: tiny  # Fastest for testing

processing:
  enable_descriptions: false  # No Ollama in CI

logging:
  level: DEBUG
  verbose: true
```

### Batch Processing Configuration

```yaml
# batch-config.yaml
models:
  whisper_model: medium  # Balance for many files

processing:
  enable_slides: true
  enable_descriptions: false  # Too slow for batch

paths:
  cache_dir: /fast/batch/cache

logging:
  level: WARNING  # Less output for batch jobs
```

## Advanced Configuration

### Custom Model Paths

For custom or fine-tuned models:

```yaml
models:
  whisper_model: /path/to/custom/whisper/model
  custom_models:
    custom_asr: /path/to/custom/asr
```

### Resource Limits

```yaml
resources:
  max_memory_gb: 8
  max_gpu_memory_gb: 4
  max_concurrent_jobs: 2
```

### Processing Hooks

```yaml
hooks:
  pre_processing:
    - validate_input
    - check_duration
  post_processing:
    - compress_output
    - upload_results
```

## Configuration Validation

The system validates all configuration on startup:

```python
from opensessionscribe.config import Config

try:
    config = Config.from_yaml("config.yaml")
    config.validate()  # Explicit validation
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

**Common Validation Errors**:
- Invalid model names
- Non-existent directories
- Incompatible settings
- Missing dependencies

## Best Practices

### 1. Hardware-Specific Configs

Create configurations matched to your hardware:

```bash
# Check capabilities first
python -m cli.main hardware

# Create appropriate config
cp config-templates/gpu-config.yaml my-config.yaml
```

### 2. Project-Specific Configs

Keep configurations with your projects:

```
my-project/
├── videos/
├── config.yaml        # Project-specific settings
└── output/
```

### 3. Environment Variables for Secrets

```bash
# Don't put tokens in config files
export HF_TOKEN=your_huggingface_token
export OPENAI_API_KEY=your_api_key  # Future use
```

### 4. Configuration Inheritance

```yaml
# base-config.yaml
base: &base
  hardware:
    device: auto
  paths:
    models_dir: ~/.opensessionscribe/models

# Override for specific use
<<: *base
models:
  whisper_model: large-v3
```

### 5. Version Control

```bash
# .gitignore
config-local.yaml
*.secret.yaml
.opensessionscribe/
output/
```

Track only template configurations, not personal settings.

## Migration Guide

### From CLI-only to Config Files

```bash
# Old way
python -m cli.main process URL --whisper-model large-v3 --no-descriptions --force-cpu

# New way - create config.yaml:
models:
  whisper_model: large-v3
processing:
  enable_descriptions: false
hardware:
  force_cpu: true

# Then use:
python -m cli.main process URL --config config.yaml
```

### Updating Model Versions

When new models are released:

```yaml
# Update model versions
models:
  whisper_model: large-v4  # When available
  vlm_model: qwen3-vl      # Future versions
```

The system will automatically download new models as needed.

## Troubleshooting Configuration

### Debug Configuration Loading

```bash
python -c "
from opensessionscribe.config import Config
config = Config.auto_detect()
print(config.model_dump_json(indent=2))
"
```

### Check Effective Configuration

```bash
python -m cli.main check --config your-config.yaml
```

### Validate Model Availability

```bash
python -c "
from opensessionscribe.config import Config
from opensessionscribe.hardware import HardwareDetector

config = Config.from_yaml('config.yaml')
summary = HardwareDetector.get_hardware_summary()
print('Recommended:', summary['recommendations'])
print('Your config:', config.whisper_model)
"
```

This configuration reference provides comprehensive coverage of all options and usage patterns.