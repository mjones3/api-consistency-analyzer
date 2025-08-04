# Microservices API Governance Platform

[![Build Status](https://github.com/your-org/microservices-api-governance/workflows/CI/badge.svg)](https://github.com/your-org/microservices-api-governance/actions)
[![Docker Image](https://img.shields.io/docker/v/your-org/api-governance?label=docker)](https://hub.docker.com/r/your-org/api-governance)
[![Helm Chart](https://img.shields.io/badge/helm-v1.0.0-blue)](https://github.com/your-org/microservices-api-governance/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive microservices API governance platform that automatically discovers Spring Boot services through Istio service mesh, harvests OpenAPI specifications, analyzes API compliance against customizable style guides, and provides standardization recommendations.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Istio Mesh    │    │  API Governance │    │ Style Guide     │
│                 │───▶│    Platform     │───▶│ Compliance      │
│ Spring Services │    │                 │    │ Analyzer        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Service       │    │  Consistency    │    │   Reports &     │
│   Discovery     │    │    Analyzer     │    │   Dashboard     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Features

### Service Discovery
- **Automatic Discovery**: Discovers Spring Boot services through Istio service mesh integration
- **Health Monitoring**: Continuous health checking of discovered services
- **Namespace Filtering**: Configurable namespace targeting for service discovery
- **Label-based Selection**: Service filtering based on Kubernetes labels

### API Specification Harvesting
- **OpenAPI Collection**: Automatically harvests OpenAPI 3.0 specifications from discovered services
- **Concurrent Processing**: Parallel harvesting with configurable concurrency limits
- **Persistent Storage**: Stores harvested specifications with versioning and timestamps
- **Error Handling**: Robust error handling with retry mechanisms

### Style Guide Compliance Analysis
- **Spectral Integration**: Uses Spectral for OpenAPI specification validation
- **Customizable Rules**: Configurable style guide rules via .spectral.yml
- **Naming Convention Validation**: Enforces camelCase, kebab-case, and other naming standards
- **Error Response Standards**: Validates required error response codes (400, 500, etc.)
- **Documentation Requirements**: Ensures proper API documentation standards

### Reporting and Dashboard
- **Real-time Dashboard**: Web-based dashboard showing compliance scores and recommendations
- **Detailed Reports**: Comprehensive compliance reports with line-by-line analysis
- **Export Functionality**: JSON export of compliance data and recommendations
- **Historical Tracking**: Tracks compliance improvements over time

## Quick Start

### Prerequisites
- Kubernetes cluster (v1.28+) with Istio 1.19+ installed
- kubectl configured and cluster accessible
- Docker (for local development)

### Kubernetes Deployment

1. **Clone and setup**
```bash
git clone https://github.com/your-org/microservices-api-governance.git
cd microservices-api-governance
./scripts/setup-istio-stable.sh
```

2. **Build and deploy**
```bash
./scripts/build-services.sh
./scripts/deploy-kubernetes.sh
```

3. **Access services**
```bash
./port-forward-k8s.sh
./local_access_guide.sh
```

## API Reference

### Core API Endpoints

#### Service Discovery

**GET /api/v1/discovered-services**
- **Description**: List all discovered services with their metadata
- **Parameters**: 
  - `namespace` (optional): Filter by namespace
- **Response Format**:
```json
[
  {
    "name": "legacy-donor-service",
    "namespace": "api",
    "labels": {
      "app": "legacy-donor-service",
      "version": "v1"
    },
    "endpoints": ["http://legacy-donor-service:8081"],
    "health_endpoint": "http://legacy-donor-service:8081/actuator/health",
    "openapi_endpoint": "http://legacy-donor-service:8081/v3/api-docs",
    "istio_sidecar": true,
    "service_version": "v1"
  }
]
```

**GET /api/v1/services/{service_name}**
- **Description**: Get detailed information about a specific service
- **Parameters**:
  - `service_name` (required): Name of the service
  - `namespace` (optional): Service namespace (default: "default")
- **Response Format**:
```json
{
  "service": {
    "name": "legacy-donor-service",
    "namespace": "api",
    "labels": {...},
    "endpoints": [...],
    "health_endpoint": "...",
    "openapi_endpoint": "...",
    "istio_sidecar": true,
    "service_version": "v1"
  },
  "istio_config": {
    "virtual_services": [...],
    "destination_rules": [...],
    "policies": [...]
  },
  "latest_spec": {
    "service_name": "legacy-donor-service",
    "namespace": "api",
    "spec_url": "http://legacy-donor-service:8081/v3/api-docs",
    "version": "v0",
    "harvested_at": "2025-08-04T02:46:10.521288Z",
    "is_valid": true,
    "validation_errors": []
  }
}
```

#### API Specifications

**GET /api/v1/specs**
- **Description**: List harvested API specifications
- **Parameters**:
  - `service_name` (optional): Filter by service name
  - `namespace` (optional): Filter by namespace
- **Response Format**:
```json
[
  {
    "service_name": "legacy-donor-service",
    "namespace": "api",
    "spec_url": "http://legacy-donor-service:8081/v3/api-docs",
    "version": "v0",
    "harvested_at": "2025-08-04T02:46:10.521288Z",
    "is_valid": true,
    "validation_errors": []
  }
]
```

#### Compliance Analysis

**GET /api/v1/compliance/overview**
- **Description**: Get service compliance overview table data
- **Response Format**:
```json
[
  {
    "service_name": "legacy-donor-service",
    "namespace": "api",
    "total_endpoints": 6,
    "inconsistent_naming_count": 8,
    "inconsistent_error_count": 12,
    "compliance_percentage": 25.5,
    "openapi_url": "http://legacy-donor-service:8081/v3/api-docs",
    "last_analyzed": "2025-08-04T02:46:10.521288Z"
  }
]
```

**GET /api/v1/compliance/naming/{service_name}**
- **Description**: Get detailed naming inconsistencies for a service
- **Parameters**:
  - `service_name` (required): Name of the service
  - `namespace` (optional): Service namespace (default: "api")
- **Response Format**:
```json
[
  {
    "field_name": "donorId",
    "current_naming": "donorId",
    "suggested_naming": "donorId",
    "endpoint": "/api/v1/donors/{donorId}",
    "severity": "error",
    "rule_violated": "arc-one-field-naming-camelcase",
    "description": "Field 'donorId' should use camelCase naming convention"
  }
]
```

**GET /api/v1/compliance/errors/{service_name}**
- **Description**: Get detailed error inconsistencies for a service
- **Parameters**:
  - `service_name` (required): Name of the service
  - `namespace` (optional): Service namespace (default: "api")
- **Response Format**:
```json
[
  {
    "endpoint": "/api/v1/donors",
    "method": "POST",
    "missing_responses": ["400", "500"],
    "severity": "warning",
    "rule_violated": "arc-one-error-response-400",
    "description": "Missing 400 Bad Request response"
  }
]
```

#### Style Guide Recommendations

**GET /api/v1/style-guide/recommendations**
- **Description**: Get API style guide compliance recommendations
- **Response Format**:
```json
[
  {
    "recommendation_id": "legacy-donor-service-donorId",
    "field_name": "donorId",
    "current_usage": ["donorId"],
    "recommended_name": "donorId",
    "rule_violated": "arc-one-field-naming-camelcase",
    "impact_level": "error",
    "services_affected": ["legacy-donor-service"],
    "implementation_notes": "Field 'donorId' should use camelCase naming convention"
  }
]
```

**GET /api/v1/style-guide/compliance-score**
- **Description**: Get overall API style guide compliance score
- **Response Format**:
```json
{
  "overall_score": 67.8,
  "total_fields": 45,
  "compliant_fields": 31,
  "non_compliant_fields": 14,
  "services_analyzed": 2,
  "timestamp": "2025-08-04T02:46:10.521288Z"
}
```

#### Reports

**GET /api/v1/reports/latest**
- **Description**: Get the latest consistency report
- **Response Format**:
```json
{
  "report_id": "report-2025-08-04-024610",
  "generated_at": "2025-08-04T02:46:10.521288Z",
  "specs_analyzed": 2,
  "total_fields": 45,
  "issues": [
    {
      "issue_id": "naming-001",
      "severity": "error",
      "category": "naming",
      "title": "Inconsistent field naming",
      "description": "Field 'donorId' uses inconsistent naming across services",
      "recommendation": "Standardize to camelCase: 'donorId'",
      "affected_services": ["legacy-donor-service"]
    }
  ],
  "summary": {
    "critical": 3,
    "major": 10,
    "minor": 2
  }
}
```

**GET /api/v1/reports/{report_id}**
- **Description**: Get a specific consistency report by ID
- **Parameters**:
  - `report_id` (required): Report identifier
- **Response Format**: Same as latest report

#### Harvest Operations

**POST /api/v1/harvest/trigger**
- **Description**: Trigger a manual harvest cycle
- **Request Body**:
```json
{
  "namespaces": ["api", "production"],
  "force": true
}
```
- **Response Format**:
```json
{
  "status": "completed",
  "services_discovered": 2,
  "specs_harvested": 2,
  "issues_found": 13,
  "recommendations_generated": 2,
  "timestamp": "2025-08-04T02:46:10.521288Z"
}
```

**GET /api/v1/harvest/status**
- **Description**: Get current harvest status
- **Response Format**:
```json
{
  "status": "operational",
  "services_discovered": 2,
  "specs_harvested": 2,
  "success_rate": 1.0,
  "last_harvest": "2025-08-04T02:46:10.521288Z"
}
```

#### System Information

**GET /api/v1/namespaces**
- **Description**: Get list of monitored namespaces
- **Response Format**:
```json
{
  "monitored_namespaces": ["api", "api-governance", "default"],
  "active_services": {
    "api": 2,
    "api-governance": 1,
    "default": 0
  },
  "last_discovery": "2025-08-04T02:46:10.521288Z"
}
```

### Health and Monitoring Endpoints

**GET /health/**
- **Description**: Basic health check endpoint
- **Response Format**:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-04T02:46:10.521288Z",
  "version": "1.0.0"
}
```

**GET /health/ready**
- **Description**: Readiness probe for Kubernetes
- **Response Format**:
```json
{
  "status": "ready",
  "checks": {
    "kubernetes": "connected",
    "database": "healthy",
    "dependencies": "available"
  },
  "timestamp": "2025-08-04T02:46:10.521288Z"
}
```

**GET /health/live**
- **Description**: Liveness probe for Kubernetes
- **Response Format**:
```json
{
  "status": "alive",
  "uptime": 3600,
  "memory_usage": "256MB",
  "timestamp": "2025-08-04T02:46:10.521288Z"
}
```

**GET /health/metrics**
- **Description**: Prometheus metrics endpoint
- **Response Format**: Prometheus text format
```
# HELP api_governance_services_discovered_total Total number of services discovered
# TYPE api_governance_services_discovered_total counter
api_governance_services_discovered_total{namespace="api"} 2

# HELP api_governance_harvest_duration_seconds Time spent harvesting API specs
# TYPE api_governance_harvest_duration_seconds histogram
api_governance_harvest_duration_seconds_bucket{le="0.1"} 0
api_governance_harvest_duration_seconds_bucket{le="0.5"} 1
api_governance_harvest_duration_seconds_bucket{le="1.0"} 2
```

### Web Interface Endpoints

**GET /**
- **Description**: Main API governance dashboard
- **Response**: HTML dashboard interface

**GET /recommendations/{service_name}**
- **Description**: Service-specific recommendations page
- **Parameters**:
  - `service_name` (required): Name of the service
- **Response**: HTML recommendations interface

**GET /compliance/naming/{service_name}/window**
- **Description**: Naming inconsistencies detail window
- **Parameters**:
  - `service_name` (required): Name of the service
- **Response**: HTML detail window

**GET /compliance/errors/{service_name}/window**
- **Description**: Error inconsistencies detail window
- **Parameters**:
  - `service_name` (required): Name of the service
- **Response**: HTML detail window

## Export Formats

### Comprehensive Compliance Export

**GET /api/v1/compliance/comprehensive-export**
- **Description**: Get comprehensive compliance data for all services with violation details
- **Response Format**:
```json
{
  "export_metadata": {
    "generated_at": "2025-08-04T02:46:10.521288Z",
    "export_type": "comprehensive_compliance",
    "version": "1.0.0",
    "services_included": 2
  },
  "services": [
    {
      "service_name": "legacy-donor-service",
      "namespace": "api",
      "compliance_overview": {
        "total_endpoints": 6,
        "compliance_percentage": 25.5,
        "last_analyzed": "2025-08-04T02:46:10.521288Z"
      },
      "naming_violations": [
        {
          "field_name": "donorId",
          "current_naming": "donorId",
          "suggested_naming": "donorId",
          "endpoint": "/api/v1/donors/{donorId}",
          "severity": "error",
          "rule_violated": "arc-one-field-naming-camelcase",
          "description": "Field 'donorId' should use camelCase naming convention"
        }
      ],
      "error_violations": [
        {
          "endpoint": "/api/v1/donors",
          "method": "POST",
          "missing_responses": ["400", "500"],
          "severity": "warning",
          "rule_violated": "arc-one-error-response-400",
          "description": "Missing 400 Bad Request response"
        }
      ]
    }
  ],
  "summary": {
    "total_services": 2,
    "average_compliance": 67.8,
    "total_violations": 15,
    "violations_by_severity": {
      "error": 3,
      "warning": 10,
      "info": 2
    }
  }
}
```

### Service Recommendations Export

When exporting from the recommendations page, the format is:
```json
{
  "service_name": "legacy-donor-service",
  "compliance_score": 25.5,
  "total_fields": 15,
  "compliant_fields": 4,
  "recommendations": [
    {
      "field_name": "donorId",
      "current_naming": "donorId",
      "suggested_naming": "donorId",
      "severity": "error",
      "description": "Field 'donorId' should use camelCase naming convention",
      "rule_violated": "arc-one-field-naming-camelcase"
    }
  ],
  "generated_at": "2025-08-04T02:46:10.521288Z"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEST_INTERVAL_HOURS` | `6` | Hours between automatic harvest cycles |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent API requests during harvesting |
| `KUBERNETES_NAMESPACES` | `api,api-governance,default` | Comma-separated list of namespaces to scan |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics collection |
| `HEALTH_CHECK_ENABLED` | `true` | Enable service health checking |
| `ENVIRONMENT` | `kubernetes` | Environment mode (development, kubernetes, production) |
| `SERVICE_LABEL_APP` | `spring-boot` | Label selector for service discovery |
| `STORAGE_PATH` | `/data/api-specs` | Path for storing harvested specifications |
| `RUN_MODE` | `continuous` | Run mode (continuous, single) |

### Spectral Configuration

The system uses `.spectral.yml` for defining API style guide rules:

```yaml
extends: ["@stoplight/spectral-openapi"]

rules:
  # Field naming conventions
  arc-one-field-naming-camelcase:
    description: "Field names should use camelCase convention"
    given: "$.paths[*][*].responses[*].content[*].schema..properties[*]~"
    severity: error
    then:
      function: pattern
      functionOptions:
        match: "^[a-z][a-zA-Z0-9]*$"

  # Path naming conventions
  arc-one-path-kebab-case:
    description: "Path segments should use kebab-case"
    given: "$.paths[*]~"
    severity: warn
    then:
      function: pattern
      functionOptions:
        match: "^(/[a-z0-9-]+(\{[a-zA-Z0-9]+\})?)*/?$"

  # Required error responses
  arc-one-error-response-400:
    description: "All endpoints should define 400 Bad Request response"
    given: "$.paths[*][*].responses"
    severity: warn
    then:
      function: schema
      functionOptions:
        schema:
          type: object
          required: ["400"]

  arc-one-error-response-500:
    description: "All endpoints should define 500 Internal Server Error response"
    given: "$.paths[*][*].responses"
    severity: warn
    then:
      function: schema
      functionOptions:
        schema:
          type: object
          required: ["500"]
```

## Deployment

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-governance-config
  namespace: api-governance
data:
  ENVIRONMENT: kubernetes
  HARVEST_INTERVAL_HOURS: "2"
  HEALTH_CHECK_ENABLED: "true"
  KUBERNETES_NAMESPACES: api,api-governance,default
  LOG_LEVEL: INFO
  MAX_CONCURRENT_REQUESTS: "10"
  METRICS_ENABLED: "true"
  RUN_MODE: continuous
  SERVICE_LABEL_APP: spring-boot
  STORAGE_PATH: /data/api-specs
```

### Service Labels

Services must be labeled for discovery:
```yaml
metadata:
  labels:
    app: spring-boot
    service-type: spring-boot
    domain: api
    compliance: style-guide
```

## Monitoring and Observability

### Key Metrics

The platform exposes the following Prometheus metrics:

- `api_governance_services_discovered_total`: Total services discovered by namespace
- `api_governance_harvest_duration_seconds`: Time spent harvesting API specifications
- `api_governance_compliance_score`: Current compliance score by service
- `api_governance_violations_total`: Total violations by severity and type
- `api_governance_harvest_success_rate`: Success rate of harvest operations

### Health Checks

The platform provides comprehensive health checking:
- **Liveness**: Basic application health
- **Readiness**: Dependency availability (Kubernetes API, storage)
- **Service Health**: Individual service health monitoring

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v

# Run locally
python -m src.main

# Build Docker image
docker build -t api-governance:latest .
```

### Testing API Endpoints

```bash
# Health check
curl -s http://localhost:8080/health/ | jq

# List services
curl -s http://localhost:8080/api/v1/discovered-services | jq

# Get compliance overview
curl -s http://localhost:8080/api/v1/compliance/overview | jq

# Trigger harvest
curl -X POST http://localhost:8080/api/v1/harvest/trigger \
  -H "Content-Type: application/json" \
  -d '{"force": true}' | jq

# Get recommendations
curl -s http://localhost:8080/api/v1/style-guide/recommendations | jq
```

## Troubleshooting

### Common Issues

1. **Services not discovered**: Check namespace configuration and service labels
2. **Harvest failures**: Verify service health and OpenAPI endpoint availability
3. **Compliance analysis errors**: Check Spectral configuration and rule syntax
4. **Dashboard not loading**: Verify port forwarding and service accessibility

### Debug Commands

```bash
# Check pod status
kubectl get pods -n api-governance
kubectl logs -f deployment/api-governance -n api-governance

# Verify service discovery
kubectl get services -n api
kubectl describe service legacy-donor-service -n api

# Test service connectivity
kubectl exec -n api-governance deployment/api-governance -- \
  curl -s http://legacy-donor-service.api.svc.cluster.local:8081/actuator/health
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.