# Kubernetes Deployment Guide for API Governance Platform

This guide covers deploying the API Governance Platform and Arc One Blood Banking services to Kubernetes with Istio service mesh integration.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Istio Mesh    │  │  API Governance │  │ Blood Banking   │ │
│  │                 │  │    Platform     │  │    Services     │ │
│  │ - Service Mesh  │  │                 │  │                 │ │
│  │ - Traffic Mgmt  │  │ - Discovery     │  │ - Legacy Service│ │
│  │ - Security      │  │ - Analysis      │  │ - Modern Service│ │
│  │ - Observability │  │ - FHIR Mapping  │  │ - Spring Boot   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┐
```

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (Kind, Minikube, or cloud provider)
- Istio installed and configured
- kubectl configured to access your cluster
- Docker (for building images locally)

### 1. Setup Istio (if not already installed)
```bash
./scripts/setup-istio-stable.sh
```

### 2. Deploy Everything
```bash
./scripts/deploy-kubernetes.sh
```

### 3. Access Services
```bash
./port-forward-k8s.sh
```

### 4. View Analysis Results
```bash
./scripts/view-analysis-results.sh
```

## 📊 Deployed Components

### API Governance Platform (api-governance namespace)
- **Deployment**: API Governance Platform with Istio sidecar
- **Service**: ClusterIP service exposing HTTP and metrics ports
- **ConfigMap**: Configuration for namespace targeting and FHIR compliance
- **PVC**: Persistent storage for API specifications
- **RBAC**: ServiceAccount with cluster-wide read permissions
- **Istio**: VirtualService, DestinationRule, and Gateway configuration

### Blood Banking Services (blood-banking namespace)
- **Legacy Donor Service**: Non-FHIR compliant Spring Boot service
- **Modern Donor Service**: FHIR R4 compliant Spring Boot service
- **Istio Configuration**: VirtualServices, DestinationRules, PeerAuthentication
- **Service Mesh**: Automatic sidecar injection and traffic management

## 🔍 Service Discovery Process

The API Governance Platform automatically:

1. **Discovers Services**: Scans `blood-banking`, `api-governance`, and `default` namespaces
2. **Filters by Labels**: Looks for services with `service-type=spring-boot`
3. **Checks Istio Integration**: Verifies sidecar injection (`sidecar.istio.io/inject=true`)
4. **Health Validation**: Tests service health endpoints
5. **OpenAPI Discovery**: Finds and validates OpenAPI specifications
6. **Harvests Specifications**: Collects API specs for analysis
7. **Analyzes Consistency**: Identifies field naming and type inconsistencies
8. **FHIR Compliance**: Generates healthcare-specific recommendations

## 📈 Viewing Analysis Results

### 1. Web Dashboard
```bash
# Start port forwarding
./port-forward-k8s.sh

# Access dashboard
open http://localhost:8080/health/status
```

### 2. API Endpoints
```bash
# Discovered services
curl http://localhost:8080/api/v1/discovered-services | jq

# Latest consistency report
curl http://localhost:8080/api/v1/reports/latest | jq

# FHIR recommendations
curl http://localhost:8080/api/v1/fhir/recommendations | jq

# Compliance score
curl http://localhost:8080/api/v1/fhir/compliance-score | jq
```

### 3. Comprehensive Results Viewer
```bash
# View all results in terminal
./scripts/view-analysis-results.sh

# Trigger manual analysis
./scripts/view-analysis-results.sh --trigger
```

### 4. Service APIs
```bash
# Legacy Service Swagger UI
open http://localhost:8081/swagger-ui.html

# Modern Service Swagger UI
open http://localhost:8082/swagger-ui.html
```

## 🔧 Configuration

### Environment Variables (ConfigMap)
```yaml
KUBERNETES_NAMESPACES: "blood-banking,api-governance,default"
HARVEST_INTERVAL_HOURS: "2"
MAX_CONCURRENT_REQUESTS: "10"
FHIR_COMPLIANCE_MODE: "true"
SERVICE_LABEL_APP: "spring-boot"
HEALTH_CHECK_ENABLED: "true"
```

### Service Labels (Required for Discovery)
```yaml
labels:
  service-type: spring-boot  # Required for discovery
  domain: blood-banking      # Optional: domain classification
  compliance: fhir-r4        # Optional: compliance level
```

### Istio Annotations (Required)
```yaml
annotations:
  sidecar.istio.io/inject: "true"  # Required for Istio integration
