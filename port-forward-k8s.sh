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
echo "  • FHIR Recommendations: http://localhost:8080/api/v1/fhir/recommendations"
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
