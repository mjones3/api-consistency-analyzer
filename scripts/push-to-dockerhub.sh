#!/bin/bash

# Push API Governance Platform images to Docker Hub
# Usage: ./scripts/push-to-dockerhub.sh [username]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get Docker Hub username
DOCKERHUB_USERNAME=${1:-"melvinjones3"}

# Define images to push
IMAGES=(
    "api-governance"
    "legacy-donor-service"
    "modern-donor-service"
)

# Define version
VERSION="v1.0.0"

echo "========================================"
log_info "PUSHING IMAGES TO DOCKER HUB"
echo "========================================"
echo ""
log_info "Docker Hub Username: ${CYAN}$DOCKERHUB_USERNAME${NC}"
log_info "Version: ${CYAN}$VERSION${NC}"
echo ""

# Check if user is logged in
if ! docker info | grep -q "Username: $DOCKERHUB_USERNAME"; then
    log_warning "Not logged in to Docker Hub as $DOCKERHUB_USERNAME"
    log_info "Attempting to login..."
    docker login --username "$DOCKERHUB_USERNAME"
fi

log_success "Logged in to Docker Hub as $DOCKERHUB_USERNAME"
echo ""

# Function to check if local image exists
check_local_image() {
    local image_name=$1
    if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "^${image_name}:latest$"; then
        return 0
    else
        return 1
    fi
}

# Function to tag and push image
tag_and_push_image() {
    local image_name=$1
    local dockerhub_repo="$DOCKERHUB_USERNAME/$image_name"
    
    log_info "Processing image: ${CYAN}$image_name${NC}"
    
    # Check if local image exists
    if ! check_local_image "$image_name"; then
        log_error "Local image $image_name:latest not found"
        log_info "Please run: ./scripts/build-services.sh"
        return 1
    fi
    
    # Tag images
    log_info "Tagging $image_name..."
    docker tag "$image_name:latest" "$dockerhub_repo:latest"
    docker tag "$image_name:latest" "$dockerhub_repo:$VERSION"
    
    # Push latest tag
    log_info "Pushing $dockerhub_repo:latest..."
    if docker push "$dockerhub_repo:latest"; then
        log_success "✅ Successfully pushed $dockerhub_repo:latest"
    else
        log_error "❌ Failed to push $dockerhub_repo:latest"
        log_warning "Repository might not exist. Please create it at: https://hub.docker.com/repository/create"
        return 1
    fi
    
    # Push version tag
    log_info "Pushing $dockerhub_repo:$VERSION..."
    if docker push "$dockerhub_repo:$VERSION"; then
        log_success "✅ Successfully pushed $dockerhub_repo:$VERSION"
    else
        log_error "❌ Failed to push $dockerhub_repo:$VERSION"
        return 1
    fi
    
    echo ""
}

# Function to create repository creation instructions
show_repository_creation_instructions() {
    echo ""
    log_warning "If you get 'access denied' errors, you need to create the repositories first:"
    echo ""
    echo "1. Go to: ${CYAN}https://hub.docker.com/repository/create${NC}"
    echo "2. Create these repositories:"
    for image in "${IMAGES[@]}"; do
        echo "   • ${CYAN}$DOCKERHUB_USERNAME/$image${NC}"
    done
    echo "3. Set them as ${CYAN}Public${NC} (or Private if preferred)"
    echo "4. Re-run this script"
    echo ""
}

# Main execution
main() {
    # Show repository creation instructions first
    show_repository_creation_instructions
    
    # Ask user if they want to continue
    read -p "Have you created the repositories on Docker Hub? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Please create the repositories first, then re-run this script"
        exit 0
    fi
    
    # Process each image
    local success_count=0
    local total_count=${#IMAGES[@]}
    
    for image in "${IMAGES[@]}"; do
        if tag_and_push_image "$image"; then
            ((success_count++))
        fi
    done
    
    echo "========================================"
    if [ $success_count -eq $total_count ]; then
        log_success "🎉 ALL IMAGES PUSHED SUCCESSFULLY!"
        echo ""
        log_info "Your images are now available at:"
        for image in "${IMAGES[@]}"; do
            echo "  • ${CYAN}https://hub.docker.com/r/$DOCKERHUB_USERNAME/$image${NC}"
        done
        echo ""
        log_info "To use these images in Kubernetes:"
        echo "  • Update your deployment YAML files"
        echo "  • Change image references from 'image-name:latest' to '$DOCKERHUB_USERNAME/image-name:latest'"
        echo "  • Or use the versioned tags: '$DOCKERHUB_USERNAME/image-name:$VERSION'"
    else
        log_warning "⚠️  $success_count/$total_count images pushed successfully"
        log_info "Check the errors above and retry failed pushes"
    fi
    echo "========================================"
}

# Function to show current tagged images
show_tagged_images() {
    echo ""
    log_info "Currently tagged images for Docker Hub:"
    docker images | grep "$DOCKERHUB_USERNAME" | head -20
    echo ""
}

# Command line options
case "${1:-}" in
    "--help"|"-h")
        echo "Usage: $0 [dockerhub-username]"
        echo ""
        echo "This script will:"
        echo "1. Tag your local images for Docker Hub"
        echo "2. Push them to your Docker Hub repositories"
        echo ""
        echo "Prerequisites:"
        echo "- Docker images built locally (run ./scripts/build-services.sh)"
        echo "- Docker Hub account and repositories created"
        echo "- Logged in to Docker Hub (docker login)"
        exit 0
        ;;
    "--show-images")
        show_tagged_images
        exit 0
        ;;
    *)
        main
        ;;
esac