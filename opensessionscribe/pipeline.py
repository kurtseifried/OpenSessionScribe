"""Main processing pipeline orchestration."""

from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import json
import hashlib
from datetime import datetime

from .config import Config
from .schemas.package import Package, Source, Transcript, Segment, Word, Slide, Speaker, Manifest
from .ingest.downloader import MediaDownloader
from .asr.whisperx_adapter import WhisperXAdapter
from .diarize.pyannote_adapter import PyAnnoteAdapter
from .slides.processor import SlideProcessor
from .utils.ffmpeg import FFmpegProcessor


logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Main pipeline for processing podcasts and webinars."""
    
    def __init__(self, config: Config):
        self.config = config
        self.downloader = MediaDownloader(config)
        self.asr = WhisperXAdapter(config)
        self.diarizer = PyAnnoteAdapter(config)
        self.slide_processor = SlideProcessor(config)
        self.ffmpeg = FFmpegProcessor()
    
    def process_url(self, url: str, output_dir: Path) -> Package:
        """Process a URL (YouTube, podcast, etc.) into a complete package."""
        logger.info(f"Starting processing pipeline for URL: {url}")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Phase 1: Download and prepare media
            logger.info("Phase 1: Downloading media...")
            media_info = self.downloader.download(url, output_dir)
            
            # Phase 2: Process transcript with speaker diarization
            logger.info("Phase 2: Processing transcript...")
            transcript_data = self._process_transcript(media_info, output_dir)
            
            # Phase 3: Process slides (if video and enabled)
            slides_data = []
            if media_info.get("has_video") and self.config.enable_slides:
                logger.info("Phase 3: Processing slides...")
                slides_data = self._process_slides(media_info, output_dir)
            
            # Phase 4: Create final package
            logger.info("Phase 4: Creating package...")
            package = self._create_package(url, media_info, transcript_data, slides_data, output_dir)
            
            # Phase 5: Export and generate manifest
            logger.info("Phase 5: Exporting package...")
            self._export_package(package, output_dir)
            
            logger.info(f"Processing complete! Package saved to: {output_dir}")
            return package
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
        finally:
            # Cleanup loaded models
            self._cleanup()
    
    def _process_transcript(self, media_info: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """Process audio for transcript and speaker diarization."""
        audio_path = Path(media_info["audio_path"])
        
        # Run ASR (transcription)
        logger.info("Running speech recognition with WhisperX...")
        transcript_result = self.asr.transcribe(audio_path)
        
        # Run speaker diarization
        logger.info("Running speaker diarization...")
        diarization_result = self.diarizer.diarize(audio_path)
        
        # Merge transcript and diarization
        logger.info("Merging transcript with speaker labels...")
        merged_segments = self.diarizer.merge_transcript_diarization(
            transcript_result['segments'],
            diarization_result['segments']
        )
        
        # Save individual results for debugging/reference
        transcript_file = output_dir / "transcript_raw.json"
        with open(transcript_file, 'w') as f:
            json.dump(transcript_result, f, indent=2, ensure_ascii=False)
            
        diarization_file = output_dir / "diarization_raw.json"
        with open(diarization_file, 'w') as f:
            json.dump(diarization_result, f, indent=2)
        
        return {
            "language": transcript_result["language"],
            "model": transcript_result["model"],
            "diarization_model": diarization_result["model"],
            "segments": merged_segments,
            "speakers": diarization_result["speakers"],
            "word_segments": transcript_result.get("word_segments", [])
        }
    
    def _process_slides(self, media_info: Dict[str, Any], output_dir: Path) -> List[Slide]:
        """Process video for slides, OCR, and descriptions."""
        video_path = Path(media_info["video_path"])
        
        # Use the integrated slide processor
        slides_data = self.slide_processor.process_video(video_path, output_dir)
        
        # Save raw slides data for debugging
        slides_file = output_dir / "slides_raw.json"
        with open(slides_file, 'w') as f:
            slides_dict = [slide.model_dump() for slide in slides_data]
            json.dump(slides_dict, f, indent=2, ensure_ascii=False)
        
        return slides_data
    
    def _create_segments(self, merged_segments: List[Dict[str, Any]]) -> List[Segment]:
        """Convert merged segment data to Segment objects."""
        segments = []
        
        for seg_data in merged_segments:
            # Convert words if present
            words = []
            if 'words' in seg_data:
                for word_data in seg_data['words']:
                    word = Word(
                        start=word_data['start'],
                        end=word_data['end'],
                        text=word_data['text'],
                        conf=word_data.get('conf')
                    )
                    words.append(word)
            
            # Create segment
            segment = Segment(
                id=seg_data.get('id', f"seg_{len(segments):06d}"),
                start=seg_data['start'],
                end=seg_data['end'],
                speaker=seg_data.get('speaker', 'SPEAKER_00'),
                text=seg_data['text'],
                words=words
            )
            segments.append(segment)
        
        return segments
    
    def _create_package(
        self, 
        url: str, 
        media_info: Dict[str, Any], 
        transcript_data: Dict[str, Any], 
        slides_data: List[Slide],
        output_dir: Path
    ) -> Package:
        """Create final Package object."""
        
        # Create Source object
        source = Source(
            type="video" if media_info.get("has_video") else "audio",
            url=url,
            downloaded_at=datetime.now(),
            media_file=str(Path(media_info["video_path" if media_info.get("has_video") else "audio_path"]).name),
            duration_sec=media_info.get("duration", 0),
            has_video=media_info.get("has_video", False)
        )
        
        # Create segments
        segments = self._create_segments(transcript_data["segments"])
        
        # Create transcript object
        transcript = Transcript(
            model=transcript_data["model"],
            diarization_model=transcript_data["diarization_model"],
            language=transcript_data["language"],
            segments=segments
        )
        
        # Create speakers
        speakers = []
        for speaker_label in transcript_data.get("speakers", []):
            speaker = Speaker(
                label=speaker_label,
                name=None,  # Could be enhanced in Phase 3 with enrollment
                method="diarization"
            )
            speakers.append(speaker)
        
        # Create manifest (will be populated in export)
        manifest = Manifest()
        
        # Create complete package
        package = Package(
            source=source,
            transcript=transcript,
            slides=slides_data,
            speakers=speakers,
            manifest=manifest
        )
        
        return package
    
    def _export_package(self, package: Package, output_dir: Path) -> None:
        """Export package to JSON and generate manifest."""
        
        # Generate file checksums for manifest
        file_hashes = []
        
        for file_path in output_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "package.json":
                # Calculate SHA256 hash
                with open(file_path, 'rb') as f:
                    content = f.read()
                    hash_value = hashlib.sha256(content).hexdigest()
                
                relative_path = file_path.relative_to(output_dir)
                file_hashes.append({
                    "path": str(relative_path),
                    "sha256": hash_value,
                    "size": len(content)
                })
        
        # Update manifest
        package.manifest.hashes = file_hashes
        
        # Write package.json
        package_file = output_dir / "package.json"
        with open(package_file, 'w') as f:
            package_dict = package.model_dump()
            json.dump(package_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Package exported to {package_file}")
        logger.info(f"Manifest includes {len(file_hashes)} files")
    
    def _cleanup(self) -> None:
        """Clean up loaded models to free memory."""
        try:
            self.asr.cleanup()
            self.diarizer.cleanup()
            self.slide_processor.cleanup()
            logger.info("Pipeline cleanup complete")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")