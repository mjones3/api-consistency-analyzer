#!/bin/bash

# Deploy API Governance Platform and API Services to Kubernetes with Istio

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    # Check if Istio is installed
    if ! kubectl get namespace istio-system &> /dev/null; then
        log_error "Istio is not installed. Please run ./scripts/setup-istio-stable.sh first"
        exit 1
    fi
    
    # Check if Docker images exist locally (for Kind)
    if kubectl config current-context | grep -q "kind"; then
        log_info "Detected Kind cluster, building and loading Docker images..."
        
        # Use the build script to build all images
        if ! ./scripts/build-services.sh; then
            log_error "Failed to build Docker images"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check completed"
}

deploy_api_services() {
    log_step "Deploying API Services..."
    
    # Apply API services
    log_info "Creating api namespace with Istio injection..."
    kubectl apply -f k8s/api-services/legacy-donor-service.yaml
    
    log_info "Deploying Modern Donor Service..."
    kubectl apply -f k8s/api-services/modern-donor-service.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for API services to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/legacy-donor-service -n api
    kubectl wait --for=condition=available --timeout=300s deployment/modern-donor-service -n api
    
    log_success "API Services deployed successfully"
}

deploy_api_governance() {
    log_step "Deploying API Governance Platform..."
    
    # Apply API Governance resources
    log_info "Creating api-governance namespace..."
    kubectl apply -f k8s/namespace.yaml
    
    log_info "Setting up RBAC..."
    kubectl apply -f k8s/rbac.yaml
    
    log_info "Creating ConfigMap..."
    kubectl apply -f k8s/configmap.yaml
    
    log_info "Creating PVC..."
    kubectl apply -f k8s/pvc.yaml
    
    log_info "Deploying API Governance Platform..."
    kubectl apply -f k8s/deployment.yaml
    
    log_info "Creating Service..."
    kubectl apply -f k8s/service.yaml
    
    # Apply Istio configuration
    log_info "Applying Istio configuration..."
    kubectl apply -f k8s/istio/
    
    # Wait for deployment to be ready
    log_info "Waiting for API Governance Platform to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/api-governance -n api-governance
    
    log_success "API Governance Platform deployed successfully"
}

