#!/bin/bash
set -e

# OpenSessionScribe Quick Start
# Get up and running in under 5 minutes

echo "🚀 OpenSessionScribe Quick Start"
echo "================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [[ ! -f "cli/main.py" ]]; then
    echo -e "${RED}❌ Please run this script from the OpenSessionScribe root directory${NC}"
    exit 1
fi

echo -e "${BLUE}This script will:${NC}"
echo "1. Check system requirements"
echo "2. Install dependencies (with permission)"
echo "3. Run a quick test"
echo "4. Show next steps"
echo ""

# Step 1: Quick system check
echo -e "${YELLOW}Step 1: Checking system...${NC}"

# Check Python version
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
    echo -e "${RED}❌ Python 3.9+ required${NC}"
    echo "Please install Python 3.9+ and try again"
    exit 1
fi
echo -e "${GREEN}✅ Python 3.9+ found${NC}"

# Check if key commands exist
missing_commands=()

if ! command -v ffmpeg &> /dev/null; then
    missing_commands+=("ffmpeg")
fi

if ! command -v yt-dlp &> /dev/null && ! python3 -c "import yt_dlp" 2>/dev/null; then
    missing_commands+=("yt-dlp")
fi

# Step 2: Install missing dependencies
if [ ${#missing_commands[@]} -gt 0 ]; then
    echo -e "${YELLOW}Step 2: Installing system dependencies...${NC}"
    echo "Missing: ${missing_commands[*]}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            echo "Installing with Homebrew..."
            brew install ffmpeg yt-dlp
        else
            echo -e "${RED}❌ Homebrew not found. Please install from https://brew.sh/${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            echo "Installing with apt-get..."
            sudo apt-get update && sudo apt-get install -y ffmpeg
            pip3 install --user yt-dlp
        else
            echo -e "${RED}❌ Please install ffmpeg and yt-dlp manually${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Unsupported OS. Please install ffmpeg and yt-dlp manually${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
else
    echo -e "${GREEN}✅ System dependencies found${NC}"
fi

# Step 3: Install Python dependencies
echo -e "${YELLOW}Step 3: Installing Python packages...${NC}"

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
if [[ -f "requirements.txt" ]]; then
    echo "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Python packages installed${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing core packages...${NC}"
    pip install --upgrade pip
    pip install typer pydantic pyyaml requests whisperx pyannote-audio paddleocr torch torchaudio
fi

# Step 4: Quick functionality test
echo -e "${YELLOW}Step 4: Running quick test...${NC}"

# Test basic functionality
if python -m cli.main check --quiet; then
    echo -e "${GREEN}✅ Basic functionality test passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some optional dependencies missing (this is usually OK)${NC}"
fi

# Test with a quick example
echo -e "${YELLOW}Step 5: Running example...${NC}"
echo "Processing a short test video (this may take a minute)..."

TEST_OUTPUT="./quickstart-test"
mkdir -p "$TEST_OUTPUT"

if python -m cli.main process "https://youtube.com/watch?v=jNQXAC9IVRw" \
   --output "$TEST_OUTPUT" \
   --no-slides \
   --no-descriptions \
   --whisper-model tiny \
   2>/dev/null; then
    
    echo -e "${GREEN}🎉 Success! Test video processed${NC}"
    echo ""
    echo "📋 Results:"
    if [[ -f "$TEST_OUTPUT/package.json" ]]; then
        SEGMENTS=$(python3 -c "import json; data=json.load(open('$TEST_OUTPUT/package.json')); print(len(data['transcript']['segments']))" 2>/dev/null || echo "unknown")
        echo "  • Transcript segments: $SEGMENTS"
        echo "  • Output directory: $TEST_OUTPUT"
        echo "  • Main result file: $TEST_OUTPUT/package.json"
    fi
else
    echo -e "${YELLOW}⚠️  Test processing had issues, but installation appears successful${NC}"
fi

# Step 6: Next steps
echo ""
echo -e "${BLUE}🎯 Next Steps:${NC}"
echo "================================"
echo ""
echo "1. 📖 View full documentation:"
echo "   cat README.md"
echo ""
echo "2. 🔧 Check system capabilities:"
echo "   python -m cli.main hardware"
echo ""
echo "3. 🎬 Process your own video:"
echo "   python -m cli.main process 'YOUR_YOUTUBE_URL' --output ./my-output"
echo ""
echo "4. 📚 See more examples:"
echo "   ./examples/basic-usage.sh"
echo ""
echo "5. ⚙️  Advanced configuration:"
echo "   cat docs/CONFIGURATION.md"
echo ""

# Optional Ollama setup
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Optional: Install Ollama for AI slide descriptions${NC}"
    echo "• macOS: brew install ollama"
    echo "• Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "• Then: ollama pull qwen2-vl"
    echo ""
fi

echo -e "${GREEN}🚀 OpenSessionScribe is ready to use!${NC}"
echo ""
echo "To get started with a new terminal session:"
echo "1. cd $(pwd)"
echo "2. source venv/bin/activate"
echo "3. python -m cli.main --help"

# Cleanup test if successful
if [[ -d "$TEST_OUTPUT" ]]; then
    read -p "Remove test output directory? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$TEST_OUTPUT"
        echo "Test directory cleaned up"
    fi
fi