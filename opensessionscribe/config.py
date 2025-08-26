"""Configuration management with hardware detection."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal, Dict, Any
import yaml
import logging
import os


logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Main configuration class for OpenSessionScribe."""
    
    # Model settings
    whisper_model: str = "medium"
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    vlm_model: str = "qwen2.5-vl"
    ocr_engine: Literal["paddle", "tesseract"] = "paddle"
    
    # Hardware settings
    force_cpu: bool = False
    device: Optional[str] = None
    
    # Processing options
    enable_slides: bool = True
    enable_descriptions: bool = True
    phash_threshold: int = 8
    
    # Paths
    models_dir: Path = Path.home() / ".opensessionscribe" / "models"
    cache_dir: Path = Path.home() / ".opensessionscribe" / "cache"
    
    # Privacy
    offline_only: bool = True
    
    @classmethod
    def auto_detect(cls) -> "Config":
        """Create config with auto-detected optimal settings."""
        from .hardware import HardwareDetector
        
        hardware = HardwareDetector.get_hardware_summary()
        
        config = cls(
            whisper_model=hardware["recommendations"]["whisper_model"],
            device=hardware["gpu"]["device"],
            force_cpu=not hardware["gpu"]["available"]
        )
        
        logger.info(f"Auto-detected configuration: {hardware['recommendations']}")
        return config
    
    @classmethod 
    def from_yaml(cls, path: Path) -> "Config":
        """Load config from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Convert path strings to Path objects
        if 'models_dir' in data:
            data['models_dir'] = Path(data['models_dir']).expanduser()
        if 'cache_dir' in data:
            data['cache_dir'] = Path(data['cache_dir']).expanduser()
        
        return cls(**data)
    
    def validate(self) -> None:
        """Validate configuration and check model availability."""
        # Create required directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check directory permissions
        if not os.access(self.models_dir, os.W_OK):
            raise PermissionError(f"Models directory not writable: {self.models_dir}")
        if not os.access(self.cache_dir, os.W_OK):
            raise PermissionError(f"Cache directory not writable: {self.cache_dir}")
        
        # Validate model names
        valid_whisper_models = ["base", "small", "medium", "large", "large-v2", "large-v3"]
        if self.whisper_model not in valid_whisper_models:
            raise ValueError(f"Invalid whisper_model: {self.whisper_model}. Valid options: {valid_whisper_models}")
        
        logger.debug(f"Config validation passed: models_dir={self.models_dir}, cache_dir={self.cache_dir}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result
    
    def save_yaml(self, path: Path) -> None:
        """Save config to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=True)
        
        logger.info(f"Config saved to {path}")
    
    @classmethod
    def load_or_create(cls, config_path: Optional[Path] = None) -> "Config":
        """Load config from file or create with auto-detection."""
        if config_path is None:
            config_path = Path.home() / ".opensessionscribe" / "config.yaml"
        
        if config_path.exists():
            logger.info(f"Loading config from {config_path}")
            config = cls.from_yaml(config_path)
        else:
            logger.info("No config file found, using auto-detection")
            config = cls.auto_detect()
            # Save auto-detected config for future use
            config.save_yaml(config_path)
        
        config.validate()
        return config