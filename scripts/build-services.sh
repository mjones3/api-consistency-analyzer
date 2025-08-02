#!/bin/bash

# Build Docker images for Spring Boot services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

build_api_governance() {
    log_info "Building API Governance Platform image..."
    
    if docker build -t api-governance:latest .; then
        log_success "API Governance Platform image built successfully"
    else
        log_error "Failed to build API Governance Platform image"
        return 1
    fi
}

build_legacy_service() {
    log_info "Building Legacy Donor Service image..."
    
    if docker build -t legacy-donor-service:latest ./examples/mock-services/legacy-donor-service/; then
        log_success "Legacy Donor Service image built successfully"
    else
        log_error "Failed to build Legacy Donor Service image"
        return 1
    fi
}

build_modern_service() {
    log_info "Building Modern Donor Service image..."
    
    if docker build -t modern-donor-service:latest ./examples/mock-services/modern-donor-service/; then
        log_success "Modern Donor Service image built successfully"
    else
        log_error "Failed to build Modern Donor Service image"
        return 1
    fi
}

load_images_to_kind() {
    local context=$(kubectl config current-context 2>/dev/null || echo "")
    
    if [[ "$context" == *"kind"* ]]; then
        log_info "Loading images into Kind cluster..."
        
        # Extract cluster name from context (e.g., kind-api-governance -> api-governance)
        local cluster_name=$(echo "$context" | sed 's/kind-//')
        
        kind load docker-image api-governance:latest --name "$cluster_name" || log_warning "Failed to load api-governance image"
        kind load docker-image legacy-donor-service:latest --name "$cluster_name" || log_warning "Failed to load legacy-donor-service image"
        kind load docker-image modern-donor-service:latest --name "$cluster_name" || log_warning "Failed to load modern-donor-service image"
        
        log_success "Images loaded into Kind cluster: $cluster_name"
    else
        log_info "Not using Kind cluster (context: $context), skipping image loading"
    fi
}

main() {
    echo "========================================"
    log_info "BUILDING DOCKER IMAGES FOR API GOVERNANCE PLATFORM"
    echo "========================================"
    
    # Build all images
    build_api_governance
    build_legacy_service
    build_modern_service
    
    # Load into Kind if applicable
    load_images_to_kind
    
    echo ""
    log_success "All Docker images built successfully!"
    echo ""
    log_info "Built images:"
    docker images | grep -E "(api-governance|legacy-donor-service|modern-donor-service)" | head -3
    
    echo ""
    log_info "Next steps:"
    echo "1. Deploy to Kubernetes: ./scripts/deploy-kubernetes.sh"
    echo "2. Or run locally: docker-compose up -d"
}

# Run main function
main "$@"