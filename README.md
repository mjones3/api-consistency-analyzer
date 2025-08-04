# Microservices API Governance Platform

[![Build Status](https://github.com/your-org/microservices-api-governance/workflows/CI/badge.svg)](https://github.com/your-org/microservices-api-governance/actions)
[![Docker Image](https://img.shields.io/docker/v/your-org/api-governance?label=docker)](https://hub.docker.com/r/your-org/api-governance)
[![Helm Chart](https://img.shields.io/badge/helm-v1.0.0-blue)](https://github.com/your-org/microservices-api-governance/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive microservices API governance platform that automatically discovers Spring Boot services through Istio service mesh, harvests OpenAPI specifications, analyzes field naming inconsistencies, and provides FHIR-compliant standardization recommendations.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Istio Mesh    │    │  API Governance │    │   FHIR Mapper   │
│                 │───▶│    Platform     │───▶│                 │
│ Spring Services │    │                 │    │  Standardizer   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service       │    │  Consistency    │    │   Reports &     │
│   Discovery     │    │    Analyzer     │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (v1.28+) with Istio 1.19+ installed
- kubectl configured and cluster accessible
- Docker (for local development)
- curl (for testing endpoints)

### Kubernetes Deployment (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/your-org/microservices-api-governance.git
cd microservices-api-governance
```

2. **Set up local Istio environment**
```bash
./scripts/setup-istio-stable.sh
```

3. **Build and deploy everything to Kubernetes**
```bash
./scripts/build-services.sh
./scripts/deploy-kubernetes.sh
```

4. **Access services with enhanced monitoring**
```bash
./port-forward-k8s.sh
```

5. **Quick access to all dashboards**
```bash
./local_access_guide.sh
```

### Local Development (Alternative)

1. **Build Docker images**
```bash
./scripts/build-services.sh
```

2. **Run with Docker Compose**
```bash
docker-compose up -d
```

**If you encounter network conflicts:**
```bash
./scripts/fix-docker-networks.sh
docker-compose up -d
```

### Production Deployment

1. **Deploy with Helm**
```bash
helm install api-governance ./helm/api-governance \
  --namespace api-governance \
  --create-namespace \
  --values ./helm/api-governance/values-prod.yaml
```

2. **Verify deployment**
```bash
kubectl get pods -n api-governance
kubectl port-forward svc/api-governance 8080:80
```

## 📊 Features

- **🔍 Automatic Service Discovery**: Discovers Spring Boot services through Istio service mesh
- **📋 API Harvesting**: Collects OpenAPI specifications from discovered services
- **🔍 Consistency Analysis**: Identifies field naming inconsistencies across services
- **🏥 FHIR Compliance**: Provides healthcare-specific standardization recommendations
- **📈 Monitoring & Metrics**: Prometheus metrics and health endpoints
- **🚀 Production Ready**: Kubernetes deployment with Helm charts
- **🛠️ Local Development**: Complete local development stack with Docker Compose

## 📊 Monitoring & Observability

### Service Mesh Visualization with Kiali
Access the Kiali dashboard at http://localhost:20001/kiali/ to:
- **Service Graph**: Visualize service-to-service communication
- **Traffic Flow**: Monitor request rates, response times, and error rates
- **Configuration**: Validate Istio configuration (VirtualServices, DestinationRules)
- **Distributed Tracing**: View request traces across services
- **Security**: Monitor mTLS status and security policies

### Metrics & Dashboards with Grafana
Access Grafana at http://localhost:3000/ (admin/admin) for:
- **Istio Service Dashboard**: Service-level metrics and SLIs
- **Istio Mesh Dashboard**: Overall mesh health and performance
- **API Governance Metrics**: Custom dashboards for governance platform
- **Spring Boot Dashboards**: Application-specific metrics

### Raw Metrics with Prometheus
Access Prometheus at http://localhost:9090/ for:
- **Service Discovery**: Auto-discovered targets
- **Custom Queries**: PromQL queries for specific metrics
- **Alerting Rules**: Configure alerts for SLA violations
- **Federation**: Aggregate metrics from multiple clusters

### Key Metrics to Monitor
```promql
# API Governance Platform Metrics
api_governance_services_discovered_total
api_governance_harvest_duration_seconds
api_governance_fhir_compliance_score
api_governance_consistency_issues_total

# Istio Service Mesh Metrics
istio_requests_total
istio_request_duration_milliseconds
istio_tcp_connections_opened_total
istio_tcp_connections_closed_total

# Spring Boot Application Metrics
http_server_requests_seconds_count
jvm_memory_used_bytes
jvm_gc_pause_seconds
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEST_INTERVAL_HOURS` | `6` | Hours between harvest cycles |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent API requests |
| `KUBERNETES_NAMESPACES` | `default,api-governance` | Comma-separated list of namespaces to scan |
| `FHIR_COMPLIANCE_MODE` | `true` | Enable FHIR compliance checking |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |
| `ENVIRONMENT` | `kubernetes` | Environment mode (development, kubernetes, production) |

### ConfigMap Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-governance-config
data:
  config.yaml: |
    discovery:
      namespaces: ["default", "production", "staging"]
      labels:
        app: spring-boot
    harvester:
      concurrent_requests: 10
      timeout: 30
    fhir:
      compliance_mode: true
      mappings_file: /config/fhir-mappings.yaml
```

## 📚 API Reference & Endpoints

### 🚀 API Governance Platform Endpoints
| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/` | GET | Main FHIR Compliance Dashboard | http://localhost:8080/ |
| `/health/` | GET | Health check | http://localhost:8080/health/ |
| `/api/v1/discovered-services` | GET | List discovered services | http://localhost:8080/api/v1/discovered-services |
| `/api/v1/reports/latest` | GET | Latest consistency report | http://localhost:8080/api/v1/reports/latest |
| `/api/v1/fhir/recommendations` | GET | FHIR compliance recommendations | http://localhost:8080/api/v1/fhir/recommendations |
| `/api/v1/harvest/trigger` | POST | Trigger manual analysis | `curl -X POST http://localhost:8080/api/v1/harvest/trigger` |
| `/metrics` | GET | Prometheus metrics | http://localhost:8090/metrics |

### 🔗 API Services
| Service | Endpoint | Description | Example |
|---------|----------|-------------|---------|
| Legacy Donor Service | `/swagger-ui.html` | OpenAPI documentation | http://localhost:8081/swagger-ui.html |
| Legacy Donor Service | `/actuator/health` | Spring Boot health | http://localhost:8081/actuator/health |
| Modern Donor Service | `/swagger-ui.html` | OpenAPI documentation | http://localhost:8082/swagger-ui.html |
| Modern Donor Service | `/actuator/health` | Spring Boot health | http://localhost:8082/actuator/health |

### 🔍 Istio Service Mesh Monitoring
| Dashboard | URL | Description | Features |
|-----------|-----|-------------|----------|
| **Kiali** | http://localhost:20001/kiali/ | Service mesh topology | Service graph, traffic flow, configuration validation |
| **Grafana** | http://localhost:3000/ | Metrics dashboards | Performance metrics, service health, custom dashboards |
| **Prometheus** | http://localhost:9090/ | Metrics collection | Raw metrics, queries, alerting rules |
| **Istio Gateway** | http://localhost:15021/ | Gateway status | Ingress gateway health and configuration |

### 🔧 Useful Commands
```bash
# Check all pods across namespaces
kubectl get pods -A

# View API Governance logs
kubectl logs -f deployment/api-governance -n api-governance

# Check Istio configuration
kubectl get virtualservices,destinationrules -A

# Service mesh proxy status
istioctl proxy-status

# Trigger manual analysis
curl -X POST http://localhost:8080/api/v1/harvest/trigger \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Check service mesh traffic
kubectl exec -n istio-system deployment/kiali -- curl -s http://localhost:20001/kiali/api/namespaces/graph
```

## 🛠️ Scripts & Automation

### Build Scripts
```bash
# Build all Docker images and load into Kind cluster
./scripts/build-services.sh

# Build specific service
docker build -t api-governance:latest .
docker build -t legacy-donor-service:latest ./examples/mock-services/legacy-donor-service/
```

### Deployment Scripts
```bash
# Full Kubernetes deployment with Istio
./scripts/deploy-kubernetes.sh

# Port forwarding for local access
./port-forward-k8s.sh

# Enhanced local access guide
./local_access_guide.sh
```

### Monitoring Scripts
```bash
# Quick dashboard access
./dashboard-access.sh

# Check system status
kubectl get pods -A
kubectl get svc -A
istioctl proxy-status
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest --cov=src tests/

# Test API endpoints
curl -s http://localhost:8080/health/ | jq
curl -s http://localhost:8080/api/v1/discovered-services | jq
curl -s http://localhost:8080/api/v1/reports/latest | jq
```

## 🔍 Troubleshooting

### Common Issues

#### 1. API Governance Pod Not Starting
```bash
# Check pod status
kubectl get pods -n api-governance
kubectl describe pod -n api-governance -l app=api-governance

# Check logs
kubectl logs -f deployment/api-governance -n api-governance

# Common fixes
kubectl delete pod -n api-governance -l app=api-governance  # Restart pod
kubectl rollout restart deployment/api-governance -n api-governance
```

#### 2. Services Not Discovered
```bash
# Check if services are running
kubectl get pods -n api
kubectl get svc -n api

# Check Istio sidecar injection
kubectl get pods -n api -o jsonpath='{.items[*].spec.containers[*].name}'

# Verify service mesh configuration
istioctl proxy-config cluster -n api deployment/legacy-donor-service
```

#### 3. Port Forward Issues
```bash
# Kill existing port forwards
pkill -f "kubectl.*port-forward"

# Check if ports are in use
lsof -i :8080
lsof -i :20001

# Restart port forwarding
./port-forward-k8s.sh
```

#### 4. Istio Dashboard Not Accessible
```bash
# Check Istio installation
kubectl get pods -n istio-system
kubectl get svc -n istio-system

# Verify Kiali installation
kubectl get svc kiali -n istio-system
kubectl port-forward svc/kiali 20001:20001 -n istio-system

# Check Grafana
kubectl get svc grafana -n istio-system
kubectl port-forward svc/grafana 3000:3000 -n istio-system
```

#### 5. FHIR Compliance Analysis Not Working
```bash
# Check if services are accessible
kubectl exec -n api-governance deployment/api-governance -- \
  curl -s http://legacy-donor-service.api.svc.cluster.local:8081/actuator/health

# Trigger manual analysis
curl -X POST http://localhost:8080/api/v1/harvest/trigger \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Check analysis logs
kubectl logs -f deployment/api-governance -n api-governance | grep -i fhir
```

### Debug Commands
```bash
# Check all resources
kubectl get all -A

# Describe problematic resources
kubectl describe deployment api-governance -n api-governance
kubectl describe svc api-governance -n api-governance

# Check Istio configuration
kubectl get virtualservices,destinationrules,gateways -A
istioctl analyze -A

# Network connectivity test
kubectl run debug --image=curlimages/curl -it --rm -- sh
# Inside the pod: curl http://api-governance.api-governance.svc.cluster.local/health/
```

## 📖 Documentation

- [Deployment Guide](docs/DEPLOYMENT.md)
- [Configuration Reference](docs/CONFIGURATION.md)
- [API Reference](docs/API_REFERENCE.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Architecture Deep Dive](docs/ARCHITECTURE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🗺️ Roadmap

- [ ] GraphQL API support
- [ ] Advanced FHIR R5 compliance
- [ ] Machine learning-based inconsistency detection
- [ ] Integration with API gateways
- [ ] Real-time notifications
- [ ] Multi-cluster support

## 🆘 Support

- 📧 Email: support@your-org.com
- 💬 Slack: #api-governance
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/microservices-api-governance/issues)