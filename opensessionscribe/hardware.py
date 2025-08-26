"""Hardware detection and optimal configuration selection."""

import platform
import subprocess
import logging
from typing import Tuple, Optional
import psutil


logger = logging.getLogger(__name__)


class HardwareDetector:
    """Detect system capabilities and recommend optimal settings."""
    
    @staticmethod
    def detect_gpu() -> Tuple[bool, Optional[str]]:
        """Detect GPU availability and type (CUDA/MPS)."""
        # Check for NVIDIA CUDA
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return True, "cuda"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check for Apple Metal Performance Shaders (M1/M2 Macs)
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                # Check if PyTorch MPS is available
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    return True, "mps"
            except ImportError:
                # If PyTorch not installed, assume MPS available on Apple Silicon
                return True, "mps"
        
        return False, None
    
    @staticmethod
    def get_system_ram() -> int:
        """Get total system RAM in GB."""
        return psutil.virtual_memory().total // (1024**3)
    
    @staticmethod
    def get_cpu_info() -> Tuple[int, str]:
        """Get CPU core count and architecture."""
        cores = psutil.cpu_count(logical=False)
        arch = platform.machine()
        return cores, arch
    
    @classmethod
    def recommend_whisper_model(cls) -> str:
        """Recommend optimal Whisper model based on hardware."""
        has_gpu, gpu_type = cls.detect_gpu()
        ram_gb = cls.get_system_ram()
        
        logger.debug(f"Hardware: GPU={has_gpu} ({gpu_type}), RAM={ram_gb}GB")
        
        if has_gpu and ram_gb >= 16:
            return "large-v3"
        elif has_gpu and ram_gb >= 8:
            return "medium"
        elif ram_gb >= 16:
            return "medium"
        elif ram_gb >= 8:
            return "small"
        else:
            return "base"
    
    @classmethod
    def get_optimal_device(cls) -> str:
        """Get optimal PyTorch device string."""
        has_gpu, gpu_type = cls.detect_gpu()
        
        if has_gpu:
            if gpu_type == "cuda":
                return "cuda"
            elif gpu_type == "mps":
                return "mps"
        
        return "cpu"
    
    @classmethod
    def get_hardware_summary(cls) -> dict:
        """Get complete hardware summary."""
        has_gpu, gpu_type = cls.detect_gpu()
        ram_gb = cls.get_system_ram()
        cores, arch = cls.get_cpu_info()
        
        return {
            "gpu": {
                "available": has_gpu,
                "type": gpu_type,
                "device": cls.get_optimal_device()
            },
            "cpu": {
                "cores": cores,
                "architecture": arch
            },
            "memory": {
                "total_gb": ram_gb
            },
            "recommendations": {
                "whisper_model": cls.recommend_whisper_model(),
                "device": cls.get_optimal_device()
            }
        }