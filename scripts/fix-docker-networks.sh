#!/bin/bash

# Fix Docker network conflicts for API Governance Platform

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

show_docker_networks() {
    log_info "Current Docker networks:"
    docker network ls
    echo ""
    
    log_info "Network details with IP ranges:"
    docker network ls --format "table {{.Name}}\t{{.Driver}}" | tail -n +2 | while read name driver; do
        if [ "$driver" = "bridge" ]; then
            subnet=$(docker network inspect "$name" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "N/A")
            echo "  $name: $subnet"
        fi
    done
    echo ""
}

cleanup_conflicting_networks() {
    log_info "Cleaning up potential conflicting networks..."
    
    # Stop any running containers from this project
    log_info "Stopping containers from api-consistency-analyzer project..."
    docker-compose down 2>/dev/null || true
    
    # Remove networks that might conflict
    local conflicting_networks=(
        "api-consistency-analyzer_api-governance"
        "api-consistency-analyzer_default"
        "microservices-api-governance_api-governance"
        "microservices-api-governance_default"
    )
    
    for network in "${conflicting_networks[@]}"; do
        if docker network ls | grep -q "$network"; then
            log_info "Removing conflicting network: $network"
            docker network rm "$network" 2>/dev/null || log_warning "Could not remove $network (may be in use)"
        fi
    done
}

find_available_subnet() {
    log_info "Finding available subnet..."
    
    # Common private subnets to try
    local subnets=(
        "172.25.0.0/16"
        "172.26.0.0/16"
        "172.27.0.0/16"
        "172.28.0.0/16"
        "172.29.0.0/16"
        "192.168.100.0/24"
        "192.168.101.0/24"
        "192.168.102.0/24"
    )
    
    for subnet in "${subnets[@]}"; do
        # Check if subnet is already in use
        if ! docker network ls -q | xargs -I {} docker network inspect {} --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null | grep -q "$subnet"; then
            log_success "Available subnet found: $subnet"
            return 0
        fi
    done
    
    log_warning "All common subnets appear to be in use"
    return 1
}

update_docker_compose_subnet() {
    local new_subnet="$1"
    log_info "Updating docker-compose.yml to use subnet: $new_subnet"
    
    # Create backup
    cp docker-compose.yml docker-compose.yml.backup
    
    # Update subnet in docker-compose.yml
    sed -i.tmp "s|subnet: 172\.[0-9]\+\.0\.0/16|subnet: $new_subnet|g" docker-compose.yml
    rm -f docker-compose.yml.tmp
    
    log_success "Updated docker-compose.yml with new subnet"
}

prune_docker_resources() {
    log_warning "This will remove unused Docker resources. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Pruning unused Docker networks..."
        docker network prune -f
        
        log_info "Pruning unused Docker volumes..."
        docker volume prune -f
        
        log_success "Docker resources pruned"
    else
        log_info "Skipping Docker resource pruning"
    fi
}

test_docker_compose() {
    log_info "Testing docker-compose configuration..."
    
    if docker-compose config >/dev/null 2>&1; then
        log_success "docker-compose.yml configuration is valid"
    else
        log_error "docker-compose.yml configuration has errors:"
        docker-compose config
        return 1
    fi
    
    log_info "Attempting to create networks..."
    if docker-compose up --no-start 2>/dev/null; then
        log_success "Networks created successfully"
        docker-compose down
    else
        log_error "Failed to create networks"
        return 1
    fi
}

main() {
    log_info "Docker Network Conflict Resolver for API Governance Platform"
    echo ""
    
    # Show current state
    show_docker_networks
    
    # Clean up conflicting networks
    cleanup_conflicting_networks
    
    # Find available subnet
    if find_available_subnet; then
        # Test current configuration first
        if ! test_docker_compose; then
            log_info "Current configuration failed, trying different subnet..."
            update_docker_compose_subnet "172.26.0.0/16"
        fi
    else
        log_warning "Could not find available subnet automatically"
        log_info "You may need to manually edit docker-compose.yml"
    fi
    
    # Offer to prune unused resources
    echo ""
    prune_docker_resources
    
    # Final test
    echo ""
    log_info "Final configuration test..."
    if test_docker_compose; then
        log_success "Docker Compose is ready to use!"
        echo ""
        log_info "You can now run:"
        log_info "  docker-compose up -d"
    else
        log_error "Configuration still has issues"
        echo ""
        log_info "Manual steps to try:"
        log_info "1. Check existing networks: docker network ls"
        log_info "2. Remove conflicting networks: docker network rm <network_name>"
        log_info "3. Edit docker-compose.yml to use a different subnet"
        log_info "4. Try: docker network prune -f"
    fi
}

# Run main function
main "$@"