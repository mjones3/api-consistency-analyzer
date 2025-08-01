#!/bin/bash

# Setup local Istio environment - Ultra Stable Version
# Uses older, well-tested versions for maximum compatibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Ultra stable versions
ISTIO_VERSION="1.19.9"  # Last of 1.19 series, better CLI compatibility
CLUSTER_NAME="api-governance"
K8S_VERSION="v1.26.15"  # Stable and well-supported

# Functions
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

detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v kind &> /dev/null; then
        log_warning "Kind not found. Please install Kind for local development"
        log_info "Install with: brew install kind (macOS) or go install sigs.k8s.io/kind@latest"
    fi
    
    log_success "Prerequisites check completed"
}

create_kind_cluster() {
    log_info "Creating Kind cluster with stable configuration..."
    
    # Delete existing cluster if it exists
    kind delete cluster --name ${CLUSTER_NAME} 2>/dev/null || true
    
    cat <<EOF | kind create cluster --name ${CLUSTER_NAME} --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  image: kindest/node:${K8S_VERSION}
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 15021
    hostPort: 15021
    protocol: TCP
- role: worker
  image: kindest/node:${K8S_VERSION}
EOF
    
    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
    
    # Verify cluster
    kubectl cluster-info
    kubectl get nodes
    
    log_success "Kind cluster created and ready"
}

install_istio_stable() {
    log_info "Installing Istio ${ISTIO_VERSION} (stable version)..."
    
    # Download Istio
    if [ ! -d "istio-${ISTIO_VERSION}" ]; then
        log_info "Downloading Istio ${ISTIO_VERSION}..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
    fi
    
    # Add istioctl to PATH
    export PATH=$PWD/istio-${ISTIO_VERSION}/bin:$PATH
    
    # Verify istioctl (handle different version flag formats)
    log_info "Verifying istioctl installation..."
    if istioctl version --help 2>/dev/null | grep -q "\--client"; then
        ISTIO_CLIENT_VERSION=$(istioctl version --client --short 2>/dev/null || echo "unknown")
    else
        ISTIO_CLIENT_VERSION=$(istioctl version 2>/dev/null | head -1 || echo "unknown")
    fi
    log_info "Using istioctl version: ${ISTIO_CLIENT_VERSION}"
    
    # Pre-check cluster (skip if command doesn't exist in this version)
    if istioctl x precheck --help &>/dev/null; then
        log_info "Running pre-installation checks..."
        istioctl x precheck || log_warning "Pre-check had warnings, continuing..."
    else
        log_info "Skipping pre-check (not available in this Istio version)"
    fi
    
    # Install Istio with demo profile - use the most compatible approach
    log_info "Installing Istio control plane..."
    
    # Try different flag combinations for different Istio versions
    if istioctl install --help 2>/dev/null | grep -q "\--yes"; then
        # Newer versions use --yes
        CONFIRM_FLAG="--yes"
    elif istioctl install --help 2>/dev/null | grep -q "\-y"; then
        # Some versions use -y
        CONFIRM_FLAG="-y"
    else
        # Fallback: no confirmation flag, will prompt user
        CONFIRM_FLAG=""
        log_warning "Auto-confirmation not available, you may need to confirm installation manually"
    fi
    
    # Install with conservative settings
    if [ -n "$CONFIRM_FLAG" ]; then
        istioctl install --set values.defaultRevision=default \
            --set values.pilot.env.EXTERNAL_ISTIOD=false \
            --set values.gateways.istio-ingressgateway.type=NodePort \
            --set values.pilot.resources.requests.cpu=50m \
            --set values.pilot.resources.requests.memory=128Mi \
            --set values.global.proxy.resources.requests.cpu=10m \
            --set values.global.proxy.resources.requests.memory=40Mi \
            $CONFIRM_FLAG
    else
        # Interactive installation
        echo "Please confirm the installation when prompted..."
        istioctl install --set values.defaultRevision=default \
            --set values.pilot.env.EXTERNAL_ISTIOD=false \
            --set values.gateways.istio-ingressgateway.type=NodePort \
            --set values.pilot.resources.requests.cpu=50m \
            --set values.pilot.resources.requests.memory=128Mi \
            --set values.global.proxy.resources.requests.cpu=10m \
            --set values.global.proxy.resources.requests.memory=40Mi
    fi
    
    # Wait for istiod to be ready
    log_info "Waiting for Istio control plane..."
    kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
    
    # Enable Istio injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    # Verify installation
    log_info "Verifying Istio installation..."
    if istioctl verify-install --help &>/dev/null; then
        istioctl verify-install || log_warning "Verification had warnings, but installation may be functional"
    else
        log_info "Manual verification - checking Istio pods:"
        kubectl get pods -n istio-system
    fi
    
    log_success "Istio installed successfully"
}

