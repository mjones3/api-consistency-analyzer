"""Main application entry point."""

import asyncio
import os
import signal
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from src.core.api_harvester import APIHarvester
from src.core.consistency_analyzer import ConsistencyAnalyzer
from src.core.fhir_mapper import FHIRMapper
from src.core.istio_discovery import IstioServiceDiscovery
from src.server.api_routes import create_api_router
from src.server.health_server import create_health_router
from src.utils.logging_config import setup_logging
from src.utils.metrics import setup_metrics

logger = structlog.get_logger()


class APIGovernancePlatform:
    """Main application class."""
    
    def __init__(self):
        self.discovery = None
        self.harvester = None
        self.analyzer = None
        self.fhir_mapper = None
        self.harvest_task = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing API Governance Platform")
        
        # Initialize components
        self.discovery = IstioServiceDiscovery()
        self.harvester = APIHarvester(self.discovery)
        self.analyzer = ConsistencyAnalyzer()
        self.fhir_mapper = FHIRMapper()
        
        # Start background harvest task if in continuous mode
        if os.getenv("RUN_MODE", "continuous") == "continuous":
            self.harvest_task = asyncio.create_task(self._harvest_loop())
        
        logger.info("Platform initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        logger.info("Shutting down API Governance Platform")
        
        self.shutdown_event.set()
        
        if self.harvest_task:
            self.harvest_task.cancel()
            try:
                await self.harvest_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Platform shutdown complete")
    
    async def _harvest_loop(self):
        """Background harvest loop."""
        interval_hours = int(os.getenv("HARVEST_INTERVAL_HOURS", "6"))
        interval_seconds = interval_hours * 3600
        
        while not self.shutdown_event.is_set():
            try:
                logger.info("Starting scheduled harvest cycle")
                await self.run_harvest()
                logger.info("Harvest cycle completed")
            except Exception as e:
                logger.error("Harvest cycle failed", error=str(e))
            
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(), 
                    timeout=interval_seconds
                )
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue  # Time for next harvest
    
    async def run_harvest(self):
        """Run a complete harvest cycle."""
        # Discover services
        services = await self.discovery.discover_services()
        logger.info("Discovered services", count=len(services))
        
        # Harvest API specs
        specs = await self.harvester.harvest_specs(services)
        logger.info("Harvested API specs", count=len(specs))
        
        # Analyze consistency
        report = await self.analyzer.analyze_consistency(specs)
        logger.info("Generated consistency report", issues=len(report.issues))
        
        # Generate FHIR recommendations
        recommendations = await self.fhir_mapper.generate_recommendations(report)
        logger.info("Generated FHIR recommendations", count=len(recommendations))
        
        return {
            "services": services,
            "specs": specs,
            "report": report,
            "recommendations": recommendations
        }


# Global platform instance
platform = APIGovernancePlatform()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await platform.initialize()
    yield
    # Shutdown
    await platform.shutdown()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Microservices API Governance Platform",
        description="Automated API governance with Istio integration and FHIR compliance",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add routers
    app.include_router(create_health_router(), prefix="/health", tags=["health"])
    app.include_router(create_api_router(platform), prefix="/api/v1", tags=["api"])
    
    return app


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


def main():
    """Main entry point."""
    # Setup logging
    setup_logging()
    
    # Setup metrics
    setup_metrics()
    
    # Handle signals
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create app
    app = create_app()
    
    # Run server
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info("Starting API Governance Platform", host=host, port=port)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,  # Use our custom logging
        access_log=False
    )


if __name__ == "__main__":
    main()