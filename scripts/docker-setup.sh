#!/bin/bash
set -e

echo "🐳 OpenSessionScribe Docker Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if Docker is installed
check_docker() {
    print_status $BLUE "🔍 Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_status $RED "❌ Docker not found!"
        echo ""
        echo "Please install Docker first:"
        echo "  macOS: https://docs.docker.com/desktop/mac/install/"
        echo "  Linux: https://docs.docker.com/engine/install/"
        echo "  Windows: https://docs.docker.com/desktop/windows/install/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_status $RED "❌ Docker daemon not running!"
        echo ""
        echo "Please start Docker Desktop or the Docker service."
        exit 1
    fi
    
    print_status $GREEN "✅ Docker is installed and running"
}

# Check for GPU support
check_gpu_support() {
    print_status $BLUE "🔍 Checking GPU support..."
    
    local has_nvidia_gpu=false
    local has_nvidia_docker=false
    local gpu_recommendation=""
    
    # Check for NVIDIA GPU
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            local gpu_info=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
            print_status $GREEN "✅ NVIDIA GPU detected: $gpu_info"
            has_nvidia_gpu=true
        fi
    fi
    
    # Check for NVIDIA Container Toolkit
    if docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &> /dev/null; then
        print_status $GREEN "✅ NVIDIA Container Toolkit is working"
        has_nvidia_docker=true
    elif [ "$has_nvidia_gpu" = true ]; then
        print_status $YELLOW "⚠️  NVIDIA GPU found but Container Toolkit not working"
        echo ""
        echo "To enable GPU support in Docker:"
        echo "  Linux: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        echo "  Docker Desktop: Enable GPU support in settings"
        echo ""
        gpu_recommendation="cpu"
    fi
    
    # Check for Apple Silicon (MPS)
    if [[ "$OSTYPE" == "darwin"* ]] && [[ "$(uname -m)" == "arm64" ]]; then
        print_status $GREEN "✅ Apple Silicon detected (Metal Performance Shaders available)"
        gpu_recommendation="mps"
    fi
    
    # Determine recommendation
    if [ "$has_nvidia_gpu" = true ] && [ "$has_nvidia_docker" = true ]; then
        gpu_recommendation="cuda"
        print_status $GREEN "🚀 Recommended configuration: GPU-accelerated (CUDA)"
    elif [ "$has_nvidia_gpu" = true ]; then
        gpu_recommendation="cpu"
        print_status $YELLOW "🔧 Recommended configuration: CPU-only (GPU available but Docker integration needed)"
    else
        gpu_recommendation="cpu"
        print_status $BLUE "💻 Recommended configuration: CPU-only"
    fi
    
    echo $gpu_recommendation
}

# Get system specs for model recommendations
get_system_specs() {
    print_status $BLUE "🔍 Checking system specifications..."
    
    local total_ram=""
    if command -v free &> /dev/null; then
        total_ram=$(free -g | awk '/^Mem:/{print $2}')
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        total_ram=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
    fi
    
    local cpu_cores=""
    if command -v nproc &> /dev/null; then
        cpu_cores=$(nproc)
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        cpu_cores=$(sysctl -n hw.ncpu)
    fi
    
    echo "   RAM: ${total_ram}GB"
    echo "   CPU Cores: $cpu_cores"
    
    # Model recommendations based on specs
    local whisper_model="small"
    if [ "$total_ram" -ge 16 ]; then
        whisper_model="medium"
    fi
    if [ "$total_ram" -ge 32 ]; then
        whisper_model="large-v3"
    fi
    
    echo "   Recommended Whisper model: $whisper_model"
}