install_basic_addons() {
    log_info "Installing basic Istio addons..."
    
    # Only install the most essential addons
    local essential_addons=("prometheus" "grafana" "kiali")
    
    for addon in "${essential_addons[@]}"; do
        if [ -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" ]; then
            log_info "Installing ${addon}..."
            kubectl apply -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml"
            sleep 10
        fi
    done
    
    # Wait for addons to be ready
    log_info "Waiting for addons to be ready..."
    for addon in "${essential_addons[@]}"; do
        if kubectl get deployment ${addon} -n istio-system &> /dev/null; then
            kubectl wait --for=condition=available --timeout=300s deployment/${addon} -n istio-system || {
                log_warning "${addon} not ready, but continuing..."
            }
        fi
    done
    
    log_success "Basic addons installed"
}

create_sample_app() {
    log_info "Creating sample application for testing..."
    
    kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: sample-app
  labels:
    istio-injection: enabled
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: httpbin
  namespace: sample-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: httpbin
  template:
    metadata:
      labels:
        app: httpbin
    spec:
      containers:
      - name: httpbin
        image: kennethreitz/httpbin
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: httpbin
  namespace: sample-app
spec:
  selector:
    app: httpbin
  ports:
  - port: 8000
    targetPort: 80
EOF
    
    log_success "Sample application created"
}

create_api_governance_namespace() {
    log_info "Creating API Governance namespace..."
    
    kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: api-governance
  labels:
    name: api-governance
    istio-injection: enabled
EOF
    
    log_success "API Governance namespace created"
}

setup_port_forwarding() {
    log_info "Setting up port forwarding script..."
    
    cat > port-forward-istio.sh << 'EOF'
#!/bin/bash
echo "Starting port forwarding for Istio addons..."
echo "Kiali: http://localhost:20001"
echo "Grafana: http://localhost:3000"  
echo "Prometheus: http://localhost:9090"
echo "Sample App: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all port forwards"

# Start port forwards in background
kubectl port-forward svc/kiali 20001:20001 -n istio-system &
kubectl port-forward svc/grafana 3000:3000 -n istio-system &
kubectl port-forward svc/prometheus 9090:9090 -n istio-system &
kubectl port-forward svc/httpbin 8000:8000 -n sample-app &

# Wait for all background jobs
wait
EOF
    
    chmod +x port-forward-istio.sh
    log_success "Port forwarding script created: ./port-forward-istio.sh"
}

validate_installation() {
    log_info "Validating installation..."
    
    # Check Istio components
    log_info "Istio system pods:"
    kubectl get pods -n istio-system
    
    # Check sample app
    log_info "Sample app pods:"
    kubectl get pods -n sample-app
    
    # Check Istio proxy status (if available)
    log_info "Checking Istio proxy status..."
    if istioctl proxy-status --help &>/dev/null; then
        istioctl proxy-status || log_warning "Some proxies may not be ready yet"
    else
        log_info "Proxy status command not available in this Istio version"
        log_info "Checking sidecar injection manually:"
        kubectl get pods -n sample-app -o jsonpath='{.items[*].spec.containers[*].name}' | grep -q istio-proxy && \
            log_info "✓ Istio sidecars are injected" || \
            log_warning "⚠ Istio sidecars may not be injected yet"
    fi
    
    # Display summary
    log_info "Installation summary:"
    
    # Get Istio version with fallback
    if istioctl version --help 2>/dev/null | grep -q "\--short"; then
        ISTIO_VERSION_OUTPUT=$(istioctl version --short 2>/dev/null || echo 'Unable to get version')
    else
        ISTIO_VERSION_OUTPUT=$(istioctl version 2>/dev/null | head -2 || echo 'Unable to get version')
    fi
    echo "Istio version: ${ISTIO_VERSION_OUTPUT}"
    
    echo "Cluster info:"
    kubectl cluster-info --context kind-${CLUSTER_NAME}
    
    # Check if services are accessible
    log_info "Checking service accessibility..."
    kubectl get svc -n istio-system
    kubectl get svc -n sample-app
    
    log_success "Installation validation completed"
}

cleanup() {
    log_warning "Cleaning up on exit..."
    # Kill any background port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
}

main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    log_info "Starting ultra-stable Istio setup for API Governance Platform"
    log_info "Using Istio ${ISTIO_VERSION} with Kubernetes ${K8S_VERSION}"
    
    # Check prerequisites
    check_prerequisites
    
    # Create Kind cluster
    create_kind_cluster
    
    # Install Istio
    install_istio_stable
    
    # Install basic addons
    install_basic_addons
    
    # Create sample app for testing
    create_sample_app
    
    # Create API governance namespace
    create_api_governance_namespace
    
    # Setup port forwarding
    setup_port_forwarding
    
    # Validate installation
    validate_installation
    
    log_success "Ultra-stable Istio setup completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Run './port-forward-istio.sh' to access dashboards"
    log_info "2. Test with: curl http://localhost:8000/get"
    log_info "3. Run 'docker-compose up' to start the API Governance Platform"
    log_info ""
    log_info "Dashboards will be available at:"
    log_info "- Kiali: http://localhost:20001"
    log_info "- Grafana: http://localhost:3000"
    log_info "- Prometheus: http://localhost:9090"
}

# Run main function
main "$@"