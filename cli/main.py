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


if __name__ == "__main__":
    app()