# TorchCodec Migration Plan

## Background

TorchAudio is deprecating decoding/encoding functionality in favor of TorchCodec as part of PyTorch's media processing consolidation effort.

**Timeline:**
- TorchAudio 2.8 (August 2025): Deprecation warnings
- TorchAudio 2.9 (End 2025): Full removal of deprecated APIs

## Current Status (Early 2025)

### TorchCodec Capabilities
- ✅ Audio decoding fully supported
- ✅ Video decoding fully supported  
- ✅ macOS support (recently added)
- ✅ CUDA GPU acceleration available
- ⚠️ Still in early development - APIs may change

### Installation
```bash
pip install torchcodec
# For CUDA support:
pip install torchcodec --index-url=https://download.pytorch.org/whl/cu126
```

## Migration Opportunities

### 1. FFmpeg Replacement in `opensessionscribe/utils/ffmpeg.py`

**Current approach:**
```python
def extract_audio(self, video_path: Path, audio_path: Path, sample_rate: int = 16000):
    subprocess.run([...ffmpeg command...])
```

**TorchCodec approach:**
```python
from torchcodec import AudioDecoder

def extract_audio_torchcodec(self, video_path: Path, audio_path: Path, sample_rate: int = 16000):
    decoder = AudioDecoder(str(video_path))
    audio_tensor = decoder.decode()  # Returns PyTorch tensor
    # Convert tensor to audio file format expected by WhisperX
```

### 2. Video Frame Extraction

**Current approach:**
```python
def extract_frame(self, video_path: Path, timestamp: float, output_path: Path):
    subprocess.run([...ffmpeg command...])
```

**TorchCodec approach:**
```python
from torchcodec import VideoDecoder

def extract_frame_torchcodec(self, video_path: Path, timestamp: float, output_path: Path):
    decoder = VideoDecoder(str(video_path))
    frame_tensor = decoder.get_frame_at(timestamp)
    # Convert tensor to image format
```

## Current Blockers

1. **WhisperX Dependency**: Still requires TorchAudio, creating potential conflicts
2. **API Stability**: TorchCodec APIs still evolving
3. **Tensor Conversion**: Need to handle PyTorch tensor → file format conversions
4. **Testing Required**: Extensive testing needed for audio quality/compatibility

## Recommended Timeline

### Phase 1 (Current): **No Action**
- Continue with stable FFmpeg subprocess approach
- Monitor upstream dependency migrations (WhisperX, SpeechBrain)
- Track TorchCodec API stabilization

### Phase 2 (Mid-2025): **Evaluation**
- When WhisperX migrates to TorchCodec
- When TorchCodec APIs stabilize (post-1.0?)
- Performance benchmarking vs current FFmpeg approach

### Phase 3 (Late 2025+): **Migration**
- Implement TorchCodec adapters alongside existing FFmpeg
- A/B test performance and quality
- Gradual migration with fallbacks

## Implementation Notes

### Benefits of Migration
- **Performance**: GPU-accelerated decoding
- **Integration**: Native PyTorch tensor workflow  
- **Memory**: Avoid subprocess overhead
- **Future-proofing**: Aligned with PyTorch ecosystem direction

### Challenges
- **Complexity**: Tensor handling vs simple file operations
- **Dependencies**: Additional package requirements
- **Compatibility**: Ensure same output quality as FFmpeg
- **Error Handling**: Different error patterns than subprocess

## Action Items

- [ ] Monitor TorchCodec release notes for API stability
- [ ] Track WhisperX migration to TorchCodec
- [ ] Create experimental branch for TorchCodec integration
- [ ] Benchmark performance: TorchCodec vs FFmpeg subprocess
- [ ] Test audio quality: ensure bit-perfect compatibility
- [ ] Design adapter pattern for gradual migration

## Related Files
- `opensessionscribe/utils/ffmpeg.py` - Primary migration target
- `opensessionscribe/slides/detector.py` - Frame extraction
- `requirements.txt` - Dependencies
- `opensessionscribe/hardware.py` - GPU detection integration

## References
- [TorchAudio Deprecation Issue](https://github.com/pytorch/audio/issues/3902)
- [TorchCodec Documentation](https://docs.pytorch.org/torchcodec/stable/index.html)
- [TorchCodec GitHub](https://github.com/pytorch/torchcodec)
- [PyTorch TorchCodec Blog Post](https://pytorch.org/blog/torchcodec/)