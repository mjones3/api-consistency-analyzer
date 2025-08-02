#!/bin/bash
# Local Access Guide for Prometheus and Istio Dashboards
# This script helps you access monitoring and service mesh dashboards locally

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"; }

# Check if kubectl is configured
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "kubectl is not configured or cluster is not accessible"
        exit 1
    fi
    
    log "✅ kubectl is configured and cluster is accessible"
}

# Discover Prometheus installation
discover_prometheus() {
    log "🔍 Discovering Prometheus installation..."
    
    # Common namespaces where Prometheus might be installed
    PROMETHEUS_NAMESPACES=("monitoring" "prometheus" "istio-system" "kube-system" "default")
    PROMETHEUS_FOUND=false
    
    for namespace in "${PROMETHEUS_NAMESPACES[@]}"; do
        if kubectl get namespace "$namespace" &>/dev/null; then
            # Check for Prometheus service
            PROMETHEUS_SVC=$(kubectl get svc -n "$namespace" -l app=prometheus -o name 2>/dev/null | head -1)
            if [ ! -z "$PROMETHEUS_SVC" ]; then
                PROMETHEUS_NAMESPACE="$namespace"
                PROMETHEUS_SERVICE=$(echo "$PROMETHEUS_SVC" | cut -d'/' -f2)
                PROMETHEUS_FOUND=true
                log "✅ Found Prometheus service: $PROMETHEUS_SERVICE in namespace: $PROMETHEUS_NAMESPACE"
                break
            fi
            
            # Alternative: Check for prometheus-server (common in Helm charts)
            PROMETHEUS_SVC=$(kubectl get svc -n "$namespace" -l app.kubernetes.io/name=prometheus -o name 2>/dev/null | head -1)
            if [ ! -z "$PROMETHEUS_SVC" ]; then
                PROMETHEUS_NAMESPACE="$namespace"
                PROMETHEUS_SERVICE=$(echo "$PROMETHEUS_SVC" | cut -d'/' -f2)
                PROMETHEUS_FOUND=true
                log "✅ Found Prometheus service: $PROMETHEUS_SERVICE in namespace: $PROMETHEUS_NAMESPACE"
                break
            fi
        fi
    done
    
    if [ "$PROMETHEUS_FOUND" = false ]; then
        warn "❌ Prometheus service not found in common namespaces"
        warn "Try manually: kubectl get svc -A | grep prometheus"
        return 1
    fi
}

