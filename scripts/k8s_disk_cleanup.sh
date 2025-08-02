#!/bin/bash
# Kubernetes Disk Space Cleanup - Emergency Edition
# Run these commands to quickly free up disk space

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"; }

# Check current disk usage
check_disk_usage() {
    log "🔍 Checking current disk usage across nodes..."
    
    echo "=== Node Disk Usage ==="
    kubectl top nodes || echo "Metrics server not available"
    
    echo ""
    echo "=== Detailed Node Storage ==="
    kubectl get nodes -o custom-columns="NAME:.metadata.name,DISK-PRESSURE:.status.conditions[?(@.type=='DiskPressure')].status"
    
    echo ""
    echo "=== PersistentVolume Usage ==="
    kubectl get pv -o custom-columns="NAME:.metadata.name,CAPACITY:.spec.capacity.storage,STATUS:.status.phase,CLAIM:.spec.claimRef.name"
}

# 1. QUICKEST WINS - Docker/Container Cleanup
docker_cleanup() {
    log "🧹 Step 1: Docker/Container Cleanup (FASTEST)"
    
    warn "This will remove unused Docker images, containers, and volumes"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Cleaning unused Docker images..."
        docker system prune -a -f || warn "Docker cleanup failed (might not be on Docker node)"
        
        log "Removing dangling volumes..."
        docker volume prune -f || warn "Docker volume cleanup failed"
        
        log "Cleaning build cache..."
        docker builder prune -a -f || warn "Docker builder cleanup failed"
        
        # If using kind/minikube locally
        if command -v kind &> /dev/null; then
            log "Cleaning kind clusters if any..."
            kind get clusters | xargs -I {} kind delete cluster --name {} || true
        fi
        
        if command -v minikube &> /dev/null; then
            log "Cleaning minikube cache..."
            minikube delete --all || true
            minikube cache delete || true
        fi
        
        log "✅ Docker cleanup complete"
    fi
}

# 2. Kubernetes Resource Cleanup
k8s_cleanup() {
    log "🗑️ Step 2: Kubernetes Resource Cleanup"
    
    warn "This will remove failed pods, completed jobs, and unused resources"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Removing failed pods..."
        kubectl get pods --all-namespaces --field-selector=status.phase=Failed -o json | \
            kubectl delete -f - 2>/dev/null || warn "No failed pods to remove"
        
        log "Removing succeeded pods..."
        kubectl get pods --all-namespaces --field-selector=status.phase=Succeeded -o json | \
            kubectl delete -f - 2>/dev/null || warn "No succeeded pods to remove"
        
        log "Cleaning completed jobs..."
        kubectl get jobs --all-namespaces -o json | \
            jq '.items[] | select(.status.conditions[]?.type == "Complete") | .metadata.name + " -n " + .metadata.namespace' -r | \
            xargs -I {} kubectl delete job {} 2>/dev/null || warn "No completed jobs to remove"
        
        log "Removing evicted pods..."
        kubectl get pods --all-namespaces --field-selector=status.phase=Failed | \
            grep Evicted | awk '{print $2 " -n " $1}' | \
            xargs -I {} kubectl delete pod {} 2>/dev/null || warn "No evicted pods to remove"
        
        log "✅ Kubernetes resource cleanup complete"
    fi
}

# 3. Log Cleanup
log_cleanup() {
    log "📝 Step 3: Log File Cleanup"
    
    warn "This will clean container logs and system logs"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Finding large log files..."
        
        # Clean container logs (if accessible)
        log "Cleaning container logs..."
        find /var/log/containers/ -name "*.log" -type f -size +100M -delete 2>/dev/null || warn "Cannot access container logs"
        find /var/log/pods/ -name "*.log" -type f -size +100M -delete 2>/dev/null || warn "Cannot access pod logs"
        
        # Clean journal logs
        log "Cleaning journal logs..."
        journalctl --vacuum-time=7d 2>/dev/null || warn "Cannot clean journal logs"
        journalctl --vacuum-size=1G 2>/dev/null || warn "Cannot vacuum journal logs"
        
        # Clean Docker logs
        log "Cleaning Docker logs..."
        find /var/lib/docker/containers/ -name "*-json.log" -type f -size +100M -delete 2>/dev/null || warn "Cannot access Docker logs"
        
        log "✅ Log cleanup complete"
    fi
}

# 4. Container Image Cleanup
image_cleanup() {
    log "🖼️ Step 4: Container Image Cleanup"
    
    warn "This will remove unused container images from nodes"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Getting all nodes..."
        NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
        
        for NODE in $NODES; do
            log "Cleaning images on node: $NODE"
            
            # Run cleanup on each node
            kubectl debug node/$NODE -it --image=alpine -- sh -c "
                # Mount node filesystem
                chroot /host /bin/bash -c '
                    # Clean unused Docker images
                    docker image prune -a -f 2>/dev/null || echo \"Docker not available\"
                    
                    # Clean containerd images (if using containerd)
                    crictl rmi --prune 2>/dev/null || echo \"crictl not available\"
                    
                    # Clean up /tmp
                    find /tmp -type f -atime +7 -delete 2>/dev/null || true
                    
                    # Clean apt cache (if Ubuntu/Debian)
                    apt-get clean 2>/dev/null || true
                    
                    # Clean yum cache (if RHEL/CentOS)
                    yum clean all 2>/dev/null || true
                '
            " --restart=Never --rm=true || warn "Failed to clean node $NODE"
        done
        
        log "✅ Image cleanup complete"
    fi
}

# 5. Advanced Cleanup - Use with Caution
advanced_cleanup() {
    log "⚠️ Step 5: Advanced Cleanup (USE WITH CAUTION)"
    
    error "This will remove more aggressive items and may affect running services"
    warn "Only run this if you understand the implications"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Removing old ReplicaSets..."
        kubectl get rs --all-namespaces -o json | \
            jq '.items[] | select(.spec.replicas == 0) | .metadata.name + " -n " + .metadata.namespace' -r | \
            xargs -I {} kubectl delete rs {} || warn "Failed to remove old ReplicaSets"
        
        log "Cleaning old ConfigMaps (unused)..."
        # This is tricky - only remove if you're sure they're unused
        warn "Skipping ConfigMap cleanup - requires manual verification"
        
        log "Removing old PVCs (if not bound)..."
        kubectl get pvc --all-namespaces --field-selector=status.phase=Pending -o json | \
            kubectl delete -f - 2>/dev/null || warn "No pending PVCs to remove"
        
        log "✅ Advanced cleanup complete"
    fi
}

# Quick emergency cleanup function
emergency_cleanup() {
    log "🚨 EMERGENCY CLEANUP - Running all safe operations"
    
    warn "This will run all safe cleanup operations without prompts"
    read -p "Emergency cleanup? This will remove unused images, containers, logs, and failed pods. Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Running emergency cleanup..."
        
        # Docker cleanup
        docker system prune -a -f 2>/dev/null || warn "Docker cleanup failed"
        docker volume prune -f 2>/dev/null || warn "Docker volume cleanup failed"
        
        # K8s resource cleanup
        kubectl delete pods --all-namespaces --field-selector=status.phase=Failed 2>/dev/null || true
        kubectl delete pods --all-namespaces --field-selector=status.phase=Succeeded 2>/dev/null || true
        
        # Clean logs
        find /var/log/containers/ -name "*.log" -type f -size +50M -delete 2>/dev/null || true
        journalctl --vacuum-time=3d 2>/dev/null || true
        
        log "✅ Emergency cleanup complete"
        check_disk_usage
    fi
}

# Show disk usage by namespace
namespace_usage() {
    log "📊 Analyzing disk usage by namespace..."
    
    echo "=== Pod Count by Namespace ==="
    kubectl get pods --all-namespaces --no-headers | awk '{print $1}' | sort | uniq -c | sort -nr
    
    echo ""
    echo "=== PVC Usage by Namespace ==="
    kubectl get pvc --all-namespaces -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,SIZE:.spec.resources.requests.storage,STATUS:.status.phase" | sort
    
    echo ""
    echo "=== Large Pods (by restart count - indicates potential issues) ==="
    kubectl get pods --all-namespaces -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount" | sort -k3 -nr | head -20
}

# Specific cleanup for build failures
build_failure_cleanup() {
    log "🔨 Build Failure Specific Cleanup"
    
    warn "This targets common build-related disk usage"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        log "Cleaning build caches..."
        
        # Clean Docker build cache
        docker builder prune -a -f 2>/dev/null || warn "Docker builder cleanup failed"
        
        # Clean npm cache (if building Node.js apps)
        find /tmp -name ".npm" -type d -exec rm -rf {} + 2>/dev/null || true
        find /root -name ".npm" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Clean Maven cache (if building Java apps)
        find /root -name ".m2" -type d -exec rm -rf {} + 2>/dev/null || true
        find /home -name ".m2" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Clean Gradle cache
        find /root -name ".gradle" -type d -exec rm -rf {} + 2>/dev/null || true
        find /home -name ".gradle" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Clean temporary build files
        find /tmp -name "docker-*" -type d -exec rm -rf {} + 2>/dev/null || true
        find /var/tmp -name "*build*" -type d -exec rm -rf {} + 2>/dev/null || true
        
        log "✅ Build cache cleanup complete"
    fi
}

# Main menu
show_menu() {
    echo ""
    info "🆘 Kubernetes Disk Space Emergency Cleanup"
    echo "Current disk usage:"
    df -h / 2>/dev/null || echo "Cannot check disk usage"
    echo ""
    echo "Choose cleanup option:"
    echo "1) 🚨 Emergency Cleanup (Run all safe operations)"
    echo "2) 🧹 Docker/Container Cleanup (Fastest)"
    echo "3) 🗑️ Kubernetes Resource Cleanup"
    echo "4) 📝 Log File Cleanup"
    echo "5) 🖼️ Container Image Cleanup"
    echo "6) 🔨 Build Failure Specific Cleanup"
    echo "7) 📊 Analyze Usage by Namespace"
    echo "8) ⚠️ Advanced Cleanup (Use with caution)"
    echo "9) 🔍 Check Current Disk Usage"
    echo "0) Exit"
    echo ""
    read -p "Enter your choice (0-9): " choice
}

# Main execution
main() {
    log "🚀 Kubernetes Disk Cleanup Tool"
    
    while true; do
        show_menu
        
        case $choice in
            1) emergency_cleanup ;;
            2) docker_cleanup ;;
            3) k8s_cleanup ;;
            4) log_cleanup ;;
            5) image_cleanup ;;
            6) build_failure_cleanup ;;
            7) namespace_usage ;;
            8) advanced_cleanup ;;
            9) check_disk_usage ;;
            0) log "👋 Goodbye!"; exit 0 ;;
            *) warn "Invalid choice. Please try again." ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Quick command-line options
case "${1:-}" in
    "emergency")
        emergency_cleanup
        ;;
    "docker")
        docker_cleanup
        ;;
    "build")
        build_failure_cleanup
        ;;
    "check")
        check_disk_usage
        ;;
    *)
        main
        ;;
esac