# Build Docker image with appropriate configuration
build_image() {
    local gpu_support=$1
    print_status $BLUE "🏗️  Building Docker image..."
    
    local build_args=""
    local image_tag="opensessionscribe:latest"
    
    case $gpu_support in
        "cuda")
            build_args="--build-arg GPU_SUPPORT=cuda"
            image_tag="opensessionscribe:gpu"
            ;;
        "mps")
            build_args="--build-arg GPU_SUPPORT=mps"
            image_tag="opensessionscribe:mps"
            ;;
        *)
            build_args="--build-arg GPU_SUPPORT=cpu"
            image_tag="opensessionscribe:cpu"
            ;;
    esac
    
    echo "Building with configuration: $gpu_support"
    echo "Image tag: $image_tag"
    echo ""
    
    if docker build $build_args -t $image_tag .; then
        print_status $GREEN "✅ Docker image built successfully: $image_tag"
    else
        print_status $RED "❌ Docker build failed!"
        exit 1
    fi
}

# Generate docker-compose.yml
generate_compose() {
    local gpu_support=$1
    print_status $BLUE "📝 Generating docker-compose.yml..."
    
    local compose_file="docker-compose.yml"
    local image_tag="opensessionscribe:cpu"
    local gpu_config=""
    
    case $gpu_support in
        "cuda")
            image_tag="opensessionscribe:gpu"
            gpu_config="    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]"
            ;;
        "mps")
            image_tag="opensessionscribe:mps"
            ;;
    esac
    
    cat > $compose_file << EOF
version: '3.8'

services:
  opensessionscribe:
    image: $image_tag
    container_name: opensessionscribe
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
      - ./cache:/app/cache
    environment:
      - OPENSESSIONSCRIBE_OFFLINE_ONLY=true
      - OPENSESSIONSCRIBE_MODELS_DIR=/app/models
      - OPENSESSIONSCRIBE_CACHE_DIR=/app/cache
$gpu_config
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    container_name: opensessionscribe-redis
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
EOF
    
    print_status $GREEN "✅ Generated $compose_file"
}

# Generate run script
generate_run_script() {
    local gpu_support=$1
    
    cat > scripts/docker-run.sh << 'EOF'
#!/bin/bash
# Auto-generated Docker run script for OpenSessionScribe

set -e

# Ensure required directories exist
mkdir -p data models cache

# Determine image tag based on configuration
IMAGE_TAG="opensessionscribe:cpu"
DOCKER_ARGS=""

# Add GPU support if available
if [ -f /proc/driver/nvidia/version ] && docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi &> /dev/null; then
    IMAGE_TAG="opensessionscribe:gpu"
    DOCKER_ARGS="--gpus all"
elif [[ "$OSTYPE" == "darwin"* ]] && [[ "$(uname -m)" == "arm64" ]]; then
    IMAGE_TAG="opensessionscribe:mps"
fi

echo "🚀 Starting OpenSessionScribe with $IMAGE_TAG"

docker run -it --rm \
    $DOCKER_ARGS \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/models:/app/models \
    -v $(pwd)/cache:/app/cache \
    -p 8000:8000 \
    $IMAGE_TAG "$@"
EOF
    
    chmod +x scripts/docker-run.sh
    print_status $GREEN "✅ Generated scripts/docker-run.sh"
}

# Main setup flow
main() {
    echo ""
    check_docker
    
    echo ""
    gpu_support=$(check_gpu_support)
    
    echo ""
    get_system_specs
    
    echo ""
    echo "🎯 Setup Plan:"
    echo "  GPU Support: $gpu_support"
    echo "  Docker Image: opensessionscribe:$([ "$gpu_support" != "cpu" ] && echo $gpu_support || echo cpu)"
    echo ""
    
    read -p "Proceed with Docker setup? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    
    echo ""
    build_image $gpu_support
    
    echo ""
    generate_compose $gpu_support
    
    echo ""
    generate_run_script $gpu_support
    
    echo ""
    print_status $GREEN "🎉 Docker setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Start services:    docker-compose up -d"
    echo "  2. Process content:   ./scripts/docker-run.sh process <URL>"
    echo "  3. Web interface:     http://localhost:8000"
    echo ""
    echo "Volume mounts:"
    echo "  ./data/     - Processing outputs"
    echo "  ./models/   - AI model cache"
    echo "  ./cache/    - Temporary files"
    echo ""
}

main "$@"