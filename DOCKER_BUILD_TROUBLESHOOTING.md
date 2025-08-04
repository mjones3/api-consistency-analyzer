# Docker Build Troubleshooting Guide

This guide helps resolve Docker build issues for the Spring Boot services.

## 🔧 Fixed Issues

### Maven Wrapper Missing (.mvn directory)
**Error**: `"/.mvn": not found`

**Solution**: Updated Dockerfiles to use multi-stage builds with Maven base image instead of Maven wrapper.

**New Dockerfile Structure**:
```dockerfile
# Build stage with Maven
FROM maven:3.9.4-openjdk-17-slim AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src src
RUN mvn clean package -DskipTests

# Runtime stage with JRE
FROM openjdk:17-jdk-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/target/*.jar app.jar
CMD ["java", "-jar", "app.jar"]
```

## 🚀 Building Images

### Option 1: Use Build Script (Recommended)
```bash
./scripts/build-services.sh
```

This script:
- Builds all three Docker images
- Loads them into Kind cluster automatically
- Provides detailed error reporting

### Option 2: Manual Build
```bash
# API Governance Platform
docker build -t api-governance:latest .

# Legacy Donor Service
docker build -t legacy-donor-service:latest ./examples/mock-services/legacy-donor-service/

# Modern Donor Service
docker build -t modern-donor-service:latest ./examples/mock-services/modern-donor-service/
```

### Option 3: Deploy Script (Automatic)
```bash
./scripts/deploy-kubernetes.sh
```

The deployment script automatically builds images if they don't exist.

## 🐛 Common Issues

### 1. Maven Dependencies Download Slow
**Issue**: Maven dependency download takes a long time

**Solution**: The multi-stage build caches dependencies in a separate layer:
```dockerfile
COPY pom.xml .
RUN mvn dependency:go-offline -B  # This layer is cached
COPY src src                      # Source changes don't invalidate dependency cache
```

### 2. Docker Build Context Too Large
**Issue**: Build context includes unnecessary files

**Solution**: Add `.dockerignore` files:
```
target/
*.log
.git/
.idea/
*.iml
```

### 3. Out of Memory During Build
**Issue**: Maven build runs out of memory

**Solution**: Increase Docker memory or add Maven options:
```dockerfile
RUN mvn clean package -DskipTests -Dmaven.compiler.fork=true
```

### 4. Kind Image Loading Fails
**Issue**: `kind load docker-image` fails

**Solution**: 
```bash
# Check if Kind cluster exists
kind get clusters

# Recreate cluster if needed
kind delete cluster --name api-governance
kind create cluster --name api-governance

# Load images
kind load docker-image api-governance:latest
```

## 🔍 Verification

### Check Built Images
```bash
docker images | grep -E "(api-governance|legacy-donor-service|modern-donor-service)"
```

### Test Images Locally
```bash
# Test Legacy Service
docker run -p 8081:8081 legacy-donor-service:latest

# Test Modern Service  
docker run -p 8082:8082 modern-donor-service:latest

# Test API Governance
docker run -p 8080:8080 api-governance:latest
```

### Verify in Kind Cluster
```bash
# Check if images are loaded in Kind
docker exec -it api-governance-control-plane crictl images | grep -E "(legacy-donor|modern-donor|api-governance)"
```

## 🛠️ Build Optimization

### Multi-Stage Build Benefits
1. **Smaller Runtime Images**: Only includes JRE and application JAR
2. **Cached Dependencies**: Maven dependencies cached in build layer
3. **Security**: No build tools in runtime image
4. **Faster Rebuilds**: Source changes don't invalidate dependency cache

### Build Performance Tips
1. **Use .dockerignore**: Exclude unnecessary files from build context
2. **Layer Caching**: Order Dockerfile commands from least to most frequently changing
3. **Parallel Builds**: Build multiple images simultaneously
4. **Registry Caching**: Use Docker registry for layer caching in CI/CD

## 🚨 Emergency Fixes

### If Build Still Fails
1. **Clean Docker**: `docker system prune -a`
2. **Restart Docker Desktop**: Restart Docker daemon
3. **Check Disk Space**: Ensure sufficient disk space
4. **Update Docker**: Use latest Docker version

### Alternative: Use Pre-built Images
If local builds continue to fail, you can use mock services:
```bash
# Skip Spring Boot services and use mock servers
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mock-legacy-service
  namespace: api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mock-legacy-service
  template:
    metadata:
      labels:
        app: mock-legacy-service
        service-type: spring-boot
      annotations:
        sidecar.istio.io/inject: "true"
    spec:
      containers:
      - name: mock-service
        image: mockserver/mockserver:latest
        ports:
        - containerPort: 1080
EOF
```

## 📞 Getting Help

If issues persist:
1. Check Docker logs: `docker logs <container-id>`
2. Verify Maven can build locally: `cd examples/mock-services/legacy-donor-service && mvn clean package`
3. Check Docker daemon status: `docker info`
4. Review build context: `docker build --no-cache -t test . 2>&1 | head -20`