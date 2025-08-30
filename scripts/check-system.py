#!/usr/bin/env python3
"""
OpenSessionScribe System Check Script
Comprehensive verification of all dependencies and capabilities
"""

import sys
import subprocess
import importlib
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message: str, status: str, details: Optional[str] = None):
    """Print formatted status message."""
    if status == "ok":
        status_char = f"{GREEN}✅{RESET}"
    elif status == "warning":
        status_char = f"{YELLOW}⚠️ {RESET}"
    elif status == "error":
        status_char = f"{RED}❌{RESET}"
    else:
        status_char = f"{BLUE}ℹ️ {RESET}"
    
    print(f"{status_char} {message}")
    if details:
        print(f"   {details}")

def check_python_version() -> bool:
    """Check if Python version is 3.9+."""
    version = sys.version_info
    if version >= (3, 9):
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", "ok")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", "error", 
                    "Python 3.9+ required")
        return False

def check_system_command(command: str, required: bool = True) -> bool:
    """Check if system command is available."""
    if shutil.which(command):
        try:
            result = subprocess.run([command, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown version"
            print_status(f"{command}", "ok", version_line)
            return True
        except:
            print_status(f"{command}", "ok" if not required else "warning", "Available but version check failed")
            return not required
    else:
        status = "error" if required else "warning"
        print_status(f"{command}", status, f"Not found {'(required)' if required else '(optional)'}")
        return False

def check_python_package(package: str, required: bool = True) -> bool:
    """Check if Python package is available."""
    try:
        module = importlib.import_module(package)
        version = getattr(module, '__version__', 'unknown')
        print_status(f"Python: {package}", "ok", f"version {version}")
        return True
    except ImportError:
        status = "error" if required else "warning"
        print_status(f"Python: {package}", status, f"Not installed {'(required)' if required else '(optional)'}")
        return False

def check_hardware() -> Dict[str, any]:
    """Check hardware capabilities."""
    hardware_info = {}
    
    # Check GPU availability
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            hardware_info['gpu'] = 'cuda'
            print_status(f"GPU (CUDA)", "ok", f"{gpu_count} device(s): {gpu_name}")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            hardware_info['gpu'] = 'mps'
            print_status(f"GPU (MPS)", "ok", "Apple Silicon GPU acceleration available")
        else:
            hardware_info['gpu'] = 'cpu'
            print_status(f"GPU", "warning", "No GPU acceleration available, using CPU")
    except ImportError:
        hardware_info['gpu'] = 'unknown'
        print_status(f"GPU", "warning", "PyTorch not available for GPU detection")
    
    # Check memory
    try:
        import psutil
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        hardware_info['memory_gb'] = memory_gb
        
        if memory_gb >= 16:
            print_status(f"RAM", "ok", f"{memory_gb:.1f} GB available")
        elif memory_gb >= 8:
            print_status(f"RAM", "warning", f"{memory_gb:.1f} GB available (16GB+ recommended)")
        else:
            print_status(f"RAM", "error", f"{memory_gb:.1f} GB available (8GB+ required)")
    except ImportError:
        hardware_info['memory_gb'] = 0
        print_status(f"RAM", "warning", "psutil not available for memory detection")
    
    return hardware_info

def check_model_directories() -> bool:
    """Check if model directories exist and are writable."""
    from opensessionscribe.config import Config
    
    try:
        config = Config.auto_detect()
        models_dir = Path(config.models_dir)
        cache_dir = Path(config.cache_dir)
        
        # Check models directory
        if models_dir.exists() and models_dir.is_dir():
            print_status(f"Models directory", "ok", str(models_dir))
        else:
            models_dir.mkdir(parents=True, exist_ok=True)
            print_status(f"Models directory", "ok", f"Created: {models_dir}")
        
        # Check cache directory
        if cache_dir.exists() and cache_dir.is_dir():
            print_status(f"Cache directory", "ok", str(cache_dir))
        else:
            cache_dir.mkdir(parents=True, exist_ok=True)
            print_status(f"Cache directory", "ok", f"Created: {cache_dir}")
            
        return True
    except Exception as e:
        print_status(f"Model directories", "error", str(e))
        return False

def check_ollama() -> bool:
    """Check Ollama service and models."""
    # Check if ollama command exists
    if not shutil.which('ollama'):
        print_status("Ollama", "warning", "Not installed (required for VLM descriptions)")
        return False
    
    # Check if service is running
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                     if line.strip() and not line.startswith('NAME')]
            
            if models:
                print_status("Ollama service", "ok", "Running")
                print_status("Ollama models", "ok", f"Available: {', '.join(models)}")
            else:
                print_status("Ollama service", "ok", "Running")
                print_status("Ollama models", "warning", "No models installed")
            return True
        else:
            print_status("Ollama service", "warning", "Not running or error occurred")
            return False
    except subprocess.TimeoutExpired:
        print_status("Ollama service", "warning", "Service check timed out")
        return False
    except Exception as e:
        print_status("Ollama service", "warning", f"Check failed: {e}")
        return False

def run_basic_test() -> bool:
    """Run basic functionality test."""
    try:
        # Test configuration loading
        from opensessionscribe.config import Config
        config = Config.auto_detect()
        print_status("Configuration", "ok", "Loaded successfully")
        
        # Test hardware detection
        from opensessionscribe.hardware import HardwareDetector
        hw_summary = HardwareDetector.get_hardware_summary()
        recommended_model = hw_summary['recommendations']['whisper_model']
        print_status("Hardware detection", "ok", f"Recommends Whisper model: {recommended_model}")
        
        return True
    except Exception as e:
        print_status("Basic functionality", "error", str(e))
        return False

def main():
    """Main system check routine."""
    print(f"{BLUE}🔍 OpenSessionScribe System Check{RESET}")
    print("=" * 50)
    
    all_good = True
    
    # Python version
    print(f"\n{BLUE}📋 Python Environment{RESET}")
    all_good &= check_python_version()
    
    # System commands
    print(f"\n{BLUE}🛠️  System Dependencies{RESET}")
    required_commands = [
        ('ffmpeg', True),
        ('ffprobe', True),
        ('yt-dlp', True),
    ]
    
    optional_commands = [
        ('tesseract', False),
        ('ollama', False),
        ('git', False),
    ]
    
    for cmd, required in required_commands + optional_commands:
        all_good &= check_system_command(cmd, required) or not required
    
    # Python packages
    print(f"\n{BLUE}🐍 Python Dependencies{RESET}")
    required_packages = [
        ('typer', True),
        ('pydantic', True),
        ('yaml', True),
        ('torch', True),
        ('whisperx', True),
        ('pyannote.audio', True),
    ]
    
    optional_packages = [
        ('paddleocr', False),
        ('cv2', False),  # opencv
        ('scenedetect', False),
        ('librosa', False),
        ('imagehash', False),
    ]
    
    for pkg, required in required_packages + optional_packages:
        all_good &= check_python_package(pkg, required) or not required
    
    # Hardware check
    print(f"\n{BLUE}🖥️  Hardware Configuration{RESET}")
    hardware_info = check_hardware()
    
    # Model directories
    print(f"\n{BLUE}📁 Model Storage{RESET}")
    all_good &= check_model_directories()
    
    # Ollama check
    print(f"\n{BLUE}🤖 VLM Service (Ollama){RESET}")
    check_ollama()  # Not required for basic functionality
    
    # Basic functionality test
    print(f"\n{BLUE}⚙️  Functionality Test{RESET}")
    all_good &= run_basic_test()
    
    # Summary
    print(f"\n{BLUE}📊 Summary{RESET}")
    print("=" * 50)
    
    if all_good:
        print(f"{GREEN}🎉 System check passed! OpenSessionScribe is ready to use.{RESET}")
        print("\n🚀 Try these commands:")
        print("   python -m cli.main hardware")
        print("   python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./test")
    else:
        print(f"{RED}⚠️  Some issues detected. Please address the errors above.{RESET}")
        print("\n🔧 Common solutions:")
        print("   - Run setup script: ./scripts/setup.sh")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Install system dependencies with your package manager")
    
    print(f"\n📖 For help, see: https://github.com/kurtseifried/OpenSessionScribe#troubleshooting")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())