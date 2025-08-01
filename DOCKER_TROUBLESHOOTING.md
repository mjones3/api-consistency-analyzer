# Docker Troubleshooting Guide

This guide helps resolve common Docker issues with the API Governance Platform.

## Network Overlap Error

### Error Message
```
failed to create network api-consistency-analyzer_api-governance: Error response from daemon: invalid pool request: Pool overlaps with other one on this address space
```

### Quick Fix
```bash
# Run the automated fix script
./scripts/fix-docker-networks.sh

# OR manual fix
docker-compose down
docker network prune -f
docker-compose up -d
```

### Manual Diagnosis

1. **Check existing networks:**
```bash
docker network ls
docker network inspect bridge
```

2. **Find conflicting subnets:**
```bash
docker network ls -q | xargs docker network inspect --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

3. **Remove conflicting networks:**
```bash
docker network rm api-consistency-analyzer_api-governance
docker network rm api-consistency-analyzer_default
```

### Alternative Subnets

If the default subnet `172.25.0.0/16` still conflicts, edit `docker-compose.yml`:

```yaml
networks:
  api-governance:
    driver: bridge
    ipam:
      config:
        - subnet: 172.26.0.0/16  # Try different subnets
```

Good alternatives:
- `172.26.0.0/16`
- `172.27.0.0/16`
- `192.168.100.0/24`
- `192.168.101.0/24`

## Port Conflicts

### Error Message
```
bind: address already in use
```

### Solution
```bash
# Check what's using the ports
lsof -i :8080
lsof -i :3000
lsof -i :9090

# Kill conflicting processes
sudo kill -9 <PID>

# OR change ports in docker-compose.yml
```

### Alternative Ports

Edit `docker-compose.yml` to use different ports:

```yaml
services:
  api-governance:
    ports:
      - "8081:8080"  # Change host port
      - "9091:9090"
  
  grafana:
    ports:
      - "3001:3000"  # Change host port
```

## Volume Permission Issues

### Error Message
```
permission denied
mkdir: cannot create directory '/data/api-specs': Permission denied
```

### Solution
```bash
# Fix volume permissions
docker-compose down
docker volume rm api-consistency-analyzer_api-specs-data
docker-compose up -d
```

## Build Issues

### Error Message
```
failed to solve: failed to read dockerfile
```

### Solution
```bash
# Ensure you're in the project root
pwd  # Should show the project directory

# Clean Docker build cache
docker system prune -f
docker-compose build --no-cache
```

## Memory Issues

### Error Message
```
container killed (OOMKilled)
```

### Solution

1. **Increase Docker Desktop memory:**
   - Docker Desktop → Settings → Resources → Memory
   - Increase to at least 4GB

2. **Reduce resource usage:**
```yaml
# In docker-compose.yml, add resource limits
services:
  api-governance:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Complete Reset

If all else fails, perform a complete reset:

```bash
# Stop everything
docker-compose down -v

# Remove all project resources
docker system prune -a -f
docker volume prune -f
docker network prune -f

# Remove project-specific resources
docker volume ls | grep api-consistency-analyzer | awk '{print $2}' | xargs -r docker volume rm
docker network ls | grep api-consistency-analyzer | awk '{print $2}' | xargs -r docker network rm

# Restart Docker Desktop (macOS/Windows)
# Then try again
docker-compose up -d
```

## Verification Commands

After fixing issues, verify everything works:

```bash
# Check containers are running
docker-compose ps

# Check logs
docker-compose logs api-governance

# Test endpoints
curl http://localhost:8080/health/
curl http://localhost:3000  # Grafana
curl http://localhost:9091  # Prometheus
```

## Getting Help

If issues persist:

1. **Check Docker Desktop status**
2. **Restart Docker Desktop**
3. **Check available disk space**
4. **Review Docker Desktop logs**
5. **Try the automated fix script:** `./scripts/fix-docker-networks.sh`

## Common Environment Issues

### macOS
- Ensure Docker Desktop has sufficient resources
- Check that Docker Desktop is running
- Verify file sharing permissions

### Windows
- Ensure WSL2 is properly configured
- Check Docker Desktop WSL2 integration
- Verify Windows firewall settings

### Linux
- Ensure Docker daemon is running: `sudo systemctl start docker`
- Check user permissions: `sudo usermod -aG docker $USER`
- Verify cgroup configuration