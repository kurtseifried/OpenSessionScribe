"""Main CLI application using Typer."""

from pathlib import Path
from typing import Optional
import typer
import logging

from opensessionscribe import ProcessingPipeline, Config
from opensessionscribe.hardware import HardwareDetector


app = typer.Typer(name="opensessionscribe", help="Local podcast and webinar processing toolkit")


@app.command()
def process(
    url: str = typer.Argument(..., help="URL to process (YouTube, podcast, etc.)"),
    output: Path = typer.Option("./output", "--output", "-o", help="Output directory"),
    whisper_model: Optional[str] = typer.Option(None, "--whisper-model", help="Whisper model size (auto-detected if not specified)"),
    slides: bool = typer.Option(True, "--slides/--no-slides", help="Enable slide processing for videos"),
    descriptions: bool = typer.Option(True, "--descriptions/--no-descriptions", help="Generate slide descriptions"),
    ocr_engine: str = typer.Option("paddle", "--ocr-engine", help="OCR engine (paddle/tesseract)"),
    vlm_model: str = typer.Option("qwen2.5-vl", "--vlm-model", help="VLM model for descriptions"),
    force_cpu: bool = typer.Option(False, "--force-cpu", help="Force CPU processing"),
    offline_only: bool = typer.Option(True, "--offline-only/--allow-network", help="Block network after download"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Process a URL and generate transcript package."""
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create config
    if whisper_model is None:
        whisper_model = HardwareDetector.recommend_whisper_model()
        typer.echo(f"Auto-detected optimal Whisper model: {whisper_model}")
    
    config = Config(
        whisper_model=whisper_model,
        enable_slides=slides,
        enable_descriptions=descriptions,
        ocr_engine=ocr_engine,
        vlm_model=vlm_model,
        force_cpu=force_cpu,
        offline_only=offline_only,
    )
    
    # Validate config
    config.validate()
    
    # Run pipeline
    pipeline = ProcessingPipeline(config)
    
    try:
        package = pipeline.process_url(url, output)
        typer.echo(f"✅ Processing complete! Output saved to: {output}")
        typer.echo(f"📄 Package: {output}/package.json")
        
        if slides and package.slides:
            typer.echo(f"🖼️  Slides: {len(package.slides)} slides extracted")
            
    except Exception as e:
        typer.echo(f"❌ Processing failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def info(
    url: str = typer.Argument(..., help="URL to get information about")
):
    """Get information about a URL without processing."""
    from opensessionscribe.ingest.downloader import MediaDownloader
    
    try:
        config = Config.auto_detect()
        downloader = MediaDownloader(config)
        
        typer.echo(f"🔍 Getting information for: {url}")
        info = downloader.get_info(url)
        
        typer.echo("\n📺 Video Information:")
        typer.echo(f"   Title: {info.get('title', 'N/A')}")
        typer.echo(f"   Uploader: {info.get('uploader', 'N/A')}")
        typer.echo(f"   Duration: {info.get('duration', 0)} seconds")
        typer.echo(f"   View count: {info.get('view_count', 'N/A')}")
        
        if info.get('description'):
            desc = info['description'][:200]
            typer.echo(f"   Description: {desc}{'...' if len(info['description']) > 200 else ''}")
            
    except Exception as e:
        typer.echo(f"❌ Failed to get info: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def hardware():
    """Show system hardware information and recommendations."""
    import json
    
    hardware_summary = HardwareDetector.get_hardware_summary()
    
    typer.echo("🖥️  Hardware Information:")
    typer.echo(f"   CPU: {hardware_summary['cpu']['cores']} cores ({hardware_summary['cpu']['architecture']})")
    typer.echo(f"   RAM: {hardware_summary['memory']['total_gb']} GB")
    
    gpu = hardware_summary['gpu']
    typer.echo(f"   GPU: {'Yes' if gpu['available'] else 'No'} ({gpu['type'] or 'N/A'})")
    
    typer.echo()
    typer.echo("📊 Recommendations:")
    rec = hardware_summary['recommendations']
    typer.echo(f"   Whisper model: {rec['whisper_model']}")
    typer.echo(f"   Device: {rec['device']}")
    
    typer.echo()
    typer.echo("🔧 System Dependencies:")
    
    # Check system dependencies
    from opensessionscribe.utils.ffmpeg import FFmpegProcessor
    from opensessionscribe.ingest.downloader import MediaDownloader
    
    deps = [
        ("FFmpeg", FFmpegProcessor.check_ffmpeg()),
        ("ffprobe", FFmpegProcessor.check_ffprobe()),
        ("yt-dlp", MediaDownloader.check_ytdlp()),
    ]
    
    for name, available in deps:
        status = "✅" if available else "❌"
        typer.echo(f"   {status} {name}")
    
    # Check if any dependencies missing
    missing = [name for name, available in deps if not available]
    if missing:
        typer.echo()
        typer.echo("⚠️  Missing dependencies. Install with:")
        typer.echo("   macOS: ./install-deps.sh")
        typer.echo("   Docker: ./scripts/docker-setup.sh")


@app.command()
def check():
    """Check system setup and dependencies."""
    typer.echo("🔍 Checking OpenSessionScribe setup...")
    
    # Run hardware check
    hardware()
    
    # Test configuration
    typer.echo()
    typer.echo("⚙️  Configuration:")
    try:
        config = Config.auto_detect()
        typer.echo("   ✅ Configuration loaded successfully")
        typer.echo(f"   📁 Models dir: {config.models_dir}")
        typer.echo(f"   📁 Cache dir: {config.cache_dir}")
    except Exception as e:
        typer.echo(f"   ❌ Configuration error: {e}")


@app.command()
def transcribe(
    audio_file: Path = typer.Argument(..., help="Audio file to transcribe"),
    output: Path = typer.Option("./transcription.json", "--output", "-o", help="Output JSON file"),
    whisper_model: Optional[str] = typer.Option(None, "--whisper-model", help="Whisper model size"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Test transcription of an audio file."""
    from opensessionscribe.asr.whisperx_adapter import WhisperXAdapter
    import json
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create config
    if whisper_model is None:
        whisper_model = HardwareDetector.recommend_whisper_model()
        typer.echo(f"Auto-detected optimal Whisper model: {whisper_model}")
    
    config = Config(
        whisper_model=whisper_model,
        force_cpu=False,
    )
    
    # Check if audio file exists
    if not audio_file.exists():
        typer.echo(f"❌ Audio file not found: {audio_file}", err=True)
        raise typer.Exit(1)
    
    # Check WhisperX availability
    if not WhisperXAdapter.check_whisperx():
        typer.echo("❌ WhisperX not available. Install with: pip install whisperx", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎙️ Transcribing: {audio_file}")
    typer.echo(f"📄 Output: {output}")
    typer.echo(f"🤖 Model: {config.whisper_model}")
    typer.echo(f"⚙️ Device: {config.device or 'auto'}")
    
    try:
        # Initialize WhisperX adapter
        adapter = WhisperXAdapter(config)
        
        # Transcribe
        result = adapter.transcribe(audio_file)
        
        # Save results
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Show summary
        typer.echo(f"✅ Transcription complete!")
        typer.echo(f"📊 Language: {result['language']}")
        typer.echo(f"📊 Segments: {len(result['segments'])}")
        typer.echo(f"📊 Words: {len(result['word_segments'])}")
        
        # Show first few segments as preview
        typer.echo("\n📝 Preview:")
        for i, segment in enumerate(result['segments'][:3]):
            typer.echo(f"   [{segment['start']:.1f}s-{segment['end']:.1f}s]: {segment['text'][:100]}...")
        
        if len(result['segments']) > 3:
            typer.echo(f"   ... and {len(result['segments']) - 3} more segments")
        
        # Cleanup
        adapter.cleanup()
        
    except Exception as e:
        typer.echo(f"❌ Transcription failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def diarize(
    audio_file: Path = typer.Argument(..., help="Audio file for speaker diarization"),
    output: Path = typer.Option("./diarization.json", "--output", "-o", help="Output JSON file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Test speaker diarization on an audio file."""
    from opensessionscribe.diarize.pyannote_adapter import PyAnnoteAdapter
    import json
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create config
    config = Config(
        diarization_model="pyannote/speaker-diarization-3.1",
        force_cpu=False,
    )
    
    # Check if audio file exists
    if not audio_file.exists():
        typer.echo(f"❌ Audio file not found: {audio_file}", err=True)
        raise typer.Exit(1)
    
    # Check pyannote availability
    if not PyAnnoteAdapter.check_pyannote():
        typer.echo("❌ pyannote.audio not available. Install with: pip install pyannote.audio", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"👥 Running speaker diarization: {audio_file}")
    typer.echo(f"📄 Output: {output}")
    typer.echo(f"🤖 Model: {config.diarization_model}")
    
    try:
        # Initialize adapter
        adapter = PyAnnoteAdapter(config)
        
        # Run diarization
        result = adapter.diarize(audio_file)
        
        # Save results
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Show summary
        typer.echo(f"✅ Diarization complete!")
        typer.echo(f"📊 Speakers found: {result['total_speakers']}")
        typer.echo(f"📊 Segments: {result['total_segments']}")
        typer.echo(f"📊 Speaker labels: {', '.join(result['speakers'])}")
        
        # Show segment preview
        typer.echo("\n📝 Segment Preview:")
        for i, segment in enumerate(result['segments'][:5]):
            duration = segment['end'] - segment['start']
            typer.echo(f"   [{segment['start']:.1f}s-{segment['end']:.1f}s] {segment['speaker']} ({duration:.1f}s)")
        
        if len(result['segments']) > 5:
            typer.echo(f"   ... and {len(result['segments']) - 5} more segments")
        
        # Cleanup
        adapter.cleanup()
        
    except Exception as e:
        typer.echo(f"❌ Diarization failed: {e}", err=True)
        raise typer.Exit(1)


@app.command() 
def process_combined(
    audio_file: Path = typer.Argument(..., help="Audio file to process"),
    output: Path = typer.Option("./combined_output.json", "--output", "-o", help="Output JSON file"),
    whisper_model: Optional[str] = typer.Option(None, "--whisper-model", help="Whisper model size"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Test combined transcription + diarization."""
    from opensessionscribe.asr.whisperx_adapter import WhisperXAdapter
    from opensessionscribe.diarize.pyannote_adapter import PyAnnoteAdapter
    import json
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create config
    if whisper_model is None:
        whisper_model = HardwareDetector.recommend_whisper_model()
        typer.echo(f"Auto-detected optimal Whisper model: {whisper_model}")
    
    config = Config(
        whisper_model=whisper_model,
        diarization_model="pyannote/speaker-diarization-3.1",
        force_cpu=False,
    )
    
    # Check if audio file exists
    if not audio_file.exists():
        typer.echo(f"❌ Audio file not found: {audio_file}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"🎯 Processing audio with transcription + diarization: {audio_file}")
    typer.echo(f"📄 Output: {output}")
    
    try:
        # Step 1: Transcription
        typer.echo("🎙️ Step 1: Running transcription...")
        asr_adapter = WhisperXAdapter(config)
        transcript_result = asr_adapter.transcribe(audio_file)
        typer.echo(f"✅ Found {len(transcript_result['segments'])} transcript segments")
        
        # Step 2: Diarization  
        typer.echo("👥 Step 2: Running speaker diarization...")
        diarize_adapter = PyAnnoteAdapter(config)
        diarization_result = diarize_adapter.diarize(audio_file)
        typer.echo(f"✅ Found {diarization_result['total_speakers']} speakers")
        
        # Step 3: Merge results
        typer.echo("🔄 Step 3: Merging transcript with speakers...")
        merged_segments = diarize_adapter.merge_transcript_diarization(
            transcript_result['segments'],
            diarization_result['segments']
        )
        
        # Create combined result
        combined_result = {
            "transcript": transcript_result,
            "diarization": diarization_result,
            "merged_segments": merged_segments,
            "summary": {
                "total_speakers": diarization_result['total_speakers'],
                "total_segments": len(merged_segments),
                "duration": max(seg['end'] for seg in merged_segments) if merged_segments else 0,
                "language": transcript_result['language']
            }
        }
        
        # Save results
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w') as f:
            json.dump(combined_result, f, indent=2, ensure_ascii=False)
        
        # Show summary
        typer.echo(f"\n🎉 Combined processing complete!")
        typer.echo(f"📊 Language: {transcript_result['language']}")
        typer.echo(f"📊 Speakers: {diarization_result['total_speakers']}")
        typer.echo(f"📊 Merged segments: {len(merged_segments)}")
        
        # Show preview with speakers
        typer.echo("\n📝 Preview with Speaker Labels:")
        for i, segment in enumerate(merged_segments[:3]):
            typer.echo(f"   [{segment['start']:.1f}s-{segment['end']:.1f}s] {segment['speaker']}: {segment['text'][:80]}...")
        
        if len(merged_segments) > 3:
            typer.echo(f"   ... and {len(merged_segments) - 3} more segments")
        
        # Cleanup
        asr_adapter.cleanup()
        diarize_adapter.cleanup()
        
    except Exception as e:
        typer.echo(f"❌ Combined processing failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def slides(
    video_file: Path = typer.Argument(..., help="Video file for slide extraction"),
    output: Path = typer.Option("./slides_output", "--output", "-o", help="Output directory"),
    descriptions: bool = typer.Option(True, "--descriptions/--no-descriptions", help="Generate VLM descriptions"),
    vlm_model: str = typer.Option("qwen2-vl", "--vlm-model", help="VLM model for descriptions"),
    ocr_engine: str = typer.Option("paddle", "--ocr-engine", help="OCR engine (paddle/tesseract)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Test slide processing on a video file."""
    from opensessionscribe.slides.processor import SlideProcessor
    import json
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Create config
    config = Config(
        enable_slides=True,
        enable_descriptions=descriptions,
        vlm_model=vlm_model,
        ocr_engine=ocr_engine,
        force_cpu=False,
    )
    
    # Check if video file exists
    if not video_file.exists():
        typer.echo(f"❌ Video file not found: {video_file}", err=True)
        raise typer.Exit(1)
    
    # Create output directory
    output.mkdir(parents=True, exist_ok=True)
    
    typer.echo(f"🎬 Processing slides from: {video_file}")
    typer.echo(f"📁 Output directory: {output}")
    typer.echo(f"🔍 OCR engine: {ocr_engine}")
    if descriptions:
        typer.echo(f"🤖 VLM model: {vlm_model}")
    
    try:
        # Check dependencies
        processor = SlideProcessor(config)
        deps = processor.check_dependencies()
        
        typer.echo("\n🔧 Dependencies:")
        for dep, available in deps.items():
            status = "✅" if available else "❌"
            typer.echo(f"   {status} {dep}")
        
        # Check critical dependencies
        missing_critical = []
        if not deps["ffmpeg"]:
            missing_critical.append("ffmpeg")
        if config.ocr_engine == "paddle" and not deps["paddleocr"]:
            if not deps["tesseract"]:
                missing_critical.append("OCR engine (paddleocr or tesseract)")
        if descriptions and not deps["ollama"]:
            missing_critical.append("Ollama service")
        if descriptions and not deps["vlm_model"]:
            missing_critical.append(f"VLM model ({vlm_model})")
        
        if missing_critical:
            typer.echo(f"\n❌ Missing critical dependencies: {', '.join(missing_critical)}")
            typer.echo("Install missing dependencies and try again.")
            raise typer.Exit(1)
        
        # Process slides
        typer.echo("\n🎯 Processing slides...")
        slides_data = processor.process_video(video_file, output)
        
        if not slides_data:
            typer.echo("❌ No slides extracted")
            raise typer.Exit(1)
        
        # Save results
        results_file = output / "slides.json"
        slides_dict = [slide.model_dump() for slide in slides_data]
        
        with open(results_file, 'w') as f:
            json.dump(slides_dict, f, indent=2, ensure_ascii=False)
        
        # Show summary
        typer.echo(f"\n✅ Slide processing complete!")
        typer.echo(f"📊 Slides extracted: {len(slides_data)}")
        typer.echo(f"📄 Results saved to: {results_file}")
        
        # Show preview
        typer.echo("\n📝 Slide Preview:")
        for i, slide in enumerate(slides_data[:3]):
            timestamp = slide.timestamp
            typer.echo(f"\n   📸 Slide {i+1} [{timestamp:.1f}s]:")
            typer.echo(f"       Image: {Path(slide.image_path).name}")
            
            if slide.ocr and slide.ocr.text:
                ocr_preview = slide.ocr.text[:100]
                typer.echo(f"       OCR: {ocr_preview}{'...' if len(slide.ocr.text) > 100 else ''}")
            
            if slide.description:
                desc_preview = slide.description[:100]
                typer.echo(f"       Description: {desc_preview}{'...' if len(slide.description) > 100 else ''}")
        
        if len(slides_data) > 3:
            typer.echo(f"       ... and {len(slides_data) - 3} more slides")
        
        # Cleanup
        processor.cleanup()
        
    except Exception as e:
        typer.echo(f"❌ Slide processing failed: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()