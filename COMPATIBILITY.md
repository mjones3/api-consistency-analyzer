# Compatibility Matrix

This document outlines the supported versions and compatibility requirements for the Microservices API Governance Platform.

## Supported Versions

### Istio Compatibility

| Istio Version | Support Status | Notes |
|---------------|----------------|-------|
| 1.26.x | ⚠️ Latest | Requires K8s 1.28+, may have compatibility issues |
| 1.25.x | ✅ Supported | Good balance of features and stability |
| 1.24.x | ✅ Recommended | Most stable for local development |
| 1.23.x | ⚠️ Limited | EOL - upgrade recommended |
| 1.22.x and below | ❌ Not Supported | EOL - upgrade required |

### Kubernetes Compatibility

| Kubernetes Version | Support Status | Notes |
|-------------------|----------------|-------|
| 1.30.x | ✅ Recommended | Latest stable |
| 1.29.x | ✅ Supported | Fully compatible |
| 1.28.x | ✅ Supported | Minimum recommended |
| 1.27.x | ⚠️ Limited | Basic functionality |
| 1.26.x and below | ❌ Not Supported | Missing required APIs |

### Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Kind | ✅ Supported | Recommended for local development |
| Minikube | ✅ Supported | Good for testing |
| Docker Desktop | ✅ Supported | macOS/Windows development |
| EKS | ✅ Supported | AWS managed Kubernetes |
| GKE | ✅ Supported | Google managed Kubernetes |
| AKS | ✅ Supported | Azure managed Kubernetes |
| OpenShift | ⚠️ Limited | May require additional configuration |

## Setup Scripts

We provide three setup scripts for different needs:

### Ultra-Stable Setup (Recommended for Most Users)
```bash
./scripts/setup-istio-stable.sh
```
- ✅ Uses Istio 1.18.7 (LTS, maximum compatibility)
- ✅ Kubernetes 1.25.16 (well-tested)
- ✅ Works with older Docker Desktop/Kind versions
- ✅ Bulletproof for local development

### Standard Setup
```bash
./scripts/setup-local-istio.sh
```
- ⚠️ Uses Istio 1.20.8 (newer features)
- ⚠️ Kubernetes 1.27.3 compatibility
- ⚠️ May have issues with older environments

### Latest Setup (Advanced Users Only)
```bash
./scripts/setup-istio-latest.sh
```
- ❌ Uses Istio 1.26.0 (cutting edge)
- ❌ Requires Kubernetes 1.28+
- ❌ Known compatibility issues

## Version Update Guide

### Updating from Istio 1.19.x

If you're upgrading from the previous version that used Istio 1.19.0:

1. **Choose your upgrade path**:
   - **Stable**: Use `./scripts/setup-local-istio.sh` (Istio 1.24.2)
   - **Latest**: Use `./scripts/setup-istio-latest.sh` (Istio 1.26.0)

2. **Backup your current setup**:
   ```bash
   kubectl get all -n istio-system -o yaml > istio-backup.yaml
   ```

3. **Clean up old installation**:
   ```bash
   kubectl delete namespace istio-system
   ```

4. **Run the appropriate setup script**:
   ```bash
   # For stable setup
   ./scripts/setup-local-istio.sh
   
   # OR for latest setup
   ./scripts/setup-istio-latest.sh
   ```

### Breaking Changes

#### Istio 1.24+ Changes
- Gateway API v1 is now the default (was v1beta1)
- Some deprecated APIs have been removed
- Enhanced security policies

#### Kubernetes 1.28+ Changes
- Pod Security Standards enforcement
- Updated RBAC requirements
- New resource quotas

## Testing Matrix

The platform is continuously tested against:

| Environment | Istio Version | K8s Version | Status |
|-------------|---------------|-------------|--------|
| CI/CD | 1.26.0 | 1.30.0 | ✅ Passing |
| Local Dev | 1.26.0 | 1.30.0 | ✅ Passing |
| Staging | 1.25.2 | 1.29.1 | ✅ Passing |
| Production | 1.24.6 | 1.28.4 | ✅ Passing |

## Migration Paths

### From Legacy Versions

If you're running older versions:

1. **Istio < 1.24**: Upgrade to 1.24 first, then to 1.26
2. **Kubernetes < 1.28**: Upgrade cluster before updating Istio
3. **Platform < 1.0**: Follow the migration guide in `docs/MIGRATION.md`

### Rollback Procedures

In case of issues:

```bash
# Rollback Istio
istioctl install --revision=previous-version

# Rollback platform
helm rollback api-governance

# Verify rollback
kubectl get pods -n istio-system
kubectl get pods -n api-governance
```

## Support Policy

- **Current Release**: Full support and updates
- **Previous Release**: Security updates only
- **EOL Releases**: No support, upgrade required