```

## 📊 Expected Analysis Results

The platform will detect and report:

### Field Naming Inconsistencies (8 violations)
1. `donorId` (Legacy) → `identifier` (Modern)
2. `firstName` (Legacy) → `name.given` (Modern)
3. `lastName` (Legacy) → `name.family` (Modern)
4. `phoneNumber` (Legacy) → `telecom.value` (Modern)
5. `email` (Legacy) → `telecom.value` (Modern)
6. `zip` (Legacy) → `address.postalCode` (Modern)
7. `createdDate` (Legacy) → `meta.lastUpdated` (Modern)
8. `birthDate` structure differences

### Data Type Inconsistencies (3 violations)
1. **Postal Code**: `Integer zip` vs `String postalCode`
2. **Birth Date**: `String birthDate` vs `LocalDate birthDate`
3. **Timestamps**: `LocalDateTime` vs `Instant`

### FHIR Compliance Recommendations
- Standardize to FHIR R4 field naming
- Use proper FHIR data types
- Implement FHIR Bundle responses
- Adopt FHIR validation patterns

## 🔍 Monitoring and Observability

### Istio Dashboards
```bash
# Kiali (Service Mesh Visualization)
open http://localhost:20001

# Grafana (Metrics and Dashboards)
open http://localhost:3000

# Prometheus (Metrics Collection)
open http://localhost:9090
```

### Kubernetes Monitoring
```bash
# Check pod status
kubectl get pods -n blood-banking -n api-governance

# View logs
kubectl logs -f deployment/api-governance -n api-governance
kubectl logs -f deployment/legacy-donor-service -n blood-banking
kubectl logs -f deployment/modern-donor-service -n blood-banking

# Check Istio configuration
kubectl get virtualservices,destinationrules -n blood-banking
kubectl get gateways,peerauthentications -n blood-banking
```

### Platform Metrics
The API Governance Platform exposes Prometheus metrics:
- `api_harvester_discovered_services_total`
- `api_harvester_harvested_specs_total`
- `api_harvester_consistency_issues_total`
- `api_harvester_fhir_compliance_score`

## 🛠️ Troubleshooting

### Services Not Discovered
1. **Check Labels**: Ensure services have `service-type=spring-boot`
2. **Verify Istio**: Confirm sidecar injection is working
3. **Check Namespaces**: Verify services are in monitored namespaces
4. **Health Endpoints**: Ensure `/actuator/health` is accessible

```bash
# Debug service discovery
kubectl exec -n api-governance deployment/api-governance -- \
  curl -s http://legacy-donor-service.blood-banking.svc.cluster.local:8081/actuator/health
```

### Analysis Not Running
1. **Check Platform Health**: `curl http://localhost:8080/health/status`
2. **Trigger Manual Harvest**: `curl -X POST http://localhost:8080/api/v1/harvest/trigger`
3. **Check Logs**: `kubectl logs -f deployment/api-governance -n api-governance`

### Istio Issues
1. **Verify Installation**: `istioctl verify-install`
2. **Check Proxy Status**: `istioctl proxy-status`
3. **Validate Configuration**: `istioctl analyze -n blood-banking`

## 🔄 Continuous Operation

The API Governance Platform runs continuously and:

1. **Automatically discovers** new Spring Boot services
2. **Harvests API specifications** every 2 hours
3. **Analyzes consistency** across all discovered services
4. **Updates FHIR recommendations** based on latest analysis
5. **Maintains historical data** of API evolution
6. **Provides real-time metrics** via Prometheus

## 🚀 Scaling and Production

### Horizontal Scaling
```yaml
# Increase replicas
kubectl scale deployment api-governance --replicas=3 -n api-governance
```

### Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Production Considerations
1. **Persistent Storage**: Use appropriate StorageClass for your environment
2. **Resource Limits**: Adjust based on cluster size and service count
3. **Network Policies**: Implement proper network segmentation
4. **Security**: Enable mTLS and proper RBAC
5. **Monitoring**: Set up alerts for failed harvests and high inconsistency rates

## 📚 Additional Resources

- [Istio Documentation](https://istio.io/latest/docs/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [Spring Boot Actuator](https://docs.spring.io/spring-boot/docs/current/reference/html/actuator.html)
- [OpenAPI Specification](https://swagger.io/specification/)

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review platform logs: `kubectl logs -f deployment/api-governance -n api-governance`
3. Verify Istio configuration: `istioctl analyze`
4. Test service connectivity manually