"""Logging configuration for the application."""

import logging
import os
import sys
from typing import Any, Dict

import structlog


def setup_logging():
    """Setup structured logging configuration."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            _add_service_context,
            structlog.dev.ConsoleRenderer() if _is_development() else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _add_service_context(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add service context to log entries."""
    event_dict["service"] = "api-governance-platform"
    event_dict["version"] = "1.0.0"
    
    # Add environment info
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    
    # Add Kubernetes context if available
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        event_dict["kubernetes"] = {
            "namespace": os.getenv("KUBERNETES_NAMESPACE", "default"),
            "pod_name": os.getenv("HOSTNAME", "unknown"),
            "node_name": os.getenv("KUBERNETES_NODE_NAME", "unknown")
        }
    
    return event_dict


def _is_development() -> bool:
    """Check if running in development mode."""
    return os.getenv("ENVIRONMENT", "development").lower() in ["development", "dev", "local"]


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


class StructlogHandler(logging.Handler):
    """Handler to route standard library logs through structlog."""
    
    def emit(self, record):
        """Emit a log record through structlog."""
        logger = structlog.get_logger(record.name)
        
        # Map logging levels
        level_mapping = {
            logging.DEBUG: logger.debug,
            logging.INFO: logger.info,
            logging.WARNING: logger.warning,
            logging.ERROR: logger.error,
            logging.CRITICAL: logger.critical,
        }
        
        log_func = level_mapping.get(record.levelno, logger.info)
        
        # Extract exception info if present
        exc_info = None
        if record.exc_info:
            exc_info = record.exc_info
        
        # Log the message
        log_func(
            record.getMessage(),
            exc_info=exc_info,
            extra={
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
        )


def setup_third_party_logging():
    """Setup logging for third-party libraries."""
    # Reduce noise from third-party libraries
    logging.getLogger("kubernetes").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Route third-party logs through structlog
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(StructlogHandler())


def configure_uvicorn_logging():
    """Configure uvicorn logging to use structlog."""
    # Disable uvicorn's default logging
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(StructlogHandler())
    
    # Configure access logging
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(StructlogHandler())


class RequestLoggingMiddleware:
    """Middleware for logging HTTP requests."""
    
    def __init__(self, app):
        self.app = app
        self.logger = structlog.get_logger("http")
    
    async def __call__(self, scope, receive, send):
        """Process HTTP request with logging."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request info
        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()
        
        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # Add request context
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=method,
            path=path,
            query_string=query_string
        ):
            start_time = time.time()
            
            # Log request start
            self.logger.info("Request started")
            
            # Process request
            status_code = 500  # Default to error
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as e:
                self.logger.error("Request failed", error=str(e), exc_info=True)
                raise
            finally:
                # Log request completion
                duration = time.time() - start_time
                self.logger.info(
                    "Request completed",
                    status_code=status_code,
                    duration_ms=round(duration * 1000, 2)
                )


# Import time for middleware
import time