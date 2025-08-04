#!/bin/bash

# Enhanced Local Access Guide for API Governance Platform with Istio Monitoring

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
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

cleanup() {
    echo ""
    log_info "Stopping all port forwards..."
    jobs -p | xargs -r kill
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "========================================"
echo -e "${PURPLE}🚀 API GOVERNANCE PLATFORM - LOCAL ACCESS GUIDE${NC}"
echo "========================================"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot access Kubernetes cluster"
    echo "Please ensure your kubectl is configured correctly"
    exit 1
fi

log_success "Kubernetes cluster is accessible"

# Check current context
CONTEXT=$(kubectl config current-context)
log_info "Current context: ${CYAN}$CONTEXT${NC}"
echo ""

# Check if API Governance is deployed
if kubectl get deployment api-governance -n api-governance &> /dev/null; then
    log_success "API Governance Platform is deployed"
    
    # Check pod status
    POD_STATUS=$(kubectl get pods -n api-governance -l app=api-governance -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    if [ "$POD_STATUS" = "Running" ]; then
        log_success "API Governance pod is running"
    else
        log_warning "API Governance pod status: $POD_STATUS"
    fi
else
    log_error "API Governance Platform is not deployed"
    echo "Run: ${CYAN}./scripts/deploy-kubernetes.sh${NC}"
    exit 1
fi

# Check API services
log_info "Checking API services..."
if kubectl get namespace api &> /dev/null; then
    LEGACY_STATUS=$(kubectl get pods -n api -l app=legacy-donor-service -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    MODERN_STATUS=$(kubectl get pods -n api -l app=modern-donor-service -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    
    if [ "$LEGACY_STATUS" = "Running" ]; then
        log_success "Legacy Donor Service is running"
    else
        log_warning "Legacy Donor Service status: $LEGACY_STATUS"
    fi
    
    if [ "$MODERN_STATUS" = "Running" ]; then
        log_success "Modern Donor Service is running"
    else
        log_warning "Modern Donor Service status: $MODERN_STATUS"
    fi
else
    log_warning "API namespace not found"
fi

# Check Istio
log_info "Checking Istio installation..."
if kubectl get namespace istio-system &> /dev/null; then
    ISTIO_PODS=$(kubectl get pods -n istio-system --no-headers | wc -l)
    log_success "Istio is installed with $ISTIO_PODS pods"
else
    log_warning "Istio system namespace not found"
fi

echo ""
log_info "🚀 Starting enhanced port forwarding..."
echo ""

# Function to start port forward with enhanced logging
start_port_forward() {
    local service=$1
    local local_port=$2
    local remote_port=$3
    local namespace=$4
    local description=$5
    local url_path=${6:-""}
    
    if kubectl get svc "$service" -n "$namespace" &>/dev/null; then
        log_info "Starting port forward for $description..."
        kubectl port-forward svc/"$service" "$local_port:$remote_port" -n "$namespace" >/dev/null 2>&1 &
        local pid=$!
        sleep 1
        
        # Check if port forward is working
        if kill -0 $pid 2>/dev/null; then
            log_success "✅ $description: ${CYAN}http://localhost:$local_port$url_path${NC}"
        else
            log_warning "✗ Failed to start port forward for $description"
        fi
    else
        log_warning "✗ Service $service not found in namespace $namespace"
    fi
}

# Start all port forwards with enhanced URLs
echo -e "${BLUE}📊 API Governance Platform:${NC}"
start_port_forward "api-governance" "8080" "80" "api-governance" "Main Dashboard" "/"
start_port_forward "api-governance" "8090" "9090" "api-governance" "Metrics Endpoint" "/metrics"

echo ""
echo -e "${BLUE}🔗 API Services:${NC}"
start_port_forward "legacy-donor-service" "8081" "8081" "api" "Legacy Donor Service" "/swagger-ui.html"
start_port_forward "modern-donor-service" "8082" "8082" "api" "Modern Donor Service" "/swagger-ui.html"

echo ""
echo -e "${BLUE}🔍 Istio Service Mesh Monitoring:${NC}"
start_port_forward "kiali" "20001" "20001" "istio-system" "Kiali Dashboard" "/kiali/"
start_port_forward "grafana" "3000" "3000" "istio-system" "Grafana Dashboards" "/"
start_port_forward "prometheus" "9090" "9090" "istio-system" "Prometheus Metrics" "/"
start_port_forward "istio-ingressgateway" "15021" "15021" "istio-system" "Istio Gateway Status" "/"

echo ""
echo "========================================"
echo -e "${GREEN}🎯 QUICK ACCESS DASHBOARD${NC}"
echo "========================================"
echo ""
echo -e "${PURPLE}🚀 API Governance Platform:${NC}"
echo -e "  • ${CYAN}Main Dashboard:${NC}           http://localhost:8080/"
echo -e "  • ${CYAN}Health Check:${NC}             http://localhost:8080/health/"
echo -e "  • ${CYAN}API Documentation:${NC}        http://localhost:8080/docs"
echo -e "  • ${CYAN}Latest Report:${NC}            http://localhost:8080/api/v1/reports/latest"
echo -e "  • ${CYAN}Style Guide Recommendations:${NC} http://localhost:8080/api/v1/style-guide/recommendations"
echo -e "  • ${CYAN}Discovered Services:${NC}      http://localhost:8080/api/v1/discovered-services"
echo -e "  • ${CYAN}Prometheus Metrics:${NC}       http://localhost:8090/metrics"
echo ""
echo -e "${PURPLE}🔗 API Services:${NC}"
echo -e "  • ${CYAN}Legacy Service API:${NC}       http://localhost:8081/swagger-ui.html"
echo -e "  • ${CYAN}Legacy Health:${NC}            http://localhost:8081/actuator/health"
echo -e "  • ${CYAN}Modern Service API:${NC}       http://localhost:8082/swagger-ui.html"
echo -e "  • ${CYAN}Modern Health:${NC}            http://localhost:8082/actuator/health"
echo ""
echo -e "${PURPLE}🔍 Istio Service Mesh:${NC}"
echo -e "  • ${CYAN}Kiali (Service Graph):${NC}    http://localhost:20001/kiali/"
echo -e "  • ${CYAN}Grafana (Dashboards):${NC}     http://localhost:3000/"
echo -e "  • ${CYAN}Prometheus (Metrics):${NC}     http://localhost:9090/"
echo -e "  • ${CYAN}Istio Gateway:${NC}            http://localhost:15021/"
echo ""
echo -e "${PURPLE}🔧 Useful Commands:${NC}"
echo -e "  • ${YELLOW}Check all pods:${NC}          kubectl get pods -A"
echo -e "  • ${YELLOW}View governance logs:${NC}    kubectl logs -f deployment/api-governance -n api-governance"
echo -e "  • ${YELLOW}Check Istio config:${NC}      kubectl get virtualservices,destinationrules -A"
echo -e "  • ${YELLOW}Service mesh status:${NC}     istioctl proxy-status"
echo -e "  • ${YELLOW}Trigger analysis:${NC}        curl -X POST http://localhost:8080/api/v1/harvest/trigger"
echo ""
echo -e "${PURPLE}📊 Monitoring Highlights:${NC}"
echo -e "  • ${GREEN}Service Discovery:${NC}        Real-time via Istio"
echo -e "  • ${GREEN}Style Guide Compliance:${NC}   Customizable API standards"
echo -e "  • ${GREEN}API Consistency:${NC}          Cross-service analysis"
echo -e "  • ${GREEN}Performance Metrics:${NC}      Prometheus + Grafana"
echo -e "  • ${GREEN}Service Mesh Viz:${NC}         Kiali topology"
echo ""
echo "========================================"
echo -e "${GREEN}✨ SYSTEM IS READY FOR USE!${NC}"
echo "========================================"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all port forwards${NC}"

# Wait for all background jobs
wait