#!/bin/bash

# Setup local Istio environment for API Governance Platform
# Supports Kind, Minikube, and Docker Desktop

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ISTIO_VERSION="1.20.8"  # LTS version with maximum compatibility
CLUSTER_NAME="api-governance"
K8S_VERSION="v1.27.3"   # Stable version with good Istio compatibility

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

detect_k8s_provider() {
    if kubectl config current-context | grep -q "kind"; then
        echo "kind"
    elif kubectl config current-context | grep -q "minikube"; then
        echo "minikube"
    elif kubectl config current-context | grep -q "docker-desktop"; then
        echo "docker-desktop"
    else
        echo "unknown"
    fi
}

check_k8s_compatibility() {
    log_info "Checking Kubernetes compatibility..."
    
    # Get Kubernetes version
    K8S_SERVER_VERSION=$(kubectl version --short | grep "Server Version" | cut -d' ' -f3 | sed 's/v//')
    log_info "Kubernetes server version: ${K8S_SERVER_VERSION}"
    
    # Check if HPA v2 is available
    if kubectl api-resources | grep -q "horizontalpodautoscalers.*autoscaling/v2"; then
        log_info "HPA v2 API is available"
        export HPA_API_VERSION="autoscaling/v2"
    else
        log_warning "HPA v2 not available, using v2beta2"
        export HPA_API_VERSION="autoscaling/v2beta2"
    fi
}

install_istio() {
    log_info "Installing Istio ${ISTIO_VERSION}..."
    
    # Check compatibility first
    check_k8s_compatibility
    
    # Download Istio
    if [ ! -d "istio-${ISTIO_VERSION}" ]; then
        log_info "Downloading Istio..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
    fi
    
    # Add istioctl to PATH
    export PATH=$PWD/istio-${ISTIO_VERSION}/bin:$PATH
    
    # Verify istioctl version
    log_info "Using istioctl version: $(istioctl version --client --short)"
    
    # Install Istio with demo profile - simplified for maximum compatibility
    log_info "Installing Istio with demo profile..."
    istioctl install --set values.defaultRevision=default \
        --set values.pilot.env.EXTERNAL_ISTIOD=false \
        --set values.gateways.istio-ingressgateway.type=NodePort \
        --set components.pilot.k8s.resources.requests.cpu=10m \
        --set components.pilot.k8s.resources.requests.memory=100Mi \
        --set components.ingressGateways[0].k8s.resources.requests.cpu=10m \
        --set components.ingressGateways[0].k8s.resources.requests.memory=40Mi \
        --skip-confirmation
    
    # Enable Istio injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    # Wait a moment for components to start
    sleep 15
    
    # Verify installation
    kubectl get pods -n istio-system
    
    log_success "Istio installed successfully"
}

install_istio_addons() {
    log_info "Installing Istio addons..."
    
    # Install core addons individually with validation disabled for compatibility
    local addons=("prometheus" "grafana" "kiali" "jaeger")
    
    for addon in "${addons[@]}"; do
        if [ -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" ]; then
            log_info "Installing ${addon}..."
            kubectl apply -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" --validate=false || {
                log_warning "Failed to install ${addon}, skipping..."
                continue
            }
            sleep 5
        else
            log_warning "${addon}.yaml not found, skipping..."
        fi
    done
    
    # Skip loki if it exists (causes issues with older K8s)
    if [ -f "istio-${ISTIO_VERSION}/samples/addons/loki.yaml" ]; then
        log_info "Skipping Loki (compatibility issues with older Kubernetes)"
    fi
    
    # Wait for core addons to be ready
    log_info "Waiting for addon deployments..."
    
    local core_addons=("prometheus" "grafana" "kiali")
    for addon in "${core_addons[@]}"; do
        if kubectl get deployment ${addon} -n istio-system &> /dev/null; then
            log_info "Waiting for ${addon}..."
            kubectl wait --for=condition=available --timeout=300s deployment/${addon} -n istio-system || {
                log_warning "${addon} deployment timeout, but continuing..."
            }
        else
            log_warning "${addon} deployment not found"
        fi
    done
    
    # Check addon status
    log_info "Addon deployment status:"
    kubectl get pods -n istio-system | grep -E "(kiali|prometheus|grafana)" || log_info "No addon pods found yet"
    
    log_success "Istio addons installation completed"
}

