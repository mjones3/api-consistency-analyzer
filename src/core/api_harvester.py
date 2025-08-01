"""API specification harvester module."""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import structlog
from asyncio_throttle import Throttler
from openapi_spec_validator import validate_spec
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.istio_discovery import ServiceInfo
from src.utils.metrics import harvest_metrics

logger = structlog.get_logger()


@dataclass
class APISpec:
    """Represents an API specification."""
    service_name: str
    namespace: str
    spec_url: str
    spec_content: Dict
    version: Optional[str] = None
    harvested_at: datetime = field(default_factory=datetime.utcnow)
    validation_errors: List[str] = field(default_factory=list)
    is_valid: bool = True


@dataclass
class HarvestJob:
    """Represents a harvest job."""
    job_id: str
    services: List[ServiceInfo]
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    specs_harvested: int = 0
    errors: List[str] = field(default_factory=list)


class SpecStorage:
    """Handles storage of API specifications."""
    
    def __init__(self, storage_path: str = "/data/api-specs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_spec(self, spec: APISpec) -> str:
        """Save API spec to storage."""
        filename = f"{spec.service_name}_{spec.namespace}_{spec.harvested_at.isoformat()}.json"
        filepath = self.storage_path / filename
        
        spec_data = {
            "service_name": spec.service_name,
            "namespace": spec.namespace,
            "spec_url": spec.spec_url,
            "version": spec.version,
            "harvested_at": spec.harvested_at.isoformat(),
            "validation_errors": spec.validation_errors,
            "is_valid": spec.is_valid,
            "spec_content": spec.spec_content
        }
        
        with open(filepath, 'w') as f:
            json.dump(spec_data, f, indent=2)
        
        logger.info("Saved API spec", service=spec.service_name, file=str(filepath))
        return str(filepath)
    
    async def load_spec(self, filepath: str) -> APISpec:
        """Load API spec from storage."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return APISpec(
            service_name=data["service_name"],
            namespace=data["namespace"],
            spec_url=data["spec_url"],
            spec_content=data["spec_content"],
            version=data.get("version"),
            harvested_at=datetime.fromisoformat(data["harvested_at"]),
            validation_errors=data.get("validation_errors", []),
            is_valid=data.get("is_valid", True)
        )
    
    async def list_specs(self, service_name: Optional[str] = None) -> List[str]:
        """List stored API specs."""
        pattern = f"{service_name}_*" if service_name else "*"
        return [str(p) for p in self.storage_path.glob(f"{pattern}.json")]
    
    async def get_latest_spec(self, service_name: str, namespace: str) -> Optional[APISpec]:
        """Get the latest spec for a service."""
        specs = await self.list_specs(service_name)
        if not specs:
            return None
        
        # Sort by modification time and get the latest
        latest_file = max(specs, key=lambda x: os.path.getmtime(x))
        return await self.load_spec(latest_file)


class HarvestMetrics:
    """Tracks harvest metrics."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.services_discovered = 0
        self.specs_attempted = 0
        self.specs_successful = 0
        self.specs_failed = 0
        self.validation_errors = 0
        self.total_duration = 0
    
    def record_service_discovered(self):
        """Record a discovered service."""
        self.services_discovered += 1
        harvest_metrics.discovered_services.inc()
    
    def record_spec_attempt(self):
        """Record a spec harvest attempt."""
        self.specs_attempted += 1
    
    def record_spec_success(self):
        """Record a successful spec harvest."""
        self.specs_successful += 1
        harvest_metrics.harvested_specs.inc()
    
    def record_spec_failure(self):
        """Record a failed spec harvest."""
        self.specs_failed += 1
    
    def record_validation_error(self):
        """Record a validation error."""
        self.validation_errors += 1
    
    def record_duration(self, duration: float):
        """Record harvest duration."""
        self.total_duration = duration
        harvest_metrics.harvest_duration.observe(duration)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.specs_attempted == 0:
            return 0.0
        return self.specs_successful / self.specs_attempted


class APIHarvester:
    """Harvests API specifications from discovered services."""
    
    def __init__(self, discovery_service, storage_path: str = "/data/api-specs"):
        self.discovery_service = discovery_service
        self.storage = SpecStorage(storage_path)
        self.metrics = HarvestMetrics()
        self.session = None
        self.throttler = None
        self._setup_throttler()
    
    def _setup_throttler(self):
        """Setup request throttler."""
        max_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        self.throttler = Throttler(rate_limit=max_requests, period=1.0)
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def harvest_specs(self, services: List[ServiceInfo]) -> List[APISpec]:
        """Harvest API specifications from services."""
        start_time = datetime.utcnow()
        self.metrics.reset()
        
        logger.info("Starting API spec harvest", service_count=len(services))
        
        async with self:
            # Create semaphore for concurrent requests
            semaphore = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")))
            
            async def harvest_service_spec(service: ServiceInfo) -> Optional[APISpec]:
                async with semaphore:
                    return await self._harvest_single_spec(service)
            
            # Process services concurrently
            tasks = [harvest_service_spec(service) for service in services]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            specs = []
            for result in results:
                if isinstance(result, APISpec):
                    specs.append(result)
                    await self.storage.save_spec(result)
                elif isinstance(result, Exception):
                    logger.error("Spec harvest failed", error=str(result))
                    self.metrics.record_spec_failure()
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        self.metrics.record_duration(duration)
        
        logger.info(
            "API spec harvest completed",
            specs_harvested=len(specs),
            success_rate=self.metrics.success_rate,
            duration=duration
        )
        
        return specs
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _harvest_single_spec(self, service: ServiceInfo) -> Optional[APISpec]:
        """Harvest API spec from a single service."""
        if not service.openapi_endpoint:
            logger.info("No OpenAPI endpoint found", service=service.name)
            return None
        
        self.metrics.record_spec_attempt()
        
        try:
            async with self.throttler:
                logger.info(
                    "Harvesting API spec",
                    service=service.name,
                    endpoint=service.openapi_endpoint
                )
                
                async with self.session.get(service.openapi_endpoint) as response:
                    if response.status != 200:
                        logger.warning(
                            "Failed to fetch API spec",
                            service=service.name,
                            status=response.status
                        )
                        self.metrics.record_spec_failure()
                        return None
                    
                    spec_content = await response.json()
                    
                    # Create API spec object
                    spec = APISpec(
                        service_name=service.name,
                        namespace=service.namespace,
                        spec_url=service.openapi_endpoint,
                        spec_content=spec_content,
                        version=self._extract_version(spec_content)
                    )
                    
                    # Validate spec
                    await self._validate_spec(spec)
                    
                    self.metrics.record_spec_success()
                    logger.info("Successfully harvested API spec", service=service.name)
                    
                    return spec
        
        except Exception as e:
            logger.error(
                "Failed to harvest API spec",
                service=service.name,
                error=str(e)
            )
            self.metrics.record_spec_failure()
            return None
    
    def _extract_version(self, spec_content: Dict) -> Optional[str]:
        """Extract version from OpenAPI spec."""
        info = spec_content.get("info", {})
        return info.get("version")
    
    async def _validate_spec(self, spec: APISpec):
        """Validate OpenAPI specification."""
        try:
            validate_spec(spec.spec_content)
            spec.is_valid = True
            logger.debug("API spec validation passed", service=spec.service_name)
        except Exception as e:
            spec.is_valid = False
            spec.validation_errors.append(str(e))
            self.metrics.record_validation_error()
            logger.warning(
                "API spec validation failed",
                service=spec.service_name,
                error=str(e)
            )
    
    async def detect_changes(self, current_specs: List[APISpec]) -> Dict[str, List[APISpec]]:
        """Detect changes between current and previous specs."""
        changes = {
            "new": [],
            "updated": [],
            "removed": []
        }
        
        for spec in current_specs:
            previous_spec = await self.storage.get_latest_spec(
                spec.service_name, 
                spec.namespace
            )
            
            if not previous_spec:
                changes["new"].append(spec)
            elif self._specs_differ(spec, previous_spec):
                changes["updated"].append(spec)
        
        return changes
    
    def _specs_differ(self, spec1: APISpec, spec2: APISpec) -> bool:
        """Check if two specs are different."""
        # Simple comparison - could be enhanced with semantic diff
        return (
            spec1.version != spec2.version or
            spec1.spec_content != spec2.spec_content
        )
    
    async def create_harvest_job(self, services: List[ServiceInfo]) -> HarvestJob:
        """Create a new harvest job."""
        job_id = f"harvest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return HarvestJob(
            job_id=job_id,
            services=services
        )
    
    async def get_harvest_status(self) -> Dict:
        """Get current harvest status."""
        return {
            "metrics": {
                "services_discovered": self.metrics.services_discovered,
                "specs_attempted": self.metrics.specs_attempted,
                "specs_successful": self.metrics.specs_successful,
                "specs_failed": self.metrics.specs_failed,
                "validation_errors": self.metrics.validation_errors,
                "success_rate": self.metrics.success_rate,
                "total_duration": self.metrics.total_duration
            },
            "storage": {
                "total_specs": len(await self.storage.list_specs())
            }
        }