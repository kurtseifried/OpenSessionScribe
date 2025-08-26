#!/bin/bash
set -e

echo "🤖 Setting up OpenSessionScribe AI models..."

# Check if Ollama is running
if ! pgrep -f "ollama serve" > /dev/null; then
    echo "⚠️  Ollama service not running. Starting it..."
    ollama serve &
    OLLAMA_PID=$!
    echo "   Ollama started (PID: $OLLAMA_PID)"
    sleep 5  # Give Ollama time to start
    STARTED_OLLAMA=true
else
    echo "✅ Ollama service is running"
    STARTED_OLLAMA=false
fi

# Function to download model with progress
download_model() {
    local model=$1
    echo "📥 Downloading $model..."
    
    if ollama list | grep -q "^$model"; then
        echo "   ✅ $model already downloaded"
        return 0
    fi
    
    echo "   This may take several minutes depending on your internet connection..."
    if ollama pull "$model"; then
        echo "   ✅ $model downloaded successfully"
    else
        echo "   ❌ Failed to download $model"
        return 1
    fi
}

# Download VLM models for slide descriptions
echo ""
echo "🖼️  Downloading Vision Language Models..."
download_model "qwen2.5-vl:7b"
download_model "llava:7b"

# Show available models
echo ""
echo "📋 Available models:"
ollama list

# Stop Ollama if we started it
if [ "$STARTED_OLLAMA" = true ]; then
    echo ""
    echo "🛑 Stopping Ollama service..."
    kill $OLLAMA_PID 2>/dev/null || true
    echo "   Ollama stopped. You can start it later with: ollama serve"
fi

echo ""
echo "🎉 Model setup complete!"
echo ""
echo "To use OpenSessionScribe:"
echo "1. Start Ollama: ollama serve"
echo "2. Run processing: opensessionscribe process <URL>"
echo ""
echo "Model storage location: ~/.ollama/models"
echo "Total model size: ~8-12 GB"
echo ""