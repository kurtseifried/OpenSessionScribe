#!/bin/bash

# OpenSessionScribe Basic Usage Examples
# This script demonstrates common usage patterns

set -e

echo "🎯 OpenSessionScribe Basic Usage Examples"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [[ ! -f "cli/main.py" ]]; then
    echo -e "${RED}❌ Please run this script from the OpenSessionScribe root directory${NC}"
    exit 1
fi

# Function to run example with explanation
run_example() {
    local title="$1"
    local description="$2"
    local command="$3"
    local optional="$4"
    
    echo ""
    echo -e "${BLUE}📌 Example: $title${NC}"
    echo -e "   $description"
    echo ""
    echo -e "${YELLOW}Command:${NC}"
    echo "   $command"
    echo ""
    
    if [[ "$optional" != "skip" ]]; then
        read -p "Run this example? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}🚀 Running...${NC}"
            eval $command
            echo -e "${GREEN}✅ Complete${NC}"
        else
            echo -e "${YELLOW}⏭️  Skipped${NC}"
        fi
    fi
}

# Example 1: System Check
run_example \
    "System Diagnostics" \
    "Check system capabilities and dependencies" \
    "python -m cli.main check" \
    ""

# Example 2: Hardware Detection
run_example \
    "Hardware Detection" \
    "Show detected hardware and recommendations" \
    "python -m cli.main hardware" \
    ""

# Example 3: Basic URL Processing (no slides)
run_example \
    "Basic Video Processing (Fast)" \
    "Process YouTube video with transcription only (no slides)" \
    "python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./examples/output/basic --no-slides --verbose" \
    ""

# Example 4: Full Processing with Slides
run_example \
    "Full Video Processing" \
    "Process YouTube video with transcription + slide extraction" \
    "python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./examples/output/full --slides --no-descriptions --verbose" \
    ""

# Example 5: Audio-only Processing
echo ""
echo -e "${BLUE}📌 Example: Audio-Only Processing${NC}"
echo "   Process just the audio for podcasts (faster)"
echo ""
echo -e "${YELLOW}First, let's extract audio from our test video:${NC}"
echo "   python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./temp --no-slides --verbose"
echo ""
echo -e "${YELLOW}Then process the audio file directly:${NC}"
echo "   python -m cli.main transcribe ./temp/audio.wav --output ./examples/output/audio_transcript.json --verbose"
echo ""

# Example 6: Component Testing
run_example \
    "Test Individual Components" \
    "Test each component separately for debugging" \
    "echo 'Component tests:' && \
     python -m cli.main transcribe ./temp/audio.wav --verbose && \
     python -m cli.main diarize ./temp/audio.wav --verbose" \
    "skip"

# Example 7: Different Model Sizes
run_example \
    "Different Whisper Models" \
    "Compare speed vs quality with different model sizes" \
    "echo 'Testing with medium model (faster):' && \
     python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --output ./examples/output/medium --whisper-model medium --no-slides --verbose" \
    "skip"

# Example 8: Configuration File
cat > examples/config.yaml << EOF
# OpenSessionScribe Configuration Example
force_cpu: false
device: auto

# Models
whisper_model: large-v3
ocr_engine: tesseract
vlm_model: qwen2-vl

# Processing options
enable_slides: true
enable_descriptions: false
offline_only: true

# Paths
models_dir: ~/.opensessionscribe/models
cache_dir: ~/.opensessionscribe/cache
EOF

run_example \
    "Configuration File Usage" \
    "Use a configuration file for consistent settings" \
    "python -m cli.main process 'https://youtube.com/watch?v=jNQXAC9IVRw' --config examples/config.yaml --output ./examples/output/config --verbose" \
    "skip"

# Summary
echo ""
echo -e "${GREEN}🎉 Examples Complete!${NC}"
echo "=============================="
echo ""
echo "📁 Check output directories:"
echo "   examples/output/basic/     - Basic processing"
echo "   examples/output/full/      - Full processing with slides"
echo "   examples/output/audio/     - Audio-only transcription"
echo ""
echo "📄 Each directory contains:"
echo "   • package.json          - Main structured output"
echo "   • media files           - Downloaded/processed media"
echo "   • raw outputs           - Individual component results"
echo ""
echo "🔗 Useful commands for exploring results:"
echo "   jq '.transcript.segments[0]' examples/output/basic/package.json"
echo "   ls -la examples/output/full/slides/"
echo "   cat examples/output/basic/transcript_raw.json | jq '.segments'"
echo ""
echo "📖 For more advanced usage, see:"
echo "   python -m cli.main --help"
echo "   python -m cli.main process --help"