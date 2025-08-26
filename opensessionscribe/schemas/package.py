"""Core data models for OpenSessionScribe packages."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Word(BaseModel):
    """Individual word with timing and confidence."""
    start: float
    end: float
    text: str
    conf: Optional[float] = None


class Segment(BaseModel):
    """Transcript segment with speaker and timing."""
    id: str
    start: float
    end: float
    speaker: str
    text: str
    edited: bool = False
    words: List[Word] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)


class OCRResult(BaseModel):
    """OCR processing result."""
    engine: str
    text: str
    confidence: float
    blocks: List[Dict[str, Any]] = Field(default_factory=list)


class ChartInfo(BaseModel):
    """Chart/graph analysis."""
    type: str  # line, bar, pie, scatter, etc.
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    trend: Optional[str] = None


class Slide(BaseModel):
    """Slide/keyframe with OCR and description."""
    index: int
    timestamp: float
    image_path: str
    phash: Optional[str] = None
    crop: Optional[Dict[str, int]] = None
    ocr: Optional[OCRResult] = None
    description: Optional[str] = None
    bullets: Optional[List[str]] = None
    chart: Optional[ChartInfo] = None
    ascii_art: Optional[str] = None


class Speaker(BaseModel):
    """Speaker identification."""
    label: str  # SPEAKER_01, etc.
    name: Optional[str] = None
    method: str = "diarization"  # diarization, enrollment, manual


class Source(BaseModel):
    """Source media information."""
    type: str  # podcast, webinar, video
    url: str
    downloaded_at: datetime
    media_file: str
    duration_sec: float
    has_video: bool = False


class Transcript(BaseModel):
    """Complete transcript data."""
    model: str
    diarization_model: str
    language: str
    segments: List[Segment] = Field(default_factory=list)


class Manifest(BaseModel):
    """File manifest with checksums."""
    hashes: List[Dict[str, str]] = Field(default_factory=list)


class Package(BaseModel):
    """Complete OpenSessionScribe package."""
    schema_version: str = "0.1"
    source: Source
    transcript: Transcript
    slides: List[Slide] = Field(default_factory=list)
    speakers: List[Speaker] = Field(default_factory=list)
    notes: Dict[str, Any] = Field(default_factory=dict)
    manifest: Manifest = Field(default_factory=Manifest)