# Discover Istio installation
discover_istio() {
    log "🔍 Discovering Istio installation..."
    
    if ! kubectl get namespace istio-system &>/dev/null; then
        error "❌ istio-system namespace not found. Is Istio installed?"
        return 1
    fi
    
    log "✅ Found istio-system namespace"
    
    # Check for common Istio services
    ISTIO_SERVICES=()
    
    # Kiali (Service Mesh Dashboard)
    if kubectl get svc kiali -n istio-system &>/dev/null; then
        ISTIO_SERVICES+=("kiali:20001")
        log "✅ Found Kiali service"
    fi
    
    # Grafana (Metrics Dashboard)
    if kubectl get svc grafana -n istio-system &>/dev/null; then
        ISTIO_SERVICES+=("grafana:3000")
        log "✅ Found Grafana service"
    fi
    
    # Jaeger (Distributed Tracing)
    if kubectl get svc tracing -n istio-system &>/dev/null; then
        ISTIO_SERVICES+=("tracing:16686")
        log "✅ Found Jaeger tracing service"
    elif kubectl get svc jaeger-query -n istio-system &>/dev/null; then
        ISTIO_SERVICES+=("jaeger-query:16686")
        log "✅ Found Jaeger query service"
    fi
    
    # Prometheus (if installed with Istio)
    if kubectl get svc prometheus -n istio-system &>/dev/null; then
        ISTIO_SERVICES+=("prometheus:9090")
        log "✅ Found Istio Prometheus service"
        if [ "$PROMETHEUS_FOUND" = false ]; then
            PROMETHEUS_NAMESPACE="istio-system"
            PROMETHEUS_SERVICE="prometheus"
            PROMETHEUS_FOUND=true
        fi
    fi
    
    if [ ${#ISTIO_SERVICES[@]} -eq 0 ]; then
        warn "❌ No Istio dashboard services found"
        warn "Available services in istio-system:"
        kubectl get svc -n istio-system
        return 1
    fi
}

# Start port forwarding for Prometheus
start_prometheus_portforward() {
    if [ "$PROMETHEUS_FOUND" = true ]; then
        log "🚀 Starting Prometheus port forward..."
        
        # Kill existing port forward if running
        pkill -f "kubectl.*port-forward.*prometheus" 2>/dev/null || true
        
        # Start port forward in background
        kubectl port-forward -n "$PROMETHEUS_NAMESPACE" svc/"$PROMETHEUS_SERVICE" 9090:9090 &
        PROMETHEUS_PID=$!
        
        # Wait a moment for port forward to establish
        sleep 3
        
        # Test if port forward is working
        if curl -s http://localhost:9090/api/v1/label/__name__/values &>/dev/null; then
            log "✅ Prometheus accessible at: http://localhost:9090"
            info "   - Query interface: http://localhost:9090/graph"
            info "   - Targets: http://localhost:9090/targets"
            info "   - Configuration: http://localhost:9090/config"
        else
            warn "❌ Prometheus port forward may not be working"
        fi
    fi
}

# Start port forwarding for Istio services
start_istio_portforwards() {
    if [ ${#ISTIO_SERVICES[@]} -gt 0 ]; then
        log "🚀 Starting Istio dashboard port forwards..."
        
        for service_port in "${ISTIO_SERVICES[@]}"; do
            SERVICE=$(echo "$service_port" | cut -d':' -f1)
            PORT=$(echo "$service_port" | cut -d':' -f2)
            
            # Kill existing port forward if running
            pkill -f "kubectl.*port-forward.*$SERVICE" 2>/dev/null || true
            
            # Start port forward in background
            kubectl port-forward -n istio-system svc/"$SERVICE" "$PORT:$PORT" &
            
            # Store PID for cleanup
            eval "${SERVICE^^}_PID=$!"
            
            log "✅ Started port forward for $SERVICE on port $PORT"
        done
        
        # Wait for all port forwards to establish
        sleep 5
        
        # Display access URLs
        info ""
        info "🎯 Istio Dashboard URLs:"
        for service_port in "${ISTIO_SERVICES[@]}"; do
            SERVICE=$(echo "$service_port" | cut -d':' -f1)
            PORT=$(echo "$service_port" | cut -d':' -f2)
            
            case $SERVICE in
                "kiali")
                    info "   🔍 Kiali (Service Mesh): http://localhost:$PORT"
                    ;;
                "grafana")
                    info "   📊 Grafana (Metrics): http://localhost:$PORT"
                    ;;
                "tracing"|"jaeger-query")
                    info "   🔎 Jaeger (Tracing): http://localhost:$PORT"
                    ;;
                "prometheus")
                    info "   📈 Istio Prometheus: http://localhost:$PORT"
                    ;;
            esac
        done
    fi
}

# Show running port forwards
show_running_portforwards() {
    info ""
    info "🔧 Active Port Forwards:"
    ps aux | grep "kubectl.*port-forward" | grep -v grep | while read line; do
        info "   $line"
    done
}