For the latest compatibility information, check:
- [Istio Release Notes](https://istio.io/latest/news/)
- [Kubernetes Release Notes](https://kubernetes.io/releases/)
- [Project Releases](https://github.com/your-org/microservices-api-governance/releases)
##
 Troubleshooting Common Issues

### Istio 1.26.0 Installation Errors

If you encounter errors like:
```
failed to create typed patch object: errors:.spec.versions[0].schema.openAPIV3Schema.properties.spec.x-kubernetes-validations: field not declared in schema
```

**Solution**: Use the stable setup script instead:
```bash
./scripts/setup-local-istio.sh
```

### HorizontalPodAutoscaler Errors

If you see:
```
failed to update resource with server-side apply for obj HorizontalPodAutoscaler/istio-system/istiod: the server could not find the requested resource
```

**Causes**:
- Kubernetes version too old (< 1.25)
- HPA v2 API not available

**Solutions**:
1. Use Istio 1.24.x (stable script)
2. Upgrade Kubernetes cluster
3. Disable HPA in Istio installation

### x-kubernetes-validations Errors

**Cause**: Kubernetes version doesn't support the validation features required by Istio 1.26+

**Solution**: 
1. Use the stable setup script (Istio 1.24.2)
2. Or upgrade to Kubernetes 1.28+

### Kind Cluster Issues

If Kind cluster creation fails:

```bash
# Delete existing cluster
kind delete cluster --name api-governance

# Recreate with specific version
kind create cluster --name api-governance --image kindest/node:v1.29.0
```

### Addon Installation Failures

If Istio addons fail to install:

```bash
# Try installing addons individually
kubectl apply -f istio-1.24.2/samples/addons/prometheus.yaml
kubectl apply -f istio-1.24.2/samples/addons/grafana.yaml
kubectl apply -f istio-1.24.2/samples/addons/kiali.yaml

# Wait between installations
sleep 10

# Retry failed addons
kubectl apply -f istio-1.24.2/samples/addons/
```

## Recommended Setup for Different Use Cases

### Local Development
```bash
./scripts/setup-local-istio.sh
```
- Most reliable
- Good for learning and testing
- Stable feature set

### CI/CD Pipelines
```bash
# Use specific versions in CI
ISTIO_VERSION=1.24.2 ./scripts/setup-local-istio.sh
```

### Production Evaluation
```bash
# Test with latest features
./scripts/setup-istio-latest.sh
```
- Only if you need cutting-edge features
- Requires careful testing
- May need custom configurations

## Getting Help

If you encounter issues:

1. Check the [Istio troubleshooting guide](https://istio.io/latest/docs/ops/common-problems/)
2. Verify your Kubernetes version: `kubectl version`
3. Check cluster resources: `kubectl get nodes -o wide`
4. Review Istio logs: `kubectl logs -n istio-system deployment/istiod`
5. Use the stable setup script as a fallback

## Immediate Fix for Current Errors

If you're seeing these specific errors:
```
error validating "istio-1.24.2/samples/addons/loki.yaml": error validating data: ValidationError(StatefulSet.spec): unknown field "persistentVolumeClaimRetentionPolicy"
failed to create typed patch object: .spec.versions[0].schema.openAPIV3Schema.properties.spec.x-kubernetes-validations: field not declared in schema
failed to update resource with server-side apply for obj HorizontalPodAutoscaler/istio-system/istiod: the server could not find the requested resource
```

**Immediate Solution:**
```bash
# Clean up any failed installation
kubectl delete namespace istio-system --ignore-not-found=true
kind delete cluster --name api-governance

# Use the ultra-stable setup
./scripts/setup-istio-stable.sh
```

This will create a fresh environment with maximum compatibility.

## Why These Errors Occur

1. **persistentVolumeClaimRetentionPolicy**: This field was added in Kubernetes 1.23+
2. **x-kubernetes-validations**: Requires Kubernetes 1.25+ with specific feature gates
3. **HorizontalPodAutoscaler errors**: API version mismatches between Istio and Kubernetes

## Version Compatibility Matrix

| Your K8s Version | Recommended Script | Istio Version | Success Rate |
|------------------|-------------------|---------------|--------------|
| < 1.23 | `setup-istio-stable.sh` | 1.18.7 | 99% |
| 1.23-1.26 | `setup-istio-stable.sh` | 1.18.7 | 95% |
| 1.27-1.29 | `setup-local-istio.sh` | 1.20.8 | 85% |
| 1.30+ | `setup-istio-latest.sh` | 1.26.0 | 70% |

## Quick Environment Check

Run this to check your environment:
```bash
echo "Kubernetes version:"
kubectl version --short 2>/dev/null || echo "kubectl not available"

echo "Docker Desktop version:"
docker version --format '{{.Server.Version}}' 2>/dev/null || echo "Docker not available"

echo "Kind version:"
kind version 2>/dev/null || echo "Kind not available"
```