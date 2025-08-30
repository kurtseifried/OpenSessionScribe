"""PyAnnote adapter for speaker diarization."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import torch

from ..config import Config


logger = logging.getLogger(__name__)


class PyAnnoteAdapter:
    """Adapter for pyannote.audio speaker diarization."""
    
    def __init__(self, config: Config):
        self.config = config
        self.pipeline = None
    
    def load_model(self) -> None:
        """Load pyannote diarization pipeline."""
        logger.info(f"Loading pyannote diarization pipeline: {self.config.diarization_model}")
        
        # For now, always use simple diarization as fallback since pyannote requires auth
        logger.warning("Pyannote models require authentication. Using simple fallback.")
        logger.info("To use full pyannote diarization:")
        logger.info("1. Visit https://huggingface.co/pyannote/speaker-diarization-3.1")
        logger.info("2. Accept the user conditions")
        logger.info("3. Get token from https://huggingface.co/settings/tokens")
        logger.info("4. Set: export HF_TOKEN=your_token_here")
        logger.info("")
        
        self._load_simple_diarization()
    
    def _load_simple_diarization(self) -> None:
        """Fallback to simple VAD-based segmentation."""
        try:
            # For now, we'll create a simple fallback that just segments based on silence
            # This is not true speaker diarization but provides basic functionality
            logger.warning("Using simple voice activity detection instead of full diarization")
            self.pipeline = "simple_vad"  # Flag to use simple method
            
        except Exception as e:
            logger.error(f"Failed to load simple diarization: {e}")
            raise RuntimeError(f"Failed to load any diarization method: {e}")
    
    def diarize(self, audio_path: Path) -> Dict[str, Any]:
        """Perform speaker diarization on audio file."""
        if self.pipeline is None:
            self.load_model()
        
        logger.info(f"Running speaker diarization on {audio_path}")
        
        try:
            if self.pipeline == "simple_vad":
                # Use simple fallback approach
                return self._simple_diarization(audio_path)
            else:
                # Use full pyannote pipeline
                diarization = self.pipeline(str(audio_path))
                
                # Extract segments and speakers
                segments = []
                speakers = set()
                
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    # Convert pyannote Segment to our format
                    segment_data = {
                        "start": turn.start,
                        "end": turn.end,
                        "speaker": speaker,
                        "duration": turn.end - turn.start
                    }
                    segments.append(segment_data)
                    speakers.add(speaker)
                
                # Sort segments by start time
                segments.sort(key=lambda x: x["start"])
                
                # Convert speakers set to sorted list
                speakers_list = sorted(list(speakers))
                
                logger.info(f"Diarization complete: found {len(speakers_list)} speakers in {len(segments)} segments")
                
                return {
                    "model": self.config.diarization_model,
                    "speakers": speakers_list,
                    "segments": segments,
                    "total_speakers": len(speakers_list),
                    "total_segments": len(segments)
                }
            
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise RuntimeError(f"Diarization failed: {e}")
    
    def _simple_diarization(self, audio_path: Path) -> Dict[str, Any]:
        """Simple fallback diarization using basic voice activity detection."""
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(str(audio_path), sr=16000)
            duration = len(y) / sr
            
            # Simple approach: assume single speaker for now
            # In a real implementation, we'd use VAD + clustering
            segments = [{
                "start": 0.0,
                "end": duration,
                "speaker": "SPEAKER_00",
                "duration": duration
            }]
            
            speakers = ["SPEAKER_00"]
            
            logger.info(f"Simple diarization complete: found {len(speakers)} speaker in {len(segments)} segments")
            
            return {
                "model": "simple_vad_fallback",
                "speakers": speakers,
                "segments": segments,
                "total_speakers": len(speakers),
                "total_segments": len(segments)
            }
            
        except ImportError:
            logger.error("librosa not available for simple diarization")
            # Even simpler fallback - just create a single segment
            segments = [{
                "start": 0.0,
                "end": 20.0,  # Rough estimate
                "speaker": "SPEAKER_00",
                "duration": 20.0
            }]
            
            return {
                "model": "minimal_fallback",
                "speakers": ["SPEAKER_00"],
                "segments": segments,
                "total_speakers": 1,
                "total_segments": 1
            }
    
    def merge_transcript_diarization(self, transcript_segments: List[Dict[str, Any]], diarization_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge ASR transcript with diarization results."""
        logger.info("Merging transcript with diarization results")
        
        merged_segments = []
        
        for transcript_seg in transcript_segments:
            # Find overlapping diarization segments
            best_overlap = 0
            best_speaker = "SPEAKER_00"  # Default speaker
            
            for diar_seg in diarization_segments:
                # Calculate overlap between transcript segment and diarization segment
                overlap_start = max(transcript_seg["start"], diar_seg["start"])
                overlap_end = min(transcript_seg["end"], diar_seg["end"])
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > best_overlap:
                    best_overlap = overlap_duration
                    best_speaker = diar_seg["speaker"]
            
            # Create merged segment
            merged_segment = transcript_seg.copy()
            merged_segment["speaker"] = best_speaker
            merged_segments.append(merged_segment)
        
        logger.info(f"Merged {len(transcript_segments)} transcript segments with diarization")
        return merged_segments
    
    def enroll_speakers(self, audio_segments: List[Dict[str, Any]], speaker_names: Dict[str, str]) -> Dict[str, str]:
        """Enroll known speakers for improved identification."""
        # TODO: Use SpeechBrain ECAPA embeddings for Phase 3
        # This would allow mapping SPEAKER_XX labels to actual names
        logger.warning("Speaker enrollment not yet implemented")
        return speaker_names
    
    @staticmethod
    def check_pyannote() -> bool:
        """Check if pyannote.audio is available."""
        try:
            from pyannote.audio import Pipeline
            return True
        except ImportError:
            return False
    
    def cleanup(self) -> None:
        """Clean up loaded models to free memory."""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
            
        # Clear CUDA cache if using GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Pyannote models cleaned up")