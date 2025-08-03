"""Health check and monitoring endpoints."""

import os
import time
from datetime import datetime
from typing import Dict

import structlog
from fastapi import APIRouter, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.utils.metrics import get_metrics_summary

logger = structlog.get_logger()

# Global health status
_health_status = {
    "status": "healthy",
    "timestamp": datetime.utcnow(),
    "checks": {}
}


def create_health_router() -> APIRouter:
    """Create health check router."""
    router = APIRouter()
    
    @router.get("/")
    async def health_check():
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    
    @router.get("/ready")
    async def readiness_check():
        """Readiness probe for Kubernetes."""
        # Check if all components are ready
        checks = await _perform_readiness_checks()
        
        all_ready = all(check["status"] == "ready" for check in checks.values())
        
        if not all_ready:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    
    @router.get("/live")
    async def liveness_check():
        """Liveness probe for Kubernetes."""
        # Check if the service is alive
        checks = await _perform_liveness_checks()
        
        all_alive = all(check["status"] == "alive" for check in checks.values())
        
        if not all_alive:
            raise HTTPException(status_code=503, detail="Service not alive")
        
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    
    @router.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        try:
            metrics_data = generate_latest()
            return Response(
                content=metrics_data,
                media_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            logger.error("Failed to generate metrics", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to generate metrics")
    
    @router.get("/status")
    async def status_dashboard():
        """Detailed status dashboard."""
        try:
            # Get system information
            system_info = await _get_system_info()
            
            # Get component status
            component_status = await _get_component_status()
            
            # Get metrics summary
            metrics_summary = get_metrics_summary()
            
            return {
                "status": "operational",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": _get_uptime(),
                "system": system_info,
                "components": component_status,
                "metrics": metrics_summary,
                "configuration": _get_configuration_summary()
            }
        
        except Exception as e:
            logger.error("Failed to get status", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get status")
    
    return router


async def _perform_readiness_checks() -> Dict:
    """Perform readiness checks for all components."""
    checks = {}
    
    # Check Kubernetes connectivity
    checks["kubernetes"] = await _check_kubernetes_connectivity()
    
    # Check storage availability
    checks["storage"] = await _check_storage_availability()
    
    # Check configuration
    checks["configuration"] = await _check_configuration()
    
    return checks


async def _perform_liveness_checks() -> Dict:
    """Perform liveness checks."""
    checks = {}
    
    # Check basic application health
    checks["application"] = {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check memory usage
    checks["memory"] = await _check_memory_usage()
    
    return checks


async def _check_kubernetes_connectivity() -> Dict:
    """Check Kubernetes API connectivity."""
    try:
        from kubernetes import client, config
        
        # Try to load config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        # Try to make a simple API call
        v1 = client.CoreV1Api()
        v1.list_namespace(limit=1)
        
        return {
            "status": "ready",
            "message": "Kubernetes API accessible",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "not_ready",
            "message": f"Kubernetes API not accessible: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def _check_storage_availability() -> Dict:
    """Check storage availability."""
    try:
        storage_path = os.getenv("STORAGE_PATH", "/data/api-specs")
        
        # Check if storage path exists and is writable
        if not os.path.exists(storage_path):
            os.makedirs(storage_path, exist_ok=True)
        
        # Try to write a test file
        test_file = os.path.join(storage_path, ".health_check")
        with open(test_file, 'w') as f:
            f.write("health_check")
        
        # Clean up test file
        os.remove(test_file)
        
        return {
            "status": "ready",
            "message": "Storage accessible and writable",
            "path": storage_path,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "not_ready",
            "message": f"Storage not accessible: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def _check_configuration() -> Dict:
    """Check configuration validity."""
    try:
        required_env_vars = [
            "KUBERNETES_NAMESPACES",
            "HARVEST_INTERVAL_HOURS",
            "MAX_CONCURRENT_REQUESTS"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            return {
                "status": "not_ready",
                "message": f"Missing required environment variables: {', '.join(missing_vars)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "ready",
            "message": "Configuration valid",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "not_ready",
            "message": f"Configuration check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def _check_memory_usage() -> Dict:
    """Check memory usage."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Consider unhealthy if using more than 90% of available memory
        if memory.percent > 90:
            return {
                "status": "not_alive",
                "message": f"High memory usage: {memory.percent}%",
                "system_memory_percent": memory.percent,
                "process_memory_mb": process_memory.rss / 1024 / 1024,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "alive",
            "message": "Memory usage normal",
            "system_memory_percent": memory.percent,
            "process_memory_mb": process_memory.rss / 1024 / 1024,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except ImportError:
        # psutil not available, assume healthy
        return {
            "status": "alive",
            "message": "Memory monitoring not available",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "not_alive",
            "message": f"Memory check failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


async def _get_system_info() -> Dict:
    """Get system information."""
    try:
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
            "disk_usage": {
                "total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                "used_gb": round(psutil.disk_usage('/').used / 1024 / 1024 / 1024, 2),
                "free_gb": round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2)
            }
        }
    except ImportError:
        return {
            "platform": "unknown",
            "message": "System monitoring not available"
        }


async def _get_component_status() -> Dict:
    """Get status of all components."""
    return {
        "istio_discovery": {
            "status": "operational",
            "last_discovery": "2024-01-01T12:00:00Z"  # This would be dynamic
        },
        "api_harvester": {
            "status": "operational",
            "last_harvest": "2024-01-01T12:00:00Z"  # This would be dynamic
        },
        "consistency_analyzer": {
            "status": "operational",
            "last_analysis": "2024-01-01T12:00:00Z"  # This would be dynamic
        },
        "fhir_mapper": {
            "status": "operational",
            "mappings_loaded": 50  # This would be dynamic
        }
    }


def _get_uptime() -> float:
    """Get application uptime in seconds."""
    # This would track actual startup time
    return time.time() - _health_status["timestamp"].timestamp()


def _get_configuration_summary() -> Dict:
    """Get configuration summary."""
    return {
        "namespaces": os.getenv("KUBERNETES_NAMESPACES", "default").split(","),
        "harvest_interval_hours": int(os.getenv("HARVEST_INTERVAL_HOURS", "6")),
        "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
        "fhir_compliance_mode": os.getenv("FHIR_COMPLIANCE_MODE", "true").lower() == "true",
        "metrics_enabled": os.getenv("METRICS_ENABLED", "true").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }


# Import Response here to avoid circular imports
from fastapi import Response