# Create convenience script for easy access
create_convenience_script() {
    cat > dashboard-access.sh << 'EOF'
#!/bin/bash
# Convenience script to quickly access dashboards

echo "🎯 Opening dashboards in your default browser..."

# Function to open URL in browser
open_browser() {
    if command -v xdg-open &> /dev/null; then
        xdg-open "$1"  # Linux
    elif command -v open &> /dev/null; then
        open "$1"      # macOS
    elif command -v start &> /dev/null; then
        start "$1"     # Windows
    else
        echo "Please open manually: $1"
    fi
}

# Check if port forwards are running and open dashboards
if curl -s http://localhost:9090 &>/dev/null; then
    echo "📈 Opening Prometheus..."
    open_browser "http://localhost:9090"
fi

if curl -s http://localhost:20001 &>/dev/null; then
    echo "🔍 Opening Kiali..."
    open_browser "http://localhost:20001"
fi

if curl -s http://localhost:3000 &>/dev/null; then
    echo "📊 Opening Grafana..."
    open_browser "http://localhost:3000"
fi

if curl -s http://localhost:16686 &>/dev/null; then
    echo "🔎 Opening Jaeger..."
    open_browser "http://localhost:16686"
fi

echo "✅ All available dashboards opened!"
EOF

    chmod +x dashboard-access.sh
    log "✅ Created convenience script: dashboard-access.sh"
}

# Stop all port forwards
stop_portforwards() {
    log "🛑 Stopping all port forwards..."
    pkill -f "kubectl.*port-forward" 2>/dev/null || true
    log "✅ All port forwards stopped"
}

# Main menu
show_menu() {
    echo ""
    info "🎯 Prometheus & Istio Local Access Menu:"
    echo "1) Discover and start all dashboards"
    echo "2) Start Prometheus only" 
    echo "3) Start Istio dashboards only"
    echo "4) Show running port forwards"
    echo "5) Open dashboards in browser"
    echo "6) Stop all port forwards"
    echo "7) Create quick access script"
    echo "8) Exit"
    echo ""
    read -p "Enter your choice (1-8): " choice
}

# Cleanup function
cleanup() {
    if [ "$1" = "INT" ]; then
        echo ""
        log "Received interrupt signal..."
        stop_portforwards
        exit 0
    fi
}

# Set trap for cleanup
trap 'cleanup INT' INT

# Main execution
main() {
    log "🚀 Prometheus & Istio Local Access Tool"
    
    check_kubectl
    
    while true; do
        show_menu
        
        case $choice in
            1)
                discover_prometheus
                discover_istio
                start_prometheus_portforward
                start_istio_portforwards
                show_running_portforwards
                echo ""
                info "✨ All dashboards are now accessible locally!"
                info "💡 Use option 5 to open them in your browser"
                ;;
            2)
                discover_prometheus
                start_prometheus_portforward
                ;;
            3)
                discover_istio
                start_istio_portforwards
                ;;
            4)
                show_running_portforwards
                ;;
            5)
                ./dashboard-access.sh 2>/dev/null || echo "Run option 7 first to create the script"
                ;;
            6)
                stop_portforwards
                ;;
            7)
                create_convenience_script
                ;;
            8)
                stop_portforwards
                log "👋 Goodbye!"
                exit 0
                ;;
            *)
                warn "Invalid choice. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Quick start function for immediate access
quick_start() {
    log "🚀 Quick Start: Discovering and starting all dashboards..."
    check_kubectl
    discover_prometheus
    discover_istio  
    start_prometheus_portforward
    start_istio_portforwards
    create_convenience_script
    
    echo ""
    log "🎉 Setup complete! Here's what's available:"
    echo ""
    
    if [ "$PROMETHEUS_FOUND" = true ]; then
        info "📈 Prometheus: http://localhost:9090"
    fi
    
    for service_port in "${ISTIO_SERVICES[@]}"; do
        SERVICE=$(echo "$service_port" | cut -d':' -f1)
        PORT=$(echo "$service_port" | cut -d':' -f2)
        
        case $SERVICE in
            "kiali") info "🔍 Kiali: http://localhost:$PORT" ;;
            "grafana") info "📊 Grafana: http://localhost:$PORT" ;;
            "tracing"|"jaeger-query") info "🔎 Jaeger: http://localhost:$PORT" ;;
        esac
    done
    
    echo ""
    info "💡 Tips:"
    info "   • Run './dashboard-access.sh' to open all dashboards in browser"
    info "   • Press Ctrl+C to stop all port forwards"
    info "   • Port forwards will continue running in background"
}

# Command line argument handling
if [ "$1" = "quick" ]; then
    quick_start
else
    main
fi
