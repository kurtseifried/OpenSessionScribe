#!/bin/bash
set -e

# OpenSessionScribe Setup Script
# Installs system dependencies and Python packages

echo "🚀 Setting up OpenSessionScribe..."

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "requirements.txt" ]]; then
    echo "❌ Please run this script from the OpenSessionScribe root directory"
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
if [[ "$PLATFORM" == "macos" ]]; then
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install from https://brew.sh/"
        exit 1
    fi
    
    echo "  Installing with Homebrew..."
    brew install ffmpeg yt-dlp tesseract
    
    # Optional: Install Ollama for VLM descriptions
    if ! command -v ollama &> /dev/null; then
        echo "  Installing Ollama for VLM descriptions..."
        brew install ollama
        echo "  ⚠️  Remember to start Ollama service: ollama serve"
    fi
    
elif [[ "$PLATFORM" == "linux" ]]; then
    # Detect Linux distribution
    if command -v apt-get &> /dev/null; then
        echo "  Installing with apt-get (Ubuntu/Debian)..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg tesseract-ocr python3-pip python3-venv
        
        # Install yt-dlp via pip since apt version is often outdated
        pip3 install --user yt-dlp
        
        # Install Ollama
        if ! command -v ollama &> /dev/null; then
            echo "  Installing Ollama..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        
    elif command -v yum &> /dev/null; then
        echo "  Installing with yum (RHEL/CentOS)..."
        sudo yum install -y ffmpeg tesseract python3-pip
        pip3 install --user yt-dlp
        
        # Install Ollama
        if ! command -v ollama &> /dev/null; then
            echo "  Installing Ollama..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
        
    else
        echo "❌ Unsupported Linux distribution. Please install manually:"
        echo "   - ffmpeg"
        echo "   - tesseract-ocr"
        echo "   - yt-dlp"
        echo "   - ollama (optional)"
        exit 1
    fi
fi

# Check if Python 3.9+ is available
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 9 ]]; then
    echo "❌ Python 3.9+ required. Found Python $PYTHON_VERSION"
    echo "   Please install Python 3.9 or later"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Verify installation
echo "🔍 Verifying installation..."
python -m cli.main check

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To get started:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Test with: python -m cli.main hardware"
echo "3. Process a video: python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./test"
echo ""

# Optional: Setup VLM models
if command -v ollama &> /dev/null; then
    read -p "📥 Download VLM model for slide descriptions? (qwen2-vl ~2GB) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Downloading VLM model (this may take several minutes)..."
        ollama pull qwen2-vl
        echo "✅ VLM model downloaded"
    fi
    
    # Start Ollama service in background if not running
    if ! pgrep -f "ollama serve" > /dev/null; then
        echo "🚀 Starting Ollama service..."
        nohup ollama serve > /dev/null 2>&1 &
        sleep 2
        echo "✅ Ollama service started"
    fi
else
    echo "⚠️  Ollama not available. Slide descriptions will be disabled."
fi

echo ""
echo "🚀 OpenSessionScribe is ready to use!"
echo "   Run 'python -m cli.main --help' for usage information"