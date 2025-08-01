"""Pytest configuration and fixtures."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.api_harvester import APISpec
from src.core.consistency_analyzer import FieldInfo
from src.core.istio_discovery import ServiceInfo


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for storage tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client."""
    mock_client = MagicMock()
    mock_v1 = MagicMock()
    mock_client.CoreV1Api.return_value = mock_v1
    return mock_client


@pytest.fixture
def sample_service_info() -> ServiceInfo:
    """Sample ServiceInfo for testing."""
    return ServiceInfo(
        name="user-service",
        namespace="default",
        labels={"app": "spring-boot", "version": "1.0.0"},
        annotations={"sidecar.istio.io/inject": "true"},
        endpoints=["http://user-service.default.svc.cluster.local:8080"],
        health_endpoint="http://user-service.default.svc.cluster.local:8080/actuator/health",
        openapi_endpoint="http://user-service.default.svc.cluster.local:8080/v3/api-docs",
        istio_sidecar=True,
        service_version="1.0.0"
    )


@pytest.fixture
def sample_services() -> List[ServiceInfo]:
    """Sample list of services for testing."""
    return [
        ServiceInfo(
            name="user-service",
            namespace="default",
            labels={"app": "spring-boot"},
            annotations={"sidecar.istio.io/inject": "true"},
            endpoints=["http://user-service.default.svc.cluster.local:8080"],
            health_endpoint="http://user-service.default.svc.cluster.local:8080/actuator/health",
            openapi_endpoint="http://user-service.default.svc.cluster.local:8080/v3/api-docs",
            istio_sidecar=True
        ),
        ServiceInfo(
            name="order-service",
            namespace="default",
            labels={"app": "spring-boot"},
            annotations={"sidecar.istio.io/inject": "true"},
            endpoints=["http://order-service.default.svc.cluster.local:8080"],
            health_endpoint="http://order-service.default.svc.cluster.local:8080/actuator/health",
            openapi_endpoint="http://order-service.default.svc.cluster.local:8080/v3/api-docs",
            istio_sidecar=True
        )
    ]


@pytest.fixture
def sample_openapi_spec() -> Dict:
    """Sample OpenAPI specification."""
    return {
        "openapi": "3.0.1",
        "info": {
            "title": "User Service API",
            "version": "1.0.0"
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "firstName", "lastName"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "User identifier"
                        },
                        "firstName": {
                            "type": "string",
                            "description": "User's first name"
                        },
                        "lastName": {
                            "type": "string",
                            "description": "User's last name"
                        },
                        "email": {
                            "type": "string",
                            "format": "email",
                            "description": "User's email address"
                        },
                        "phoneNumber": {
                            "type": "string",
                            "description": "User's phone number"
                        },
                        "createdAt": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Creation timestamp"
                        }
                    }
                }
            }
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get all users",
                    "responses": {
                        "200": {
                            "description": "List of users",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create a user",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/User"
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "User created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_api_spec(sample_openapi_spec) -> APISpec:
    """Sample APISpec for testing."""
    return APISpec(
        service_name="user-service",
        namespace="default",
        spec_url="http://user-service.default.svc.cluster.local:8080/v3/api-docs",
        spec_content=sample_openapi_spec,
        version="1.0.0"
    )


@pytest.fixture
def sample_field_info() -> FieldInfo:
    """Sample FieldInfo for testing."""
    return FieldInfo(
        name="firstName",
        type="string",
        service="user-service",
        namespace="default",
        path="components.schemas.User.properties.firstName",
        description="User's first name",
        required=True
    )


@pytest.fixture
def sample_fields() -> List[FieldInfo]:
    """Sample list of fields for testing."""
    return [
        FieldInfo(
            name="firstName",
            type="string",
            service="user-service",
            namespace="default",
            path="components.schemas.User.properties.firstName",
            required=True
        ),
        FieldInfo(
            name="first_name",
            type="string",
            service="order-service",
            namespace="default",
            path="components.schemas.Customer.properties.first_name",
            required=True
        ),
        FieldInfo(
            name="lastName",
            type="string",
            service="user-service",
            namespace="default",
            path="components.schemas.User.properties.lastName",
            required=True
        ),
        FieldInfo(
            name="last_name",
            type="string",
            service="order-service",
            namespace="default",
            path="components.schemas.Customer.properties.last_name",
            required=False
        )
    ]


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing."""
    session = AsyncMock()
    
    # Mock successful health check
    health_response = AsyncMock()
    health_response.status = 200
    session.get.return_value.__aenter__.return_value = health_response
    
    return session


@pytest.fixture
def mock_discovery_service():
    """Mock discovery service for testing."""
    discovery = AsyncMock()
    discovery.discover_services.return_value = []
    return discovery


@pytest.fixture
def environment_variables():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        "KUBERNETES_NAMESPACES": "default,test",
        "HARVEST_INTERVAL_HOURS": "1",
        "MAX_CONCURRENT_REQUESTS": "5",
        "FHIR_COMPLIANCE_MODE": "true",
        "LOG_LEVEL": "DEBUG",
        "METRICS_ENABLED": "true",
        "STORAGE_PATH": "/tmp/test-storage"
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_kubernetes_config():
    """Mock Kubernetes configuration."""
    with pytest.mock.patch('kubernetes.config.load_incluster_config'):
        with pytest.mock.patch('kubernetes.config.load_kube_config'):
            yield


@pytest.fixture
def sample_consistency_report():
    """Sample consistency report for testing."""
    from src.core.consistency_analyzer import ConsistencyReport, ConsistencyIssue, Severity
    from datetime import datetime
    
    issues = [
        ConsistencyIssue(
            issue_id="test_issue_1",
            severity=Severity.MAJOR,
            category="naming_inconsistency",
            title="Inconsistent field naming",
            description="Field naming inconsistency detected",
            affected_fields=[],
            recommendation="Standardize field names"
        )
    ]
    
    return ConsistencyReport(
        report_id="test_report_1",
        generated_at=datetime.utcnow(),
        specs_analyzed=2,
        total_fields=10,
        issues=issues,
        summary={"major": 1, "minor": 0, "critical": 0}
    )