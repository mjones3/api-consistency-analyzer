# Deployment Guide

This guide covers deploying the Microservices API Governance Platform in various environments.

## Prerequisites

- Kubernetes cluster (v1.28+ recommended) with Istio 1.24+ installed
- kubectl configured to access your cluster
- Helm 3.x installed
- Docker (for building custom images)

### Supported Versions

| Component | Minimum Version | Recommended Version |
|-----------|----------------|-------------------|
| Kubernetes | 1.26 | 1.30+ |
| Istio | 1.24 | 1.26+ |
| Helm | 3.8 | 3.14+ |
| Docker | 20.10 | 24.0+ |

## Quick Start

### 1. Local Development

```bash
# Setup local Istio environment
./scripts/setup-local-istio.sh

# Start the platform with Docker Compose
docker-compose up -d

# Access the platform
open http://localhost:8080/health/status
```

### 2. Production Deployment

```bash
# Create namespace
kubectl create namespace api-governance

# Deploy with Helm
helm install api-governance ./helm/api-governance \
  --namespace api-governance \
  --values ./helm/api-governance/values-prod.yaml
```

## Environment-Specific Deployments

### Development Environment

```bash
helm install api-governance ./helm/api-governance \
  --namespace api-governance \
  --values ./helm/api-governance/values-dev.yaml \
  --set image.tag=dev \
  --set replicaCount=1
```

### Staging Environment

```bash
helm install api-governance ./helm/api-governance \
  --namespace api-governance \
  --values ./helm/api-governance/values-staging.yaml \
  --set image.tag=staging \
  --set replicaCount=2
```

### Production Environment

```bash
helm install api-governance ./helm/api-governance \
  --namespace api-governance \
  --values ./helm/api-governance/values-prod.yaml \
  --set image.tag=latest \
  --set replicaCount=3
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HARVEST_INTERVAL_HOURS` | `6` | Hours between harvest cycles |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent API requests |
| `KUBERNETES_NAMESPACES` | `default` | Comma-separated list of namespaces |
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
```

## Monitoring and Observability

### Prometheus Metrics

The platform exposes metrics on `/health/metrics`:

- `api_harvester_discovered_services_total`
- `api_harvester_harvested_specs_total`
- `api_harvester_consistency_issues_total`
- `api_harvester_fhir_compliance_score`

### Health Checks

- `/health/` - Basic health check
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe
- `/health/status` - Detailed status dashboard

### Logging

Structured JSON logging is enabled by default in production. Logs include:

- Request correlation IDs
- Performance timing
- Error tracking
- Audit trails

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-governance-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-governance
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Vertical Pod Autoscaler

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-governance-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-governance
  updatePolicy:
    updateMode: "Auto"
```

## Security

### RBAC Configuration

The platform requires minimal RBAC permissions:

```yaml
rules:
- apiGroups: [""]
  resources: ["services", "namespaces", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networking.istio.io"]
  resources: ["virtualservices", "destinationrules", "gateways"]
  verbs: ["get", "list", "watch"]
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-governance-netpol
spec:
  podSelector:
    matchLabels:
      app: api-governance
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 6443
```

## Troubleshooting

### Common Issues

1. **Service Discovery Fails**
   ```bash
   kubectl logs -l app=api-governance -n api-governance
   kubectl describe pod -l app=api-governance -n api-governance
   ```

2. **RBAC Permissions**
   ```bash
   kubectl auth can-i get services --as=system:serviceaccount:api-governance:api-governance
   ```

3. **Istio Integration**
   ```bash
   istioctl proxy-config cluster -n api-governance api-governance-pod-name
   ```

### Debug Mode

Enable debug logging:

```bash
helm upgrade api-governance ./helm/api-governance \
  --set env.LOG_LEVEL=DEBUG \
  --reuse-values
```

## Backup and Recovery

### Configuration Backup

```bash
kubectl get configmap api-governance-config -o yaml > backup-config.yaml
kubectl get secret api-governance-secrets -o yaml > backup-secrets.yaml
```

### Data Backup

```bash
kubectl exec -it api-governance-pod -- tar czf - /data/api-specs > backup-data.tar.gz
```

## Upgrading

### Rolling Update

```bash
helm upgrade api-governance ./helm/api-governance \
  --set image.tag=new-version \
  --reuse-values
```

### Blue-Green Deployment

```bash
# Deploy new version
helm install api-governance-green ./helm/api-governance \
  --set nameOverride=api-governance-green \
  --set image.tag=new-version

# Switch traffic
kubectl patch service api-governance -p '{"spec":{"selector":{"version":"green"}}}'

# Cleanup old version
helm uninstall api-governance-blue
```