verify_deployment() {
    log_step "Verifying deployment..."
    
    # Check all pods are running
    log_info "Checking pod status..."
    echo ""
    echo "API Services:"
    kubectl get pods -n api -o wide
    echo ""
    echo "API Governance Platform:"
    kubectl get pods -n api-governance -o wide
    
    # Check services
    log_info "Checking services..."
    echo ""
    echo "API Services:"
    kubectl get svc -n api
    echo ""
    echo "API Governance Services:"
    kubectl get svc -n api-governance
    
    # Check Istio configuration
    log_info "Checking Istio configuration..."
    echo ""
    echo "VirtualServices:"
    kubectl get virtualservices -n api
    echo ""
    echo "DestinationRules:"
    kubectl get destinationrules -n api
    
    # Test service connectivity
    log_info "Testing service connectivity..."
    
    # Get API Governance pod name
    API_POD=$(kubectl get pods -n api-governance -l app=api-governance -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$API_POD" ]; then
        log_info "Testing connectivity from API Governance pod..."
        
        # Test Legacy Service
        if kubectl exec -n api-governance $API_POD -- curl -s -f http://legacy-donor-service.api.svc.cluster.local:8081/actuator/health > /dev/null; then
            log_success "✓ Legacy Donor Service is accessible"
        else
            log_warning "✗ Legacy Donor Service is not accessible"
        fi
        
        # Test Modern Service
        if kubectl exec -n api-governance $API_POD -- curl -s -f http://modern-donor-service.api.svc.cluster.local:8082/actuator/health > /dev/null; then
            log_success "✓ Modern Donor Service is accessible"
        else
            log_warning "✗ Modern Donor Service is not accessible"
        fi
    else
        log_warning "API Governance pod not found, skipping connectivity tests"
    fi
    
    log_success "Deployment verification completed"
}

setup_port_forwarding() {
    log_step "Setting up port forwarding..."
    
    # Create port forwarding script
    cat > port-forward-k8s.sh << 'EOF'
#!/bin/bash

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

cleanup() {
    echo ""
    log_info "Stopping all port forwards..."
    jobs -p | xargs -r kill
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "========================================"
log_info "STARTING PORT FORWARDING FOR KUBERNETES SERVICES"
echo "========================================"
echo ""

log_info "🚀 API Governance Platform:"
echo "  • Main Dashboard: http://localhost:8080/"
echo "  • Health Check: http://localhost:8080/health/"
echo "  • API Endpoints: http://localhost:8080/api/v1/"
echo "  • Latest Report: http://localhost:8080/api/v1/reports/latest"
echo "  • Style Guide Recommendations: http://localhost:8080/api/v1/style-guide/recommendations"
echo ""

log_info "🔗 API Services:"
echo "  • Legacy Service API: http://localhost:8081/swagger-ui.html"
echo "  • Legacy Health: http://localhost:8081/actuator/health"
echo "  • Modern Service API: http://localhost:8082/swagger-ui.html"
echo "  • Modern Health: http://localhost:8082/actuator/health"
echo ""

log_info "📊 Istio Service Mesh Monitoring:"
echo "  • Kiali Dashboard: http://localhost:20001/kiali/"
echo "  • Grafana Dashboards: http://localhost:3000/"
echo "  • Prometheus Metrics: http://localhost:9090/"
echo "  • Istio Gateway: http://localhost:15021/"
echo ""

log_info "🔧 Useful Commands:"
echo "  • Check pods: kubectl get pods -A"
echo "  • View logs: kubectl logs -f deployment/api-governance -n api-governance"
echo "  • Istio config: kubectl get virtualservices,destinationrules -A"
echo ""

echo "Press Ctrl+C to stop all port forwards"
echo "========================================"

# Function to start port forward with retry
start_port_forward() {
    local service=$1
    local local_port=$2
    local remote_port=$3
    local namespace=$4
    local description=$5
    
    log_info "Starting port forward for $description..."
    
    # Check if service exists
    if kubectl get svc "$service" -n "$namespace" &>/dev/null; then
        kubectl port-forward svc/"$service" "$local_port:$remote_port" -n "$namespace" &
        local pid=$!
        sleep 1
        
        # Check if port forward is working
        if kill -0 $pid 2>/dev/null; then
            log_success "✓ $description available at http://localhost:$local_port"
        else
            log_warning "✗ Failed to start port forward for $description"
        fi
    else
        log_warning "✗ Service $service not found in namespace $namespace"
    fi
}

# Start all port forwards
start_port_forward "api-governance" "8080" "80" "api-governance" "API Governance Platform"
start_port_forward "legacy-donor-service" "8081" "8081" "api" "Legacy Donor Service"
start_port_forward "modern-donor-service" "8082" "8082" "api" "Modern Donor Service"

# Istio monitoring services
start_port_forward "kiali" "20001" "20001" "istio-system" "Kiali Dashboard"
start_port_forward "grafana" "3000" "3000" "istio-system" "Grafana Dashboards"
start_port_forward "prometheus" "9090" "9090" "istio-system" "Prometheus Metrics"
start_port_forward "istio-ingressgateway" "15021" "15021" "istio-system" "Istio Gateway Status"

echo ""
log_success "All port forwards started successfully!"
echo ""
log_info "🎯 Quick Access URLs:"
echo "  Main Dashboard: http://localhost:8080/"
echo "  Kiali (Service Mesh): http://localhost:20001/kiali/"
echo "  Grafana (Metrics): http://localhost:3000/"
echo ""

# Wait for all background jobs
wait
EOF
    
    chmod +x port-forward-k8s.sh
    log_success "Port forwarding script created: ./port-forward-k8s.sh"
}

trigger_initial_analysis() {
    log_step "Triggering initial API analysis..."
    
    # Wait a bit for services to fully start
    sleep 30
    
    # Get API Governance pod name
    API_POD=$(kubectl get pods -n api-governance -l app=api-governance -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$API_POD" ]; then
        log_info "Triggering harvest from API Governance pod..."
        
        # Trigger harvest
        kubectl exec -n api-governance $API_POD -- curl -s -X POST http://localhost:8080/api/v1/harvest/trigger \
            -H "Content-Type: application/json" \
            -d '{"force": true}' || log_warning "Failed to trigger harvest"
        
        log_info "Waiting for analysis to complete..."
        sleep 60
        
        log_success "Initial analysis triggered"
    else
        log_warning "API Governance pod not found, skipping initial analysis"
    fi
}

display_access_information() {
    echo ""
    echo "========================================"
    log_success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "========================================"
    echo ""
    echo "🚀 Services Deployed:"
    echo "   ✓ API Governance Platform (api-governance namespace)"
    echo "   ✓ Legacy Donor Service (api namespace)"
    echo "   ✓ Modern Donor Service (api namespace)"
    echo "   ✓ Istio Service Mesh with monitoring stack"
    echo ""
    echo "🔗 Quick Start:"
    echo ""
    echo "1. Start port forwarding:"
    echo "   ${GREEN}./port-forward-k8s.sh${NC}"
    echo ""
    echo "2. 🎯 Main Access Points:"
    echo "   • ${CYAN}API Governance Dashboard:${NC} http://localhost:8080/"
    echo "   • ${CYAN}Style Guide Compliance Analysis:${NC} http://localhost:8080/api/v1/reports/latest"
    echo "   • ${CYAN}Service Mesh Visualization:${NC} http://localhost:20001/kiali/"
    echo "   • ${CYAN}Metrics & Monitoring:${NC} http://localhost:3000/"
    echo ""
    echo "3. 🔗 API Services:"
    echo "   • ${CYAN}Legacy Service API:${NC} http://localhost:8081/swagger-ui.html"
    echo "   • ${CYAN}Modern Service API:${NC} http://localhost:8082/swagger-ui.html"
    echo ""
    echo "4. 📊 API Governance Endpoints:"
    echo "   • ${CYAN}Health Check:${NC} http://localhost:8080/health/"
    echo "   • ${CYAN}Latest Report:${NC} http://localhost:8080/api/v1/reports/latest"
    echo "   • ${CYAN}Style Guide Recommendations:${NC} http://localhost:8080/api/v1/style-guide/recommendations"
    echo "   • ${CYAN}Discovered Services:${NC} http://localhost:8080/api/v1/discovered-services"
    echo "   • ${CYAN}Trigger Analysis:${NC} curl -X POST http://localhost:8080/api/v1/harvest/trigger"
    echo ""
    echo "5. 🔍 Istio Service Mesh Monitoring:"
    echo "   • ${CYAN}Kiali (Service Graph):${NC} http://localhost:20001/kiali/"
    echo "   • ${CYAN}Grafana (Dashboards):${NC} http://localhost:3000/"
    echo "   • ${CYAN}Prometheus (Metrics):${NC} http://localhost:9090/"
    echo "   • ${CYAN}Istio Gateway Status:${NC} http://localhost:15021/"
    echo ""
    echo "📊 Useful Kubernetes Commands:"
    echo "   • ${YELLOW}Check all pods:${NC} kubectl get pods -A"
    echo "   • ${YELLOW}View governance logs:${NC} kubectl logs -f deployment/api-governance -n api-governance"
    echo "   • ${YELLOW}Check Istio config:${NC} kubectl get virtualservices,destinationrules -A"
    echo "   • ${YELLOW}Service mesh status:${NC} istioctl proxy-status"
    echo ""
    echo "🔄 Automated Features:"
    echo "   • ✅ Automatic service discovery via Istio"
    echo "   • ✅ OpenAPI specification harvesting"
    echo "   • ✅ API style guide compliance analysis"
    echo "   • ✅ API consistency reporting"
    echo "   • ✅ Continuous monitoring (every 6 hours)"
    echo ""
    echo "💡 Pro Tips:"
    echo "   • Wait 2-3 minutes after deployment for initial analysis"
    echo "   • Use Kiali to visualize service mesh traffic"
    echo "   • Check Grafana for detailed performance metrics"
    echo "   • Monitor logs for real-time analysis progress"
}

main() {
    echo "========================================"
    log_info "KUBERNETES DEPLOYMENT FOR API GOVERNANCE PLATFORM"
    echo "========================================"
    
    # Run deployment steps
    check_prerequisites
    deploy_api_services
    deploy_api_governance
    verify_deployment
    setup_port_forwarding
    trigger_initial_analysis
    display_access_information
    
    echo ""
    log_success "Deployment script completed!"
    echo ""
    log_info "Next steps:"
    echo "1. Run './port-forward-k8s.sh' to access services"
    echo "2. Wait a few minutes for initial analysis to complete"
    echo "3. Check results at http://localhost:8080/api/v1/reports/latest"
}

# Run main function
main "$@"