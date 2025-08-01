"""Istio service discovery module."""

import asyncio
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import aiohttp
import structlog
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


@dataclass
class ServiceInfo:
    """Information about a discovered service."""
    name: str
    namespace: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    endpoints: List[str]
    health_endpoint: Optional[str] = None
    openapi_endpoint: Optional[str] = None
    istio_sidecar: bool = False
    service_version: Optional[str] = None


@dataclass
class DiscoveryConfig:
    """Configuration for service discovery."""
    namespaces: List[str]
    label_selectors: Dict[str, str]
    annotation_filters: Dict[str, str]
    health_check_enabled: bool = True
    concurrent_requests: int = 10


class HealthChecker:
    """Health checker for discovered services."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def check_health(self, service_info: ServiceInfo) -> bool:
        """Check if service is healthy."""
        if not service_info.health_endpoint:
            return True  # Assume healthy if no health endpoint
        
        try:
            async with self.session.get(service_info.health_endpoint) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(
                "Health check failed",
                service=service_info.name,
                endpoint=service_info.health_endpoint,
                error=str(e)
            )
            return False
    
    async def discover_openapi_endpoint(self, service_info: ServiceInfo) -> Optional[str]:
        """Discover OpenAPI endpoint for a service."""
        common_paths = [
            "/v3/api-docs",
            "/api-docs",
            "/swagger.json",
            "/openapi.json",
            "/docs/openapi.json"
        ]
        
        for endpoint in service_info.endpoints:
            for path in common_paths:
                url = f"{endpoint.rstrip('/')}{path}"
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type:
                                return url
                except Exception:
                    continue
        
        return None


class IstioServiceDiscovery:
    """Discovers services in Istio service mesh."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.k8s_client = None
        self.istio_client = None
        self._load_config()
        self.discovery_config = self._create_discovery_config()
    
    def _load_config(self):
        """Load Kubernetes configuration."""
        try:
            if self.config_path:
                config.load_kube_config(config_file=self.config_path)
            else:
                # Try in-cluster config first, then local config
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()
            
            self.k8s_client = client.ApiClient()
            logger.info("Kubernetes configuration loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load Kubernetes configuration", error=str(e))
            raise
    
    def _create_discovery_config(self) -> DiscoveryConfig:
        """Create discovery configuration from environment variables."""
        namespaces = os.getenv("KUBERNETES_NAMESPACES", "default").split(",")
        namespaces = [ns.strip() for ns in namespaces]
        
        return DiscoveryConfig(
            namespaces=namespaces,
            label_selectors={
                "app": os.getenv("SERVICE_LABEL_APP", "spring-boot")
            },
            annotation_filters={
                "sidecar.istio.io/inject": "true"
            },
            health_check_enabled=os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        )
    
    async def discover_services(self) -> List[ServiceInfo]:
        """Discover all services in configured namespaces."""
        logger.info("Starting service discovery", namespaces=self.discovery_config.namespaces)
        
        all_services = []
        
        for namespace in self.discovery_config.namespaces:
            try:
                services = await self._discover_services_in_namespace(namespace)
                all_services.extend(services)
                logger.info(
                    "Discovered services in namespace",
                    namespace=namespace,
                    count=len(services)
                )
            except Exception as e:
                logger.error(
                    "Failed to discover services in namespace",
                    namespace=namespace,
                    error=str(e)
                )
        
        # Filter and enrich services
        filtered_services = await self._filter_and_enrich_services(all_services)
        
        logger.info("Service discovery completed", total_services=len(filtered_services))
        return filtered_services
    
    async def _discover_services_in_namespace(self, namespace: str) -> List[ServiceInfo]:
        """Discover services in a specific namespace."""
        v1 = client.CoreV1Api(self.k8s_client)
        services = []
        
        try:
            # Get services
            service_list = v1.list_namespaced_service(namespace=namespace)
            
            for service in service_list.items:
                # Check if service matches our criteria
                if not self._matches_criteria(service):
                    continue
                
                service_info = await self._create_service_info(service, namespace)
                if service_info:
                    services.append(service_info)
        
        except ApiException as e:
            logger.error(
                "Kubernetes API error",
                namespace=namespace,
                error=str(e)
            )
            raise
        
        return services
    
    def _matches_criteria(self, service) -> bool:
        """Check if service matches discovery criteria."""
        labels = service.metadata.labels or {}
        annotations = service.metadata.annotations or {}
        
        # Check label selectors
        for key, value in self.discovery_config.label_selectors.items():
            if labels.get(key) != value:
                return False
        
        # Check annotation filters (if any)
        for key, value in self.discovery_config.annotation_filters.items():
            if annotations.get(key) != value:
                continue  # Annotation filter is optional
        
        return True
    
    async def _create_service_info(self, service, namespace: str) -> Optional[ServiceInfo]:
        """Create ServiceInfo from Kubernetes service."""
        try:
            labels = service.metadata.labels or {}
            annotations = service.metadata.annotations or {}
            
            # Build endpoints
            endpoints = []
            if service.spec.ports:
                for port in service.spec.ports:
                    if port.port:
                        endpoint = f"http://{service.metadata.name}.{namespace}.svc.cluster.local:{port.port}"
                        endpoints.append(endpoint)
            
            # Check for Istio sidecar injection
            istio_sidecar = (
                annotations.get("sidecar.istio.io/inject") == "true" or
                labels.get("istio-injection") == "enabled"
            )
            
            # Determine health endpoint
            health_endpoint = None
            if endpoints and annotations.get("health.check.path"):
                health_endpoint = f"{endpoints[0]}{annotations['health.check.path']}"
            elif endpoints:
                health_endpoint = f"{endpoints[0]}/actuator/health"
            
            return ServiceInfo(
                name=service.metadata.name,
                namespace=namespace,
                labels=labels,
                annotations=annotations,
                endpoints=endpoints,
                health_endpoint=health_endpoint,
                istio_sidecar=istio_sidecar,
                service_version=labels.get("version", labels.get("app.version"))
            )
        
        except Exception as e:
            logger.error(
                "Failed to create service info",
                service=service.metadata.name,
                error=str(e)
            )
            return None
    
    async def _filter_and_enrich_services(self, services: List[ServiceInfo]) -> List[ServiceInfo]:
        """Filter services and enrich with additional information."""
        if not self.discovery_config.health_check_enabled:
            return services
        
        async with HealthChecker() as health_checker:
            # Create semaphore for concurrent requests
            semaphore = asyncio.Semaphore(self.discovery_config.concurrent_requests)
            
            async def check_and_enrich_service(service_info: ServiceInfo) -> Optional[ServiceInfo]:
                async with semaphore:
                    # Check health
                    is_healthy = await health_checker.check_health(service_info)
                    if not is_healthy:
                        logger.info("Skipping unhealthy service", service=service_info.name)
                        return None
                    
                    # Discover OpenAPI endpoint
                    openapi_endpoint = await health_checker.discover_openapi_endpoint(service_info)
                    service_info.openapi_endpoint = openapi_endpoint
                    
                    return service_info
            
            # Process services concurrently
            tasks = [check_and_enrich_service(service) for service in services]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            filtered_services = []
            for result in results:
                if isinstance(result, ServiceInfo):
                    filtered_services.append(result)
                elif isinstance(result, Exception):
                    logger.error("Service enrichment failed", error=str(result))
            
            return filtered_services
    
    async def get_istio_configuration(self, service_info: ServiceInfo) -> Dict:
        """Get Istio configuration for a service."""
        # This would integrate with Istio APIs to get VirtualService, DestinationRule, etc.
        # For now, return basic info
        return {
            "virtual_services": [],
            "destination_rules": [],
            "gateways": [],
            "authorization_policies": []
        }