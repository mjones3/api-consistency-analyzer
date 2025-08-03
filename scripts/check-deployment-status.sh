#!/bin/bash

# Check deployment status for API Governance Platform

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

check_namespaces() {
    log_info "Checking namespaces..."
    
    if kubectl get namespace api-governance &> /dev/null; then
        log_success "✓ api-governance namespace exists"
    else
        log_error "✗ api-governance namespace missing"
        return 1
    fi
    
    if kubectl get namespace api &> /dev/null; then
        log_success "✓ api namespace exists"
    else
        log_warning "✗ api namespace missing"
        echo "  Creating api namespace..."
        kubectl create namespace api
        kubectl label namespace api istio-injection=enabled
    fi
}

check_deployments() {
    log_info "Checking deployments..."
    
    echo ""
    echo "API Governance namespace:"
    kubectl get pods -n api-governance -o wide || echo "  No pods found"
    
    echo ""
    echo "Blood Banking namespace:"
    kubectl get pods -n api -o wide || echo "  No pods found"
    
    echo ""
    echo "Services:"
    kubectl get svc -n api-governance || echo "  No services in api-governance"
    kubectl get svc -n api || echo "  No services in api"
}

check_docker_images() {
    log_info "Checking Docker images..."
    
    if kubectl config current-context | grep -q "kind"; then
        log_info "Detected Kind cluster, checking loaded images..."
        
        # Check if images are loaded in Kind
        if docker exec -it $(kubectl config current-context | cut -d'-' -f2)-control-plane crictl images 2>/dev/null | grep -q "api-governance"; then
            log_success "✓ api-governance image loaded in Kind"
        else
            log_warning "✗ api-governance image not found in Kind"
        fi
        
        if docker exec -it $(kubectl config current-context | cut -d'-' -f2)-control-plane crictl images 2>/dev/null | grep -q "legacy-donor-service"; then
            log_success "✓ legacy-donor-service image loaded in Kind"
        else
            log_warning "✗ legacy-donor-service image not found in Kind"
        fi
        
        if docker exec -it $(kubectl config current-context | cut -d'-' -f2)-control-plane crictl images 2>/dev/null | grep -q "modern-donor-service"; then
            log_success "✓ modern-donor-service image loaded in Kind"
        else
            log_warning "✗ modern-donor-service image not found in Kind"
        fi
    else
        log_info "Not using Kind cluster, skipping image check"
    fi
}

suggest_fixes() {
    log_info "Suggested fixes:"
    echo ""
    echo "1. Build and deploy everything:"
    echo "   ./scripts/deploy-kubernetes.sh"
    echo ""
    echo "2. Or build images first:"
    echo "   ./scripts/build-services.sh"
    echo ""
    echo "3. Then deploy manually:"
    echo "   kubectl apply -f k8s/"
    echo "   kubectl apply -f k8s/api-services/"
    echo ""
    echo "4. Check for errors:"
    echo "   kubectl describe pods -n api-governance"
    echo "   kubectl describe pods -n api"
    echo ""
    echo "5. View logs:"
    echo "   kubectl logs -l app=api-governance -n api-governance"
}

main() {
    echo "========================================"
    log_info "DEPLOYMENT STATUS CHECKER"
    echo "========================================"
    
    check_namespaces
    check_deployments
    check_docker_images
    suggest_fixes
    
    echo ""
    log_info "Current cluster context: $(kubectl config current-context)"
}

# Run main function
main "$@"