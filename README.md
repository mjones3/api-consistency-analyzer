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
- Kubernetes cluster (v1.28+) with Istio 1.24+ installed
- kubectl configured
- Helm 3.x
- Docker (for local development)

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

3. **Deploy everything to Kubernetes**
```bash
./scripts/deploy-kubernetes.sh
```

4. **Access services**
```bash
./port-forward-k8s.sh
```

5. **View analysis results**
```bash
./scripts/view-analysis-results.sh
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

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEST_INTERVAL_HOURS` | `6` | Hours between harvest cycles |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent API requests |
| `KUBERNETES_NAMESPACES` | `default` | Comma-separated list of namespaces to scan |
| `FHIR_COMPLIANCE_MODE` | `true` | Enable FHIR compliance checking |
| `LOG_LEVEL` | `INFO` | Logging level |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics |

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

## 📚 API Reference

### Health Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

### Data Endpoints
- `GET /discovered-services` - List discovered services
- `GET /reports/latest` - Latest consistency report
- `GET /reports/{report_id}` - Specific report
- `POST /harvest/trigger` - Trigger manual harvest

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest --cov=src tests/
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