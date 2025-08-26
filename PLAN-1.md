OpenSessionScribe — Full Technical Plan (Library, CLI, Web UI)

0) Goals & Non-Goals

Goals
	•	Convert podcasts, panels, webinars into a deterministic JSON package with:
	•	Accurate transcript (word timestamps),
	•	Speaker diarization (labels; optional who-is-who),
	•	For webinars: slides (key frames), OCR text, and local VLM descriptions (including optional ASCII sketches),
	•	Captions (SRT/VTT),
	•	Manifest checksums and audit logs.
	•	100% local processing once models are on disk.
	•	Three delivery forms:
	1.	Python library (importable, testable),
	2.	CLI (single command per job),
	3.	Web UI (FastAPI + HTMX) with a three-pane editor (player | transcript | slide text/description).

Non-Goals (v1)
	•	Perfect overlapping-speech separation,
	•	Exact chart digitization (we’ll describe charts qualitatively; quantization is a later add-on),
	•	Cloud integrations.

⸻

1) System Architecture

OpenSessionScribe/
  ├OpenSessionScribe/                         # Python package
  │   ├─ ingest/                  # yt-dlp, RSS/Podcast, local file handlers
  │   ├─ asr/                     # WhisperX adapter
  │   ├─ diarize/                 # pyannote adapter (+ enrollment optional)
  │   ├─ slides/                  # scene detect, frame extract, crop, dedupe
  │   ├─ ocr/                     # PaddleOCR (default) & Tesseract (fallback)
  │   ├─ describe/                # Ollama VLMs (Qwen2.5-VL / LLaVA) + prompts
  │   ├─ align/                   # optional aeneas/WhisperX partial re-alignment
  │   ├─ export/                  # JSON/SRT/VTT, manifest checksums, zips
  │   ├─ schemas/                 # Pydantic models; schema versioning
  │   ├─ pipeline.py              # Orchestration: podcast & webinar flows
  │   ├─ config.py                # Typed config; model paths; offline guard
  │   ├─ store/                   # Project persistence; autosave; audit log
  │   └─ utils/                   # ffmpeg helpers, hashing, timers, diff/patch
  ├─ cli/                         # Typer CLI
  ├─ webapp/                      # FastAPI + HTMX UI, wavesurfer/Konva glue
  ├─ worker/                      # Dramatiq workers for long jobs
  ├─ tests/                       # pytest (unit + E2E)
  ├─ pyproject.toml
  ├─ Dockerfile
  └─ docker-compose.yml

Key principles
	•	Adapters for each external capability (ASR, diarization, OCR, VLM), swappable via config.
	•	Deterministic outputs, stable IDs, schema-versioned JSON.
	•	Single-host operation with optional Redis queue (Dramatiq).

⸻

2) Core Pipelines

2.1 Podcast / Panel (Audio-only)
	1.	Ingest: local file or RSS (download MP3/MP4; normalize to 16 kHz mono WAV).
	2.	ASR: WhisperX (select model: small→large-v3); obtain words w/ timestamps.
	3.	Diarization: pyannote 3.1; produce labeled speech turns.
	4.	Merge: map WhisperX word/segment timing onto diarization labels.
	5.	(Optional) Who-is-who: enrollment via SpeechBrain ECAPA embeddings; cosine match segment embeddings against enrolled speakers.
	6.	Export: JSON package + SRT/VTT + manifest; logs.

2.2 Webinar (Video + Slides)
	1.	Ingest: yt-dlp (URL) or local file; extract/normalize audio for ASR.
	2.	ASR + Diarization: same as podcasts.
	3.	Slide detection: PySceneDetect (content/adaptive); capture timestamps.
	4.	Frame extraction: grab frame near each timestamp; avoid transition blur.
	5.	De-dup: imagehash (pHash/dHash) to remove near-identical slides.
	6.	(Optional) Auto-crop: OpenCV heuristic to locate stable slide rectangle across frames; crop before OCR.
	7.	OCR:
	•	Default: PaddleOCR (PP-OCR / PP-StructureV3) → text blocks, layout, tables,
	•	Fallback: Tesseract via pytesseract for speed/simple text.
	8.	Slide descriptions (optional): local VLM via Ollama:
	•	Primary: Qwen2.5-VL; fallback: LLaVA 1.6,
	•	Prompt includes slide image + OCR text; returns caption, bullets, chart description, optional ASCII (≤80 cols).
	9.	Export: JSON + slides folder + SRT/VTT + manifest; logs.

⸻

3) Tech Stack (Local-Only)

Backend/App
	•	FastAPI, Uvicorn, HTMX, Jinja2, Tailwind, orjson, Pydantic v2, Typer.

Compute
	•	WhisperX (ASR + alignment); pyannote.audio 3.1 (diarization, PyTorch),
	•	PySceneDetect; Pillow + imagehash; OpenCV (optional),
	•	PaddleOCR (PP-StructureV3); Tesseract (fallback),
	•	Ollama (Qwen2.5-VL / LLaVA) for slide descriptions/ASCII,
	•	SpeechBrain (ECAPA) for speaker enrollment (optional),
	•	aeneas (optional forced alignment for heavily edited segments).

Job processing
	•	Dramatiq + Redis (recommended),
	•	or ProcessPoolExecutor (zero-dep fallback).

Ingest
	•	yt-dlp; ffmpeg (required),
	•	Podcasts: simple RSS fetcher (feedparser) or simple-podcast-dl adapter.

⸻

4) Data Model & Schemas

4.1 JSON Package (v0.1)

{
  "schema_version": "0.1",
  "source": {
    "type": "podcast|panel|webinar",
    "url": "https://…",
    "downloaded_at": "2025-08-25T20:00:00-06:00",
    "media_file": "video.mp4",
    "duration_sec": 4567.8
  },
  "transcript": {
    "model": "whisperx-large-v3",
    "diarization_model": "pyannote/speaker-diarization-3.1",
    "language": "en",
    "segments": [
      {
        "id": "seg_000123",
        "start": 12.34,
        "end": 18.90,
        "speaker": "SPEAKER_01",
        "text": "…",
        "edited": false,
        "words": [
          {"start": 12.34, "end": 12.60, "text": "Hello", "conf": 0.98},
          {"start": 12.61, "end": 12.95, "text": "everyone", "conf": 0.97}
        ],
        "history": []
      }
    ]
  },
  "slides": [
    {
      "index": 5,
      "timestamp": 613.2,
      "image_path": "slides/slide_0005.jpg",
      "crop": {"x": 120, "y": 80, "w": 1280, "h": 720},
      "phash": "c87af3…",
      "ocr": {
        "engine": "paddleocr",
        "text": "…",
        "blocks": [{"text":"…","bbox":{"x":..,"y":..,"w":..,"h":..}}],
        "tables": [/* structure arrays if available */],
        "confidence": 0.92
      },
      "description": "One-sentence caption.",
      "bullets": ["…", "…"],
      "chart": {
        "type": "line|bar|pie|none",
        "x_axis": "time (weeks)",
        "y_axis": "throughput (req/s)",
        "trend": "upward with two plateaus"
      },
      "ascii": "ASCII art here (<=80 cols)"
    }
  ],
  "speakers": [
    {"label": "SPEAKER_01", "name": "Alice", "method": "embedding-match"}
  ],
  "notes": {
    "pipeline_version": "v0.1.0",
    "warnings": [],
    "quality": {"asr": 0.0, "diarization": 0.0, "ocr": 0.0}
  },
  "manifest": {
    "hashes": [
      {"path":"package.json","sha256":"…"},
      {"path":"slides/slide_0005.jpg","sha256":"…"}
    ]
  }
}

4.2 Pydantic Models (excerpt)

class Word(BaseModel):
    start: float
    end: float
    text: str
    conf: float | None = None

class Segment(BaseModel):
    id: str
    start: float
    end: float
    speaker: str
    text: str
    edited: bool = False
    words: list[Word] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)

class Slide(BaseModel):
    index: int
    timestamp: float
    image_path: str
    phash: str | None = None
    crop: dict | None = None
    ocr: dict | None = None
    description: str | None = None
    bullets: list[str] | None = None
    chart: dict | None = None
    ascii: str | None = None

class Package(BaseModel):
    schema_version: str
    source: dict
    transcript: dict
    slides: list[Slide] = Field(default_factory=list)
    speakers: list[dict] = Field(default_factory=list)
    notes: dict = Field(default_factory=dict)
    manifest: dict = Field(default_factory=dict)

Schema versioning
	•	schema_version bumps on breaking changes,
	•	migration helpers in opensessionscribe/schemas/migrate.py.

⸻

5) Algorithms & Heuristics

5.1 Merge ASR + Diarization
	•	Intersect ASR words with diarization speech turns,
	•	Assign each word the speaker label of the overlapping diarization segment; if overlap splits a word across turns, choose majority overlap,
	•	Segment grouping: collect consecutive words with same speaker into segments (cap long segments at ~15–30s).

5.2 Slide Detection & De-dup
	•	PySceneDetect content detector tuned for slide flips (low motion, large histogram deltas),
	•	Extract frame at t + 0.15s to avoid transition blur,
	•	Compute pHash; drop candidate slide if Hamming distance ≤ threshold (e.g., 8) vs previous kept slide.

5.3 Auto-Crop (optional)
	•	For K initial slides, detect largest stable rectangular region (edge density + aspect ratio ~16:9),
	•	If stable across ≥80% of K, crop all slides to that rectangle; else leave full frame.

5.4 OCR Strategy
	•	Default PaddleOCR (PP-StructureV3) for block detection & tables,
	•	Fallback Tesseract with --psm 6 for dense uniform text; expose language packs in config,
	•	Normalize whitespace; preserve block order for readability; store confidence.

5.5 Slide Descriptions (VLM)
	•	Prompt includes:
	•	Slide image,
	•	OCR text (verbatim),
	•	Instructions to:
	•	emit 1-line caption,
	•	3–5 concise bullets,
	•	chart type/axes/units/trend if present,
	•	ASCII sketch ≤80 columns, plain ASCII (no box-drawing).
	•	Temperature low (e.g., 0.2–0.4) to keep determinism.

5.6 Transcript Editing (timing safety)
	•	Fast path: run diff-match-patch between original and edited text per segment; remap surviving tokens to existing word timings; punctuation-only edits do not affect timings,
	•	Threshold: if >20% token delta or span edits, trigger segment re-alignment (WhisperX alignment on that window).
	•	Boundary nudges: snap boundaries to nearest word edges; maintain non-overlap invariant.

⸻

6) Library API

from opensessionscribe.pipeline import process_podcast, process_webinar
from opensessionscribe.config import Config
from opensessionscribe.schemas.package import Package

cfg = Config.default().with_models(asr="whisperx-large-v3", diar="pyannote/speaker-diarization-3.1")
pkg: Package = process_webinar("https://youtu.be/XYZ", cfg)
pkg_json = pkg.model_dump_json()

Adapters Interfaces

class ASRAdapter:       def transcribe(self, audio_path:str, cfg)->dict: ...
class DiarizerAdapter:  def diarize(self, audio_path:str, cfg)->dict: ...
class SlideDetector:    def detect(self, video_path:str, cfg)->list[float]: ...
class OCRAdapter:       def run(self, image_path:str, cfg)->dict: ...
class VLMAdapter:       def describe(self, image_path:str, ocr_text:str, cfg)->dict: ...


⸻

7) CLI (Typer)

Commands

# Podcast
opensessionscribe podcast --rss https://example.com/feed.xml --out out/
opensessionscribe podcast --file input.mp3 --out out/

# Webinar
opensessionscribe webinar --url https://youtu.be/VIDEO --out out/ --slides --ocr --describe
opensessionscribe webinar --file talk.mp4 --out out/ --slides --ocr

# Common flags
  --whisper-model large-v3|medium|small
  --diarization-model pyannote/speaker-diarization-3.1
  --ocr-engine paddle|tesseract
  --vlm qwen2.5-vl|llava
  --ascii on|off
  --phash-threshold 8
  --crop auto|full|manual:x,y,w,h
  --chapters
  --redact-pii
  --offline-only
  --models-dir /models

Outputs

out/
  package.json
  captions.srt
  captions.vtt
  slides/slide_0001.jpg
  logs/run.log
  manifest.sha256


⸻

8) Web UI (FastAPI + HTMX) — Three-Pane Editor

Layout
	•	Left: Player pane (video/audio element + wavesurfer.js for waveform & markers),
	•	Middle: Transcript pane (segment table: time, speaker chip, editable text),
	•	Right: Slide pane (thumbnail list + selected slide with OCR text and description editors; optional Konva.js bounding-box editor to re-OCR regions).

Interactions (keyboard-first)
	•	Transport: Space/J/K/L (play/pause/back/fwd),
	•	Click word → seek to exact time,
	•	Cmd/Ctrl+Enter: split segment,
	•	Alt+←/→: nudge boundary ±0.1s (snaps to word),
	•	1..9: assign speaker,
	•	Slide view: draw box → Re-OCR Region, Re-Describe, Mark as duplicate.

Backend Endpoints
	•	POST /jobs → enqueue ingest/transcribe pipeline (returns job_id),
	•	GET /jobs/{id} → status JSON; /ws/jobs/{id} for live logs,
	•	GET /projects/{id} → editor page,
	•	Transcript ops:
	•	PATCH /projects/{id}/segments/{segId},
	•	POST /projects/{id}/segments/{segId}/split,
	•	POST /projects/{id}/segments/{segId}/merge-with/{nextId},
	•	POST /projects/{id}/segments/{segId}/realign,
	•	Slide ops:
	•	PATCH /projects/{id}/slides/{idx},
	•	POST /projects/{id}/slides/{idx}/reocr (optional bbox),
	•	POST /projects/{id}/slides/{idx}/redescribe,
	•	Export:
	•	GET /projects/{id}/download/json|srt|vtt|zip.

State & Persistence
	•	Project folder under /data/projects/<uuid>/,
	•	project.json (canonical), project.tmp.json (autosave), audit.log,
	•	Edits appended to audit with timestamp & change summary.

Background Jobs
	•	Dramatiq worker processes:
	•	ingest_job, asr_job, diarize_job, slides_job, ocr_job, describe_job, export_job,
	•	Progress messages pushed by Redis pub/sub to WebSocket,
	•	Retries with exponential backoff; user can cancel job.

Accessibility
	•	Semantic HTML, ARIA roles, high-contrast theme toggle,
	•	Alt-text populated from slide descriptions,
	•	Captions downloadable; keyboard shortcuts always available.

⸻

9) Config & Offline Mode

Config resolution order: defaults → ~/.configopensessionscriben/config.yaml → CLI flags → per-job overrides.

Sample

model:
  asr: whisperx-large-v3
  diarization: pyannote/speaker-diarization-3.1
  vlm: qwen2.5-vl
paths:
  models_dir: /models
  cache_dir: /cache
slides:
  detector: content
  phash_threshold: 8
  crop_strategy: auto
ocr:
  engine: paddleocr
  languages: [en]
privacy:
  offline_only: true
  redact_pii: false

Offline guard
	•	If offline_only: true, any network call (e.g., model download) hard-fails with actionable error.

⸻

10) Packaging & Deployment

Dockerfile (sketch)
	•	Base: python:3.11-slim,
	•	Install ffmpeg, tesseract-ocr,
	•	pip install all deps (FastAPI, Dramatiq, WhisperX, pyannote, PaddleOCR, PySceneDetect, etc.),
	•	Expose 8000,
	•	CMD runs uvicorn webapp.main:app.

docker-compose
	•	Services: web, worker, redis,
	•	Volumes:
	•	/data (outputs),
	•	/models (weights for WhisperX/pyannote/PaddleOCR/VLM),
	•	/cache (yt-dlp, temp frames),
	•	Bind to 127.0.0.1 by default.

Installation paths
	•	pipx for CLI,
	•	Docker for web UI,
	•	Homebrew/Winget packaging as v1.1 nicety.

⸻

11) Reliability, Logging, Determinism
	•	Deterministic outputs: pinned model versions and seeds; ASCII prompts low temperature,
	•	Manifest: SHA-256 on all artifacts; detect tampering post-export,
	•	Logs: structlog to both console and logs/run.log; include timings per stage,
	•	Validation: on export, verify:
	•	segments sorted and non-overlapping,
	•	slide timestamps within media duration,
	•	referenced files exist; hash check.

⸻

12) Security & Privacy
	•	Default bind to 127.0.0.1,
	•	No cloud calls after model download; offline-only mode strongly recommended,
	•	Optional PII redaction: spaCy/Stanza + regex for emails, phones, credit cards; configurable,
	•	Clear per-job temp cleanup; /cache can be purged via CLI.

⸻

13) Performance Targets (initial)
	•	MacBook M-series (8–16 GB RAM): real-time to 2× real-time for WhisperX medium/large-v3; diarization near real-time for 1–2 speakers,
	•	Windows w/ CPU: slower; CUDA improves throughput if present,
	•	Slide pipeline: ~50–150 ms per slide for OCR (depends on resolution); VLM description 0.5–3 s per slide (quant and hardware dependent).

⸻

14) Testing & QA

Unit tests
	•	Adapters (ASR, diarization, OCR, VLM) return shaped data with required keys,
	•	Pydantic schema round-trip.

E2E tests
	•	Tiny samples:
	•	2-speaker podcast (3–5 min),
	•	1 webinar clip with 5–8 slide changes,
	•	Compare counts (segments, slides), JSON keys, checksum stability.

Golden outputs
	•	Version-locked expected JSON/SRT for sample inputs,
	•	CI checks: schema diffs → fail on breaking change unless migration provided.

⸻

15) Editor Interaction Details
	•	Autosave every N seconds and on blur,
	•	Undo/redo ring buffer (client-side) mirrored to audit.log,
	•	Conflict avoidance: single-user assumption in v1; last write wins; server validates monotonic timestamps.

Re-alignment trigger
	•	If edited token delta > 20% or boundaries moved more than 0.5 s, run segment re-alignment (WhisperX aligner) just on that window,
	•	Neighbor segments get their boundaries updated to maintain non-overlap.

⸻

16) CLI & API Examples

CLI

opensessionscribe webinar --url https://youtu.be/VIDEO --out out/ --slides --ocr --describe --ascii on --offline-only

REST (web UI)

POST /jobs
{ "type":"webinar", "url":"https://…", "options":{"slides":true,"ocr":true,"describe":true} }

GET /ws/jobs/{id}    # WebSocket progress stream

GET /projects/{id}   # Editor
PATCH /projects/{id}/segments/seg_000123
{ "text": "corrected text", "speaker":"SPEAKER_02" }

POST /projects/{id}/slides/5/reocr
{ "bbox": {"x":120,"y":80,"w":1280,"h":720} }

GET /projects/{id}/download/json


⸻

17) Accessibility & Inclusion
	•	Hearing-impaired: SRT/VTT with speaker labels; precise word timings,
	•	Vision-impaired: slide descriptions used as alt-text; optional ASCII charts; optional local TTS brief (add piper in v1.1),
	•	Keyboard-first navigation and high-contrast themes.

⸻

18) Roadmap

MVP
	•	Library: pipelines for podcast/webinar; PaddleOCR; JSON/SRT/VTT; pHash dedupe,
	•	CLI: podcast/webinar + flags; offline mode,
	•	Web UI: three-pane editor, basic edits, re-OCR, re-describe; Dramatiq jobs,
	•	Deterministic export + manifest.

v1.0 (hardening)
	•	Auto-crop reliability; chapterization; PII redaction; speaker enrollment (ECAPA),
	•	Local search index (FAISS/Chroma) over transcript for instant search,
	•	Brew/Winget packaging; more tests & samples.

v1.1+
	•	Chart quant extraction pass (optional),
	•	Multi-user editing (locking), richer UI (React front-end if needed),
	•	Model management UI; downloadable model packs,
	•	Pluggable “post-processors” (summaries per speaker, topic clustering).

⸻

19) Risks & Mitigations
	•	Model drift / version skew → pin versions; include pipeline_version; migration scripts,
	•	OCR variability → PaddleOCR default + Tesseract fallback; user re-OCR region,
	•	Diarization errors → easy relabel edits; optional enrollment,
	•	Performance on CPU-only Windows → expose smaller Whisper models; clear guidance on CUDA optionality,
	•	User edits breaking timing → snap to word edges; automated validation on save/export.

⸻

20) Licensing & Compliance
	•	Ensure component licenses are compatible (MIT/BSD/Apache-2.0 for most; verify PaddleOCR/Tesseract/pyannote terms),
	•	Provide THIRD_PARTY_LICENSES.md,
	•	User content processed locally; no telemetry by default.

⸻

21) “Why this is worth it”
	•	Time compression: turn 60 minutes into a skim-able JSON bundle with chapters and slide bullets,
	•	Accessibility baked in,
	•	Privacy-first: entirely local,
	•	Composable: outputs plug into downstream search, analysis, or publication.

⸻

Final notes (opinionated)
	•	Start with PaddleOCR + Qwen2.5-VL as defaults; Tesseract + LLaVA as fallbacks,
	•	Use Dramatiq + Redis for job reliability from day one; ProcessPool only for a strict “no external services” environment,
	•	Keep the web UI server-driven (HTMX) until you really need a SPA; avoid premature complexity,
	•	Guard offline mode; fail fast if a model is missing,
	•	Aggressively validate and checksum outputs—determinism and trust beat raw speed for this use case.


