#!/bin/bash

# Setup local Istio environment with latest version (1.26.0)
# This script handles compatibility issues with newer Istio versions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ISTIO_VERSION="1.26.0"
CLUSTER_NAME="api-governance"
K8S_VERSION="v1.30.0"

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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check Kubernetes version
    K8S_SERVER_VERSION=$(kubectl version --short 2>/dev/null | grep "Server Version" | cut -d' ' -f3 | sed 's/v//' || echo "unknown")
    log_info "Kubernetes server version: ${K8S_SERVER_VERSION}"
    
    # Check if we have a compatible Kubernetes version
    if [[ "$K8S_SERVER_VERSION" < "1.28.0" ]]; then
        log_error "Kubernetes 1.28+ is required for Istio 1.26. Current version: ${K8S_SERVER_VERSION}"
        log_info "Consider using the stable setup script: ./scripts/setup-local-istio.sh"
        exit 1
    fi
    
    # Check if required APIs are available
    if ! kubectl api-resources | grep -q "horizontalpodautoscalers.*autoscaling/v2"; then
        log_warning "HPA v2 API not available, this may cause issues"
    fi
}

install_istio_minimal() {
    log_info "Installing Istio ${ISTIO_VERSION} with minimal profile..."
    
    # Download Istio
    if [ ! -d "istio-${ISTIO_VERSION}" ]; then
        log_info "Downloading Istio..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=${ISTIO_VERSION} sh -
    fi
    
    # Add istioctl to PATH
    export PATH=$PWD/istio-${ISTIO_VERSION}/bin:$PATH
    
    # Install with minimal profile first to avoid HPA issues
    log_info "Installing Istio control plane..."
    istioctl install --set values.pilot.autoscaleEnabled=false \
        --set values.pilot.env.EXTERNAL_ISTIOD=false \
        --set values.global.meshID=mesh1 \
        --set values.global.network=network1 \
        --skip-confirmation
    
    # Wait for istiod to be ready
    log_info "Waiting for Istio control plane..."
    kubectl wait --for=condition=available --timeout=300s deployment/istiod -n istio-system
    
    # Install ingress gateway separately
    log_info "Installing Istio ingress gateway..."
    kubectl apply -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: ingress-gateway
  namespace: istio-system
spec:
  components:
    ingressGateways:
    - name: istio-ingressgateway
      enabled: true
      k8s:
        service:
          type: NodePort
        hpaSpec:
          maxReplicas: 1
          minReplicas: 1
          scaleTargetRef:
            apiVersion: apps/v1
            kind: Deployment
            name: istio-ingressgateway
          targetCPUUtilizationPercentage: 80
EOF
    
    # Apply the operator configuration
    istioctl install -f - <<EOF
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: ingress-gateway
spec:
  components:
    ingressGateways:
    - name: istio-ingressgateway
      enabled: true
      k8s:
        service:
          type: NodePort
        hpaSpec:
          maxReplicas: 1
EOF
    
    # Enable Istio injection for default namespace
    kubectl label namespace default istio-injection=enabled --overwrite
    
    log_success "Istio installed successfully"
}

install_istio_addons_safe() {
    log_info "Installing Istio addons with compatibility fixes..."
    
    # Create a temporary directory for modified addon files
    mkdir -p /tmp/istio-addons
    
    # Copy and modify addon files to fix compatibility issues
    for addon in prometheus grafana kiali jaeger; do
        if [ -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" ]; then
            log_info "Preparing ${addon} addon..."
            
            # Remove problematic x-kubernetes-validations if present
            sed '/x-kubernetes-validations:/d' "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" > "/tmp/istio-addons/${addon}.yaml"
            
            # Apply the modified addon
            kubectl apply -f "/tmp/istio-addons/${addon}.yaml" || {
                log_warning "Failed to install ${addon}, trying alternative method..."
                # Try installing without validation
                kubectl apply -f "istio-${ISTIO_VERSION}/samples/addons/${addon}.yaml" --validate=false || {
                    log_warning "Could not install ${addon} addon"
                }
            }
        fi
    done
    
    # Wait for key addons to be ready
    log_info "Waiting for addon deployments..."
    
    for deployment in kiali prometheus grafana; do
        if kubectl get deployment ${deployment} -n istio-system &> /dev/null; then
            kubectl wait --for=condition=available --timeout=300s deployment/${deployment} -n istio-system || {
                log_warning "${deployment} deployment timeout, but continuing..."
            }
        fi
    done
    
    # Cleanup
    rm -rf /tmp/istio-addons
    
    log_success "Istio addons installation completed"
}

create_kind_cluster_latest() {
    log_info "Creating Kind cluster with latest Kubernetes..."
    
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
  - |
    kind: ClusterConfiguration
    apiServer:
      extraArgs:
        enable-admission-plugins: NodeRestriction,MutatingAdmissionWebhook,ValidatingAdmissionWebhook
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

validate_installation() {
    log_info "Validating Istio installation..."
    
    # Check Istio installation
    log_info "Verifying Istio installation..."
    istioctl verify-install || {
        log_warning "Istio verification had issues, checking manually..."
    }
    
    # Check core components
    log_info "Checking Istio components..."
    kubectl get pods -n istio-system
    
    # Check if istiod is ready
    if kubectl get deployment istiod -n istio-system &> /dev/null; then
        kubectl wait --for=condition=available --timeout=60s deployment/istiod -n istio-system || {
            log_warning "Istiod not fully ready, but may still be functional"
        }
    fi
    
    # Check proxy status
    log_info "Checking proxy status..."
    istioctl proxy-status || log_warning "Some proxies may not be ready yet"
    
    log_success "Installation validation completed"
}

main() {
    log_info "Starting Istio ${ISTIO_VERSION} setup for API Governance Platform"
    log_warning "This script uses the latest Istio version which may have compatibility issues"
    log_info "For a more stable setup, use: ./scripts/setup-local-istio.sh"
    
    # Check prerequisites
    check_prerequisites
    
    # Check if cluster exists
    if ! kubectl cluster-info &> /dev/null; then
        log_warning "No Kubernetes cluster found"
        
        if command -v kind &> /dev/null; then
            log_info "Creating Kind cluster with latest Kubernetes..."
            create_kind_cluster_latest
        else
            log_error "Please install Kind or start your Kubernetes cluster"
            exit 1
        fi
    fi
    
    # Install Istio
    install_istio_minimal
    
    # Install addons
    install_istio_addons_safe
    
    # Create API Governance namespace
    kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: api-governance
  labels:
    name: api-governance
    istio-injection: enabled
EOF
    
    # Validate installation
    validate_installation
    
    log_success "Istio ${ISTIO_VERSION} setup completed!"
    log_info "Note: Some features may not work perfectly due to version compatibility"
    log_info "For production use, consider using Istio 1.24.x with the stable setup script"
}

# Run main function
main "$@"