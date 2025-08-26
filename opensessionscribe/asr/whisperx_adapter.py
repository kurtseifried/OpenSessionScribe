"""WhisperX adapter for speech recognition with word-level timestamps."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import torch

from ..config import Config


logger = logging.getLogger(__name__)


class WhisperXAdapter:
    """Adapter for WhisperX ASR with forced alignment."""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.align_model = None
        self.metadata = None
    
    def load_models(self) -> None:
        """Load WhisperX models."""
        import whisperx
        
        device = self.config.device if self.config.device else "cpu"
        if self.config.force_cpu:
            device = "cpu"
        
        logger.info(f"Loading WhisperX model '{self.config.whisper_model}' on device '{device}'")
        
        try:
            # Load WhisperX model for transcription
            self.model = whisperx.load_model(
                self.config.whisper_model, 
                device=device,
                compute_type="float16" if device != "cpu" else "int8",
                asr_options={
                    "suppress_numerals": True,
                    "max_new_tokens": None,
                    "clip_timestamps": None,
                    "hallucination_silence_threshold": None,
                }
            )
            
            logger.info(f"WhisperX model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load WhisperX model: {e}")
            raise RuntimeError(f"Failed to load WhisperX model: {e}")
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """Transcribe audio file with word-level timestamps."""
        if self.model is None:
            self.load_models()
        
        logger.info(f"Transcribing {audio_path} with {self.config.whisper_model}")
        
        try:
            import whisperx
            
            # Load audio
            audio = whisperx.load_audio(str(audio_path))
            
            # 1. Transcribe with Whisper model
            result = self.model.transcribe(audio, batch_size=16)
            detected_language = result.get("language", "en")
            
            logger.info(f"Transcription complete. Detected language: {detected_language}")
            logger.info(f"Found {len(result.get('segments', []))} segments")
            
            # 2. Load alignment model for the detected language
            align_model, metadata = self._load_align_model(detected_language)
            
            # 3. Perform forced alignment for word-level timestamps
            if align_model is not None:
                logger.info("Running forced alignment for word-level timestamps")
                aligned_result = whisperx.align(
                    result["segments"], 
                    align_model, 
                    metadata, 
                    audio, 
                    self.config.device or "cpu",
                    return_char_alignments=False
                )
                segments = aligned_result["segments"]
            else:
                logger.warning("Alignment model not available, using segment-level timestamps only")
                segments = result["segments"]
            
            # 4. Structure the output
            processed_segments = []
            all_words = []
            
            for i, segment in enumerate(segments):
                segment_id = f"seg_{i:06d}"
                
                # Extract words with timestamps if available
                words = segment.get("words", [])
                processed_words = []
                
                for word in words:
                    word_data = {
                        "start": word.get("start", segment.get("start", 0)),
                        "end": word.get("end", segment.get("end", 0)),
                        "text": word.get("word", "").strip(),
                        "conf": word.get("score", 0.0)
                    }
                    processed_words.append(word_data)
                    all_words.append(word_data)
                
                # Create segment entry
                segment_data = {
                    "id": segment_id,
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", "").strip(),
                    "speaker": "SPEAKER_00",  # Will be updated by diarization
                    "words": processed_words
                }
                processed_segments.append(segment_data)
            
            logger.info(f"Processed {len(processed_segments)} segments with {len(all_words)} words")
            
            return {
                "model": self.config.whisper_model,
                "language": detected_language,
                "segments": processed_segments,
                "word_segments": all_words,
                "raw_result": result  # Keep original for debugging
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")
    
    def _load_align_model(self, language: str) -> tuple[Any, Any]:
        """Load alignment model for specific language."""
        try:
            import whisperx
            
            device = self.config.device if self.config.device else "cpu"
            if self.config.force_cpu:
                device = "cpu"
            
            # Check if alignment is available for this language
            if language not in whisperx.utils.LANGUAGES:
                logger.warning(f"Alignment not available for language: {language}")
                return None, None
            
            logger.info(f"Loading alignment model for language: {language}")
            align_model, metadata = whisperx.load_align_model(
                language_code=language, 
                device=device
            )
            
            # Cache for potential reuse
            self.align_model = align_model
            self.metadata = metadata
            
            return align_model, metadata
            
        except Exception as e:
            logger.warning(f"Could not load alignment model for {language}: {e}")
            return None, None
    
    def align_segment(self, audio_path: Path, text: str, start: float, end: float) -> List[Dict[str, Any]]:
        """Re-align a specific segment after editing."""
        if self.align_model is None or self.metadata is None:
            logger.warning("Alignment model not loaded, cannot re-align segment")
            return []
        
        try:
            import whisperx
            
            # Load audio for the specific segment
            audio = whisperx.load_audio(str(audio_path))
            
            # Create a temporary segment structure
            temp_segment = {
                "start": start,
                "end": end,
                "text": text
            }
            
            # Perform alignment
            aligned_result = whisperx.align(
                [temp_segment],
                self.align_model,
                self.metadata,
                audio,
                self.config.device or "cpu",
                return_char_alignments=False
            )
            
            # Extract word-level alignments
            words = aligned_result["segments"][0].get("words", [])
            
            return [{
                "start": word.get("start", start),
                "end": word.get("end", end),
                "text": word.get("word", "").strip(),
                "conf": word.get("score", 0.0)
            } for word in words]
            
        except Exception as e:
            logger.error(f"Segment re-alignment failed: {e}")
            return []
    
    @staticmethod
    def check_whisperx() -> bool:
        """Check if WhisperX is available."""
        try:
            import whisperx
            return True
        except ImportError:
            return False
    
    def cleanup(self) -> None:
        """Clean up loaded models to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            
        if self.align_model is not None:
            del self.align_model
            self.align_model = None
            
        self.metadata = None
        
        # Clear CUDA cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("WhisperX models cleaned up")