create_kind_cluster() {
    log_info "Creating Kind cluster..."
    
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
  - containerPort: 30000
    hostPort: 30000
    protocol: TCP
  - containerPort: 30001
    hostPort: 30001
    protocol: TCP
- role: worker
  image: kindest/node:${K8S_VERSION}
- role: worker
  image: kindest/node:${K8S_VERSION}
EOF
    
    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
    
    log_success "Kind cluster created and ready"
}

setup_port_forwarding() {
    log_info "Setting up port forwarding for Istio addons..."
    
    # Create port forwarding script
    cat > port-forward-istio.sh << 'EOF'
#!/bin/bash
echo "Starting port forwarding for Istio addons..."
echo "Kiali: http://localhost:20001"
echo "Grafana: http://localhost:3000"
echo "Prometheus: http://localhost:9090"
echo "Jaeger: http://localhost:16686"
echo ""
echo "Press Ctrl+C to stop all port forwards"

kubectl port-forward svc/kiali 20001:20001 -n istio-system &
kubectl port-forward svc/grafana 3000:3000 -n istio-system &
kubectl port-forward svc/prometheus 9090:9090 -n istio-system &
kubectl port-forward svc/tracing 16686:80 -n istio-system &

wait
EOF
    
    chmod +x port-forward-istio.sh
    log_success "Port forwarding script created: ./port-forward-istio.sh"
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

validate_installation() {
    log_info "Validating installation..."
    
    # Check Istio installation
    log_info "Verifying Istio installation..."
    if ! istioctl verify-install; then
        log_warning "Istio verification had warnings, but installation may still be functional"
    fi
    
    # Check if all pods are running
    log_info "Checking pod status in istio-system namespace..."
    kubectl get pods -n istio-system
    
    # Wait for core Istio components to be ready
    log_info "Waiting for core Istio components..."
    kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
    
    # Check Istio proxy status
    log_info "Checking Istio proxy status..."
    istioctl proxy-status || log_warning "Some proxies may not be ready yet"
    
    # Display useful information
    log_info "Istio installation summary:"
    echo "Istio version: $(istioctl version --short)"
    echo "Istio components:"
    kubectl get svc -n istio-system
    
    log_success "Installation validation completed"
}

cleanup_failed_installation() {
    log_warning "Cleaning up failed installation..."
    kubectl delete namespace istio-system --ignore-not-found=true
    sleep 5
}

main() {
    log_info "Starting local Istio setup for API Governance Platform"
    
    # Detect platform
    PLATFORM=$(detect_platform)
    log_info "Detected platform: ${PLATFORM}"
    
    # Check prerequisites
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if cluster exists
    if ! kubectl cluster-info &> /dev/null; then
        log_warning "No Kubernetes cluster found"
        
        if command -v kind &> /dev/null; then
            log_info "Creating Kind cluster..."
            create_kind_cluster
        else
            log_error "Please install Kind or start your Kubernetes cluster"
            exit 1
        fi
    fi
    
    # Detect K8s provider
    K8S_PROVIDER=$(detect_k8s_provider)
    log_info "Detected Kubernetes provider: ${K8S_PROVIDER}"
    
    # Check if Istio is already installed
    if kubectl get namespace istio-system &> /dev/null; then
        log_warning "Istio appears to be already installed"
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup_failed_installation
        else
            log_info "Skipping Istio installation"
            validate_installation
            exit 0
        fi
    fi
    
    # Install Istio with error handling
    if ! install_istio; then
        log_error "Istio installation failed"
        cleanup_failed_installation
        exit 1
    fi
    
    # Install Istio addons
    install_istio_addons
    
    # Create API Governance namespace
    create_api_governance_namespace
    
    # Setup port forwarding
    setup_port_forwarding
    
    # Validate installation
    validate_installation
    
    log_success "Local Istio setup completed successfully!"
    log_info "Next steps:"
    log_info "1. Run './port-forward-istio.sh' to access Istio dashboards"
    log_info "2. Run './scripts/deploy-mock-services.sh' to deploy test services"
    log_info "3. Run 'docker-compose up' to start the API Governance Platform"
}

# Run main function
main "$@"