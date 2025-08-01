#!/bin/bash

# View API Governance Analysis Results from Kubernetes Deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
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

log_section() {
    echo -e "${CYAN}[SECTION]${NC} $1"
}

log_highlight() {
    echo -e "${MAGENTA}[HIGHLIGHT]${NC} $1"
}

check_services() {
    log_info "Checking if services are accessible..."
    
    # Check if port forwarding is active
    if ! curl -s http://localhost:8080/health/ > /dev/null; then
        log_error "API Governance Platform is not accessible on localhost:8080"
        log_info "Please run: ./port-forward-k8s.sh"
        exit 1
    fi
    
    if ! curl -s http://localhost:8081/actuator/health > /dev/null; then
        log_warning "Legacy Donor Service is not accessible on localhost:8081"
    fi
    
    if ! curl -s http://localhost:8082/actuator/health > /dev/null; then
        log_warning "Modern Donor Service is not accessible on localhost:8082"
    fi
    
    log_success "API Governance Platform is accessible"
}

show_discovered_services() {
    log_section "=== DISCOVERED SERVICES ==="
    
    log_info "Fetching discovered services from API Governance Platform..."
    
    services=$(curl -s http://localhost:8080/api/v1/discovered-services)
    
    if [ $? -eq 0 ] && [ "$services" != "[]" ]; then
        echo ""
        log_success "Services discovered by the platform:"
        echo "$services" | jq -r '.[] | "• \(.name) (\(.namespace)) - \(.endpoints[0] // "no endpoint")"'
        
        echo ""
        log_info "Service details:"
        echo "$services" | jq -r '.[] | "
Service: \(.name)
  Namespace: \(.namespace)
  Istio Sidecar: \(.istio_sidecar)
  Health Endpoint: \(.health_endpoint // "none")
  OpenAPI Endpoint: \(.openapi_endpoint // "none")
  Labels: \(.labels | to_entries | map("\(.key)=\(.value)") | join(", "))
"'
    else
        log_warning "No services discovered yet. This could mean:"
        echo "  1. Services are still starting up"
        echo "  2. Services don't have the correct labels (service-type=spring-boot)"
        echo "  3. Istio sidecar injection is not working"
        echo "  4. The discovery process hasn't run yet"
    fi
}

show_consistency_report() {
    log_section "=== CONSISTENCY ANALYSIS REPORT ==="
    
    log_info "Fetching latest consistency report..."
    
    report=$(curl -s http://localhost:8080/api/v1/reports/latest)
    
    if [ $? -eq 0 ] && [ "$report" != "null" ]; then
        echo ""
        log_success "Latest Consistency Report:"
        
        # Show summary
        echo ""
        log_highlight "SUMMARY:"
        echo "$report" | jq -r '
        "Report ID: \(.report_id)",
        "Generated: \(.generated_at)",
        "Specs Analyzed: \(.specs_analyzed)",
        "Total Fields: \(.total_fields)",
        "Issues Found: \(.issues | length)"
        '
        
        # Show issue breakdown
        echo ""
        log_highlight "ISSUES BY SEVERITY:"
        echo "$report" | jq -r '.summary | to_entries | map("  \(.key | ascii_upcase): \(.value)") | .[]'
        
        # Show top issues
        echo ""
        log_highlight "TOP ISSUES FOUND:"
        echo "$report" | jq -r '.issues[0:5][] | "
🔍 \(.title) (\(.severity | ascii_upcase))
   Category: \(.category)
   Description: \(.description)
   Affected Services: \(.affected_fields | map(.service) | unique | join(", "))
   Recommendation: \(.recommendation)
"'
        
        # Show field naming issues specifically
        echo ""
        log_highlight "FIELD NAMING INCONSISTENCIES:"
        echo "$report" | jq -r '.issues[] | select(.category == "naming_inconsistency" or .category == "blood_banking") | "
📝 \(.title)
   Fields: \(.affected_fields | map(.name) | unique | join(" → "))
   Services: \(.affected_fields | map(.service) | unique | join(", "))
"'
        
    else
        log_warning "No consistency report available yet. This could mean:"
        echo "  1. Analysis is still in progress"
        echo "  2. No services have been discovered"
        echo "  3. OpenAPI specs couldn't be harvested"
        echo ""
        log_info "Try triggering a manual harvest:"
        echo "  curl -X POST http://localhost:8080/api/v1/harvest/trigger"
    fi
}

show_fhir_recommendations() {
    log_section "=== FHIR COMPLIANCE RECOMMENDATIONS ==="
    
    log_info "Fetching FHIR compliance recommendations..."
    
    recommendations=$(curl -s http://localhost:8080/api/v1/fhir/recommendations)
    
    if [ $? -eq 0 ] && [ "$recommendations" != "[]" ]; then
        echo ""
        log_success "FHIR Compliance Recommendations:"
        
        echo "$recommendations" | jq -r '.[] | "
🏥 Field: \(.field_name)
   Current Usage: \(.current_usage | join(", "))
   FHIR Recommendation: \(.recommended_name)
   FHIR Path: \(.fhir_path)
   Impact Level: \(.impact_level | ascii_upcase)
   Services Affected: \(.services_affected | join(", "))
   Implementation: \(.implementation_notes)
"'
        
        # Show compliance score
        echo ""
        log_highlight "FHIR COMPLIANCE SCORE:"
        compliance=$(curl -s http://localhost:8080/api/v1/fhir/compliance-score)
        if [ $? -eq 0 ]; then
            echo "$compliance" | jq -r '
            "Overall Score: \(.overall_score)%",
            "Total Fields: \(.total_fields)",
            "Compliant Fields: \(.compliant_fields)",
            "Recommendations: \(.recommendations_count)"
            '
            
            echo ""
            echo "Category Scores:"
            echo "$compliance" | jq -r '.category_scores | to_entries | map("  \(.key): \(.value)%") | .[]'
        fi
        
    else
        log_warning "No FHIR recommendations available yet"
    fi
}

show_harvest_status() {
    log_section "=== HARVEST STATUS ==="
    
    log_info "Fetching harvest status..."
    
    status=$(curl -s http://localhost:8080/api/v1/harvest/status)
    
    if [ $? -eq 0 ]; then
        echo ""
        log_success "Harvest Status:"
        echo "$status" | jq -r '
        "Status: \(.status)",
        "Services Discovered: \(.services_discovered)",
        "Specs Harvested: \(.specs_harvested)",
        "Success Rate: \(.success_rate * 100)%",
        "Last Harvest: \(.last_harvest // "never")"
        '
    else
        log_warning "Could not fetch harvest status"
    fi
}

show_platform_health() {
    log_section "=== PLATFORM HEALTH ==="
    
    log_info "Fetching platform health status..."
    
    health=$(curl -s http://localhost:8080/health/status)
    
    if [ $? -eq 0 ]; then
        echo ""
        log_success "Platform Health:"
        echo "$health" | jq -r '
        "Status: \(.status)",
        "Uptime: \(.uptime) seconds",
        "Environment: \(.configuration.namespaces | join(", "))"
        '
        
        echo ""
        log_highlight "COMPONENT STATUS:"
        echo "$health" | jq -r '.components | to_entries | map("  \(.key): \(.value.status)") | .[]'
        
        echo ""
        log_highlight "METRICS SUMMARY:"
        echo "$health" | jq -r '.metrics | to_entries | map("  \(.key): \(.value)") | .[]'
    else
        log_warning "Could not fetch platform health"
    fi
}

trigger_manual_analysis() {
    log_section "=== MANUAL ANALYSIS TRIGGER ==="
    
    log_info "Triggering manual analysis..."
    
    result=$(curl -s -X POST http://localhost:8080/api/v1/harvest/trigger \
        -H "Content-Type: application/json" \
        -d '{"force": true}')
    
    if [ $? -eq 0 ]; then
        echo ""
        log_success "Manual analysis triggered:"
        echo "$result" | jq -r '
        "Status: \(.status)",
        "Services Discovered: \(.services_discovered)",
        "Specs Harvested: \(.specs_harvested)",
        "Issues Found: \(.issues_found)",
        "Recommendations Generated: \(.recommendations_generated)"
        '
        
        echo ""
        log_info "Analysis is running... Wait a few minutes and run this script again to see results."
    else
        log_error "Failed to trigger manual analysis"
    fi
}

show_kubernetes_status() {
    log_section "=== KUBERNETES STATUS ==="
    
    log_info "Checking Kubernetes deployment status..."
    
    echo ""
    log_highlight "BLOOD BANKING SERVICES:"
    kubectl get pods -n blood-banking -o wide 2>/dev/null || log_warning "Cannot access blood-banking namespace"
    
    echo ""
    log_highlight "API GOVERNANCE PLATFORM:"
    kubectl get pods -n api-governance -o wide 2>/dev/null || log_warning "Cannot access api-governance namespace"
    
    echo ""
    log_highlight "ISTIO CONFIGURATION:"
    kubectl get virtualservices,destinationrules -n blood-banking 2>/dev/null || log_warning "Cannot access Istio resources"
}

show_service_endpoints() {
    log_section "=== SERVICE ENDPOINTS ==="
    
    echo ""
    log_highlight "API GOVERNANCE PLATFORM ENDPOINTS:"
    echo "  Health Dashboard: http://localhost:8080/health/status"
    echo "  Discovered Services: http://localhost:8080/api/v1/discovered-services"
    echo "  Latest Report: http://localhost:8080/api/v1/reports/latest"
    echo "  FHIR Recommendations: http://localhost:8080/api/v1/fhir/recommendations"
    echo "  Harvest Status: http://localhost:8080/api/v1/harvest/status"
    echo "  Trigger Analysis: curl -X POST http://localhost:8080/api/v1/harvest/trigger"
    
    echo ""
    log_highlight "BLOOD BANKING SERVICES:"
    echo "  Legacy Service API: http://localhost:8081/swagger-ui.html"
    echo "  Legacy OpenAPI Spec: http://localhost:8081/v3/api-docs"
    echo "  Modern Service API: http://localhost:8082/swagger-ui.html"
    echo "  Modern OpenAPI Spec: http://localhost:8082/v3/api-docs"
    
    echo ""
    log_highlight "ISTIO DASHBOARDS:"
    echo "  Kiali: http://localhost:20001"
    echo "  Grafana: http://localhost:3000"
    echo "  Prometheus: http://localhost:9090"
}

main() {
    echo "========================================"
    log_info "API GOVERNANCE ANALYSIS RESULTS VIEWER"
    echo "========================================"
    
    # Check if services are accessible
    check_services
    
    # Show all analysis results
    show_discovered_services
    show_consistency_report
    show_fhir_recommendations
    show_harvest_status
    show_platform_health
    
    # Show Kubernetes status
    show_kubernetes_status
    
    # Show available endpoints
    show_service_endpoints
    
    echo ""
    echo "========================================"
    log_success "ANALYSIS RESULTS REVIEW COMPLETED"
    echo "========================================"
    
    echo ""
    log_info "Available actions:"
    echo "1. Trigger manual analysis: ./scripts/view-analysis-results.sh --trigger"
    echo "2. View in browser: open http://localhost:8080/health/status"
    echo "3. Check service APIs: open http://localhost:8081/swagger-ui.html"
    echo "4. Monitor with Kiali: open http://localhost:20001"
}

# Handle command line arguments
if [ "$1" = "--trigger" ]; then
    trigger_manual_analysis
    exit 0
fi

# Run main function
main "$@"