#!/bin/bash

# Deploy API Governance Platform and Blood Banking Services to Kubernetes with Istio

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

deploy_blood_banking_services() {
    log_step "Deploying Blood Banking Services..."
    
    # Apply blood banking services
    log_info "Creating blood-banking namespace with Istio injection..."
    kubectl apply -f k8s/blood-banking-services/legacy-donor-service.yaml
    
    log_info "Deploying Modern Donor Service..."
    kubectl apply -f k8s/blood-banking-services/modern-donor-service.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for blood banking services to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/legacy-donor-service -n blood-banking
    kubectl wait --for=condition=available --timeout=300s deployment/modern-donor-service -n blood-banking
    
    log_success "Blood Banking Services deployed successfully"
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
    echo "Blood Banking Services:"
    kubectl get pods -n blood-banking -o wide
    echo ""
    echo "API Governance Platform:"
    kubectl get pods -n api-governance -o wide
    
    # Check services
    log_info "Checking services..."
    echo ""
    echo "Blood Banking Services:"
    kubectl get svc -n blood-banking
    echo ""
    echo "API Governance Services:"
    kubectl get svc -n api-governance
    
    # Check Istio configuration
    log_info "Checking Istio configuration..."
    echo ""
    echo "VirtualServices:"
    kubectl get virtualservices -n blood-banking
    echo ""
    echo "DestinationRules:"
    kubectl get destinationrules -n blood-banking
    
    # Test service connectivity
    log_info "Testing service connectivity..."
    
    # Get API Governance pod name
    API_POD=$(kubectl get pods -n api-governance -l app=api-governance -o jsonpath='{.items[0].metadata.name}')
    
    if [ -n "$API_POD" ]; then
        log_info "Testing connectivity from API Governance pod..."
        
        # Test Legacy Service
        if kubectl exec -n api-governance $API_POD -- curl -s -f http://legacy-donor-service.blood-banking.svc.cluster.local:8081/actuator/health > /dev/null; then
            log_success "✓ Legacy Donor Service is accessible"
        else
            log_warning "✗ Legacy Donor Service is not accessible"
        fi
        
        # Test Modern Service
        if kubectl exec -n api-governance $API_POD -- curl -s -f http://modern-donor-service.blood-banking.svc.cluster.local:8082/actuator/health > /dev/null; then
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
echo "Starting port forwarding for Kubernetes services..."
echo ""
echo "API Governance Platform:"
echo "  Health Dashboard: http://localhost:8080/health/status"
echo "  API Endpoints: http://localhost:8080/api/v1/"
echo ""
echo "Blood Banking Services:"
echo "  Legacy Service: http://localhost:8081/swagger-ui.html"
echo "  Modern Service: http://localhost:8082/swagger-ui.html"
echo ""
echo "Istio Dashboards:"
echo "  Kiali: http://localhost:20001"
echo "  Grafana: http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "Press Ctrl+C to stop all port forwards"

# Start port forwards in background
kubectl port-forward svc/api-governance 8080:80 -n api-governance &
kubectl port-forward svc/legacy-donor-service 8081:8081 -n blood-banking &
kubectl port-forward svc/modern-donor-service 8082:8082 -n blood-banking &

# Istio dashboards (if available)
kubectl port-forward svc/kiali 20001:20001 -n istio-system &
kubectl port-forward svc/grafana 3000:3000 -n istio-system &
kubectl port-forward svc/prometheus 9090:9090 -n istio-system &

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
    echo "   ✓ Legacy Donor Service (blood-banking namespace)"
    echo "   ✓ Modern Donor Service (blood-banking namespace)"
    echo ""
    echo "🔗 Access Information:"
    echo ""
    echo "1. Start port forwarding:"
    echo "   ./port-forward-k8s.sh"
    echo ""
    echo "2. Access services:"
    echo "   • API Governance Dashboard: http://localhost:8080/health/status"
    echo "   • Legacy Service API: http://localhost:8081/swagger-ui.html"
    echo "   • Modern Service API: http://localhost:8082/swagger-ui.html"
    echo ""
    echo "3. View analysis results:"
    echo "   • Latest Report: http://localhost:8080/api/v1/reports/latest"
    echo "   • FHIR Recommendations: http://localhost:8080/api/v1/fhir/recommendations"
    echo "   • Discovered Services: http://localhost:8080/api/v1/discovered-services"
    echo ""
    echo "4. Monitor with Istio:"
    echo "   • Kiali: http://localhost:20001"
    echo "   • Grafana: http://localhost:3000"
    echo "   • Prometheus: http://localhost:9090"
    echo ""
    echo "📊 Kubernetes Commands:"
    echo "   • Check pods: kubectl get pods -n blood-banking -n api-governance"
    echo "   • View logs: kubectl logs -f deployment/api-governance -n api-governance"
    echo "   • Check Istio: kubectl get virtualservices,destinationrules -n blood-banking"
    echo ""
    echo "🔄 The API Governance Platform will automatically:"
    echo "   • Discover Spring Boot services in the blood-banking namespace"
    echo "   • Harvest their OpenAPI specifications"
    echo "   • Analyze API consistency and FHIR compliance"
    echo "   • Generate reports every 2 hours"
}

main() {
    echo "========================================"
    log_info "KUBERNETES DEPLOYMENT FOR API GOVERNANCE PLATFORM"
    echo "========================================"
    
    # Run deployment steps
    check_prerequisites
    deploy_blood_banking_services
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