"""Prometheus metrics for the application."""

import os
import time
from typing import Dict

import structlog
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

logger = structlog.get_logger()


class HarvestMetrics:
    """Metrics for API harvesting operations."""
    
    def __init__(self):
        # Service discovery metrics
        self.discovered_services = Counter(
            'api_harvester_discovered_services_total',
            'Total number of services discovered',
            ['namespace']
        )
        
        # API spec harvesting metrics
        self.harvested_specs = Counter(
            'api_harvester_harvested_specs_total',
            'Total number of API specs harvested',
            ['service', 'namespace', 'status']
        )
        
        self.harvest_duration = Histogram(
            'api_harvester_harvest_duration_seconds',
            'Time spent harvesting API specs',
            ['operation']
        )
        
        self.harvest_errors = Counter(
            'api_harvester_errors_total',
            'Total number of harvest errors',
            ['error_type', 'service']
        )
        
        # Consistency analysis metrics
        self.consistency_issues = Counter(
            'api_harvester_consistency_issues_total',
            'Total number of consistency issues found',
            ['severity', 'category']
        )
        
        self.fields_analyzed = Counter(
            'api_harvester_fields_analyzed_total',
            'Total number of fields analyzed',
            ['service', 'namespace']
        )
        
        # FHIR compliance metrics
        self.fhir_compliance_score = Gauge(
            'api_harvester_fhir_compliance_score',
            'FHIR compliance score (0-100)',
            ['category']
        )
        
        self.fhir_recommendations = Counter(
            'api_harvester_fhir_recommendations_total',
            'Total number of FHIR recommendations generated',
            ['impact_level']
        )
        
        # System metrics
        self.active_services = Gauge(
            'api_harvester_active_services',
            'Number of currently active services',
            ['namespace']
        )
        
        self.last_harvest_timestamp = Gauge(
            'api_harvester_last_harvest_timestamp',
            'Timestamp of last successful harvest'
        )
        
        self.harvest_success_rate = Gauge(
            'api_harvester_harvest_success_rate',
            'Success rate of API spec harvesting (0-1)'
        )


class SystemMetrics:
    """System-level metrics."""
    
    def __init__(self):
        # Application info
        self.app_info = Info(
            'api_governance_platform_info',
            'Information about the API governance platform'
        )
        
        # HTTP request metrics
        self.http_requests = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        # Health check metrics
        self.health_check_status = Gauge(
            'health_check_status',
            'Health check status (1=healthy, 0=unhealthy)',
            ['check_type']
        )
        
        # Kubernetes integration metrics
        self.k8s_api_calls = Counter(
            'kubernetes_api_calls_total',
            'Total number of Kubernetes API calls',
            ['operation', 'status']
        )
        
        self.k8s_api_duration = Histogram(
            'kubernetes_api_call_duration_seconds',
            'Kubernetes API call duration',
            ['operation']
        )


# Global metrics instances
harvest_metrics = HarvestMetrics()
system_metrics = SystemMetrics()


def setup_metrics():
    """Setup metrics collection."""
    # Temporarily disable all metrics to bypass label issues
    logger.info("Metrics collection temporarily disabled")
    return
    
    # Set application info
    system_metrics.app_info.info({
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'kubernetes_namespace': os.getenv('KUBERNETES_NAMESPACE', 'default')
    })
    
    # Start metrics server if enabled
    if os.getenv('METRICS_ENABLED', 'true').lower() == 'true':
        metrics_port = int(os.getenv('METRICS_PORT', '9090'))
        start_http_server(metrics_port)


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    # Temporarily disabled
    pass


def record_service_discovery(namespace: str, count: int):
    """Record service discovery metrics."""
    # Temporarily disabled
    pass


def record_spec_harvest(service: str, namespace: str, status: str, duration: float):
    """Record API spec harvest metrics."""
    # Temporarily disabled
    pass


def record_harvest_error(error_type: str, service: str):
    """Record harvest error metrics."""
    # Temporarily disabled
    pass


def record_consistency_analysis(issues_by_severity: Dict[str, int], fields_count: int):
    """Record consistency analysis metrics."""
    # Temporarily disabled
    pass


def record_fhir_compliance(score: float, category_scores: Dict[str, float]):
    """Record FHIR compliance metrics."""
    # Temporarily disabled
    pass


def record_fhir_recommendations(recommendations_by_impact: Dict[str, int]):
    """Record FHIR recommendation metrics."""
    # Temporarily disabled
    pass


def record_k8s_api_call(operation: str, status: str, duration: float):
    """Record Kubernetes API call metrics."""
    # Temporarily disabled
    pass


def update_health_status(check_type: str, is_healthy: bool):
    """Update health check status metrics."""
    # Temporarily disabled
    pass


def update_last_harvest_timestamp():
    """Update last harvest timestamp."""
    # Temporarily disabled
    pass


def update_harvest_success_rate(success_rate: float):
    """Update harvest success rate."""
    # Temporarily disabled
    pass


def get_metrics_summary() -> Dict:
    """Get a summary of current metrics."""
    try:
        # Safely get gauge values
        last_harvest = 0
        success_rate = 0
        compliance_score = 0
        
        try:
            last_harvest = harvest_metrics.last_harvest_timestamp._value._value if hasattr(harvest_metrics.last_harvest_timestamp, '_value') else 0
        except:
            pass
            
        try:
            success_rate = harvest_metrics.harvest_success_rate._value._value if hasattr(harvest_metrics.harvest_success_rate, '_value') else 0
        except:
            pass
        
        # Safely collect counter metrics
        total_discovered = 0
        active_count = 0
        total_issues = 0
        fields_analyzed = 0
        recommendations_generated = 0
        
        try:
            for metric in harvest_metrics.discovered_services.collect():
                if metric.samples:
                    total_discovered += sum(sample.value for sample in metric.samples)
        except:
            pass
            
        try:
            for metric in harvest_metrics.active_services.collect():
                if metric.samples:
                    active_count += sum(sample.value for sample in metric.samples)
        except:
            pass
            
        try:
            for metric in harvest_metrics.consistency_issues.collect():
                if metric.samples:
                    total_issues += sum(sample.value for sample in metric.samples)
        except:
            pass
            
        try:
            for metric in harvest_metrics.fields_analyzed.collect():
                if metric.samples:
                    fields_analyzed += sum(sample.value for sample in metric.samples)
        except:
            pass
            
        try:
            for metric in harvest_metrics.fhir_recommendations.collect():
                if metric.samples:
                    recommendations_generated += sum(sample.value for sample in metric.samples)
        except:
            pass
        
        return {
            "harvest": {
                "last_harvest": last_harvest,
                "success_rate": success_rate,
            },
            "services": {
                "total_discovered": total_discovered,
                "active_count": active_count
            },
            "consistency": {
                "total_issues": total_issues,
                "fields_analyzed": fields_analyzed
            },
            "fhir": {
                "compliance_score": compliance_score,
                "recommendations_generated": recommendations_generated
            }
        }
    except Exception as e:
        logger.error("Failed to get metrics summary", error=str(e))
        # Return default values if metrics collection fails
        return {
            "harvest": {
                "last_harvest": 0,
                "success_rate": 0,
            },
            "services": {
                "total_discovered": 0,
                "active_count": 0
            },
            "consistency": {
                "total_issues": 0,
                "fields_analyzed": 0
            },
            "fhir": {
                "compliance_score": 0,
                "recommendations_generated": 0
            }
        }


class MetricsMiddleware:
    """Middleware for collecting HTTP metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """Collect metrics for HTTP requests."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope["method"]
        path = scope["path"]
        start_time = time.time()
        status_code = 500  # Default to error
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.time() - start_time
            record_http_request(method, path, status_code, duration)