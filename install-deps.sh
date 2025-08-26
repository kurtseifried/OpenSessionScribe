#!/bin/bash
set -e

echo "🔧 Installing OpenSessionScribe system dependencies..."

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only. Please install dependencies manually:"
    echo "   - FFmpeg"
    echo "   - Tesseract OCR"
    echo "   - Redis (optional, for Phase 2+)"
    exit 1
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✅ Homebrew found"

# Update brew
echo "📦 Updating Homebrew..."
brew update

# Install FFmpeg (required for audio/video processing)
echo "🎵 Installing FFmpeg..."
if brew list ffmpeg &>/dev/null; then
    echo "   FFmpeg already installed"
else
    brew install ffmpeg
fi

# Install Tesseract OCR (fallback OCR engine)
echo "👁️  Installing Tesseract OCR..."
if brew list tesseract &>/dev/null; then
    echo "   Tesseract already installed"
else
    brew install tesseract
fi

# Install additional Tesseract language packs
echo "🌍 Installing Tesseract language packs..."
brew install tesseract-lang

# Install Redis (for Phase 2+ background jobs)
echo "🔄 Installing Redis (optional)..."
if brew list redis &>/dev/null; then
    echo "   Redis already installed"
else
    brew install redis
    echo "   📝 Note: Redis installed but not started. To start:"
    echo "      brew services start redis"
fi

# Install Ollama (for VLM descriptions)
echo "🤖 Installing Ollama (for AI descriptions)..."
if brew list ollama &>/dev/null; then
    echo "   Ollama already installed"
else
    brew install ollama
    echo "   📝 Note: Ollama installed. To start the service:"
    echo "      ollama serve"
    echo "   To download models (after starting):"
    echo "      ollama pull qwen2.5-vl"
    echo "      ollama pull llava"
fi

# Optional: Install Python if not present
echo "🐍 Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "   ✅ Python $PYTHON_VERSION found"
    
    # Check if version is 3.9+
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
        echo "   ✅ Python version is 3.9+ (compatible)"
    else
        echo "   ⚠️  Python version is < 3.9. Installing newer Python..."
        brew install python@3.11
    fi
else
    echo "   ⚠️  Python not found. Installing Python..."
    brew install python@3.11
fi

echo ""
echo "🎉 All system dependencies installed!"
echo ""
echo "Next steps:"
echo "1. Install OpenSessionScribe: pip install -e ."
echo "2. Start Ollama service: ollama serve"
echo "3. Download VLM models: ollama pull qwen2.5-vl"
echo "4. Test installation: opensessionscribe hardware"
echo ""
echo "Optional (for Phase 2+):"
echo "- Start Redis: brew services start redis"
echo ""