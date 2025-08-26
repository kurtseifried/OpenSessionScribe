#!/usr/bin/env python3
"""Check if all required dependencies are installed."""

import subprocess
import sys
import shutil
from pathlib import Path


def check_command(cmd: str, name: str) -> bool:
    """Check if a command is available."""
    if shutil.which(cmd):
        try:
            result = subprocess.run([cmd, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                print(f"✅ {name}: {version}")
                return True
        except subprocess.TimeoutExpired:
            pass
    
    print(f"❌ {name}: Not found")
    return False


def check_ollama_models():
    """Check if Ollama models are available."""
    try:
        result = subprocess.run(["ollama", "list"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            models = result.stdout.strip().split('\n')[1:]  # Skip header
            if models and models[0]:  # Check if any models exist
                print("✅ Ollama models:")
                for model in models:
                    if model.strip():
                        model_name = model.split()[0]
                        print(f"   - {model_name}")
                return True
            else:
                print("⚠️  Ollama running but no models installed")
                print("   Run: ./scripts/setup-models.sh")
                return False
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        pass
    
    print("❌ Ollama models: Not available")
    return False


def check_python_packages():
    """Check if required Python packages can be imported."""
    packages = [
        ("torch", "PyTorch"),
        ("whisperx", "WhisperX"), 
        ("pyannote.audio", "pyannote.audio"),
        ("paddleocr", "PaddleOCR"),
        ("cv2", "OpenCV"),
        ("scenedetect", "PySceneDetect"),
    ]
    
    all_good = True
    for package, name in packages:
        try:
            __import__(package)
            print(f"✅ {name}: Available")
        except ImportError:
            print(f"❌ {name}: Not installed")
            all_good = False
    
    return all_good


def main():
    """Check all dependencies."""
    print("🔍 Checking OpenSessionScribe dependencies...\n")
    
    all_good = True
    
    print("📦 System Dependencies:")
    all_good &= check_command("ffmpeg", "FFmpeg")
    all_good &= check_command("tesseract", "Tesseract OCR")
    all_good &= check_command("ollama", "Ollama")
    all_good &= check_command("redis-server", "Redis (optional)")
    
    print("\n🤖 AI Models:")
    all_good &= check_ollama_models()
    
    print("\n🐍 Python Packages:")
    packages_ok = check_python_packages()
    
    print("\n" + "="*50)
    
    if all_good and packages_ok:
        print("🎉 All dependencies are installed and ready!")
        print("\nYou can now run:")
        print("   opensessionscribe hardware")
        print("   opensessionscribe process <URL>")
    else:
        print("⚠️  Some dependencies are missing.")
        print("\nTo install missing dependencies:")
        if not all_good:
            print("   ./install-deps.sh          # System dependencies")
            print("   ./scripts/setup-models.sh  # AI models")
        if not packages_ok:
            print("   pip install -e .           # Python packages")
        
        sys.exit(1)


if __name__ == "__main__":
    main()