# Multi-stage Dockerfile for OpenSessionScribe
# Supports CPU, CUDA, and Apple Silicon (MPS) configurations

ARG GPU_SUPPORT=cpu
ARG PYTHON_VERSION=3.11

# Base stage - common dependencies
FROM python:${PYTHON_VERSION}-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Media processing
    ffmpeg \
    # OCR engines
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # System utilities
    curl \
    wget \
    git \
    # Build tools for Python packages
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create app user and directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/data /app/models /app/cache && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Python dependencies stage
FROM base as python-deps

# Install Python build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir build wheel

# GPU-specific stage
FROM python-deps as gpu-deps
ARG GPU_SUPPORT

# Install PyTorch with appropriate GPU support
RUN if [ "$GPU_SUPPORT" = "cuda" ]; then \
        pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu118; \
    else \
        pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Install other ML dependencies
RUN pip install --no-cache-dir \
    whisperx \
    pyannote.audio \
    paddleocr \
    opencv-python-headless \
    scenedetect[opencv] \
    imagehash

# Application stage
FROM base as app

# Copy Python dependencies
COPY --from=gpu-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=gpu-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY opensessionscribe/ ./opensessionscribe/
COPY cli/ ./cli/
COPY webapp/ ./webapp/
COPY pyproject.toml ./
COPY README.md ./

# Install the application
RUN pip install --no-deps -e .

# Copy scripts
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh scripts/*.py

# Switch to non-root user
USER appuser

# Create model download script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🤖 Starting Ollama and downloading models..."\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
sleep 5\n\
echo "📥 Downloading Qwen2.5-VL..."\n\
ollama pull qwen2.5-vl:7b || echo "Failed to download qwen2.5-vl"\n\
echo "📥 Downloading LLaVA..."\n\
ollama pull llava:7b || echo "Failed to download llava"\n\
kill $OLLAMA_PID 2>/dev/null || true\n\
echo "✅ Model download complete"\n\
' > /app/download-models.sh && chmod +x /app/download-models.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import opensessionscribe; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "cli.main", "--help"]

# Labels
LABEL org.opencontainers.image.title="OpenSessionScribe"
LABEL org.opencontainers.image.description="Local podcast and webinar processing toolkit"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.source="https://github.com/kurtseifried/OpenSessionScribe"