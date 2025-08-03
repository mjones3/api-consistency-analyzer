"""Unit tests for Istio service discovery."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.istio_discovery import IstioServiceDiscovery, ServiceInfo, HealthChecker


class TestIstioServiceDiscovery:
    """Test cases for IstioServiceDiscovery."""
    
    @pytest.fixture
    def discovery(self, mock_kubernetes_config):
        """Create IstioServiceDiscovery instance for testing."""
        with patch('src.core.istio_discovery.client'):
            return IstioServiceDiscovery()
    
    @pytest.mark.asyncio
    async def test_discover_services_empty_namespace(self, discovery, mock_k8s_client):
        """Test service discovery with empty namespace."""
        # Mock empty service list
        mock_service_list = MagicMock()
        mock_service_list.items = []
        mock_k8s_client.CoreV1Api.return_value.list_namespaced_service.return_value = mock_service_list
        
        with patch('src.core.istio_discovery.client', mock_k8s_client):
            services = await discovery.discover_services()
        
        assert services == []
    
    @pytest.mark.asyncio
    async def test_discover_services_with_matching_service(self, discovery, mock_k8s_client):
        """Test service discovery with matching service."""
        # Create mock service
        mock_service = MagicMock()
        mock_service.metadata.name = "test-service"
        mock_service.metadata.namespace = "default"
        mock_service.metadata.labels = {"app": "spring-boot"}
        mock_service.metadata.annotations = {"sidecar.istio.io/inject": "true"}
        mock_service.spec.ports = [MagicMock(port=8080)]
        
        mock_service_list = MagicMock()
        mock_service_list.items = [mock_service]
        mock_k8s_client.CoreV1Api.return_value.list_namespaced_service.return_value = mock_service_list
        
        with patch('src.core.istio_discovery.client', mock_k8s_client):
            with patch.object(discovery, '_filter_and_enrich_services', return_value=[]):
                services = await discovery.discover_services()
        
        # Should call the filter method
        assert isinstance(services, list)
    
    def test_matches_criteria_with_matching_labels(self, discovery):
        """Test service matching with correct labels."""
        mock_service = MagicMock()
        mock_service.metadata.labels = {"app": "spring-boot"}
        mock_service.metadata.annotations = {}
        
        result = discovery._matches_criteria(mock_service)
        assert result is True
    
    def test_matches_criteria_with_non_matching_labels(self, discovery):
        """Test service matching with incorrect labels."""
        mock_service = MagicMock()
        mock_service.metadata.labels = {"app": "nodejs"}
        mock_service.metadata.annotations = {}
        
        result = discovery._matches_criteria(mock_service)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_service_info(self, discovery):
        """Test ServiceInfo creation from Kubernetes service."""
        mock_service = MagicMock()
        mock_service.metadata.name = "test-service"
        mock_service.metadata.labels = {"app": "spring-boot", "version": "1.0.0"}
        mock_service.metadata.annotations = {"sidecar.istio.io/inject": "true"}
        mock_service.spec.ports = [MagicMock(port=8080)]
        
        service_info = await discovery._create_service_info(mock_service, "default")
        
        assert service_info is not None
        assert service_info.name == "test-service"
        assert service_info.namespace == "default"
        assert service_info.istio_sidecar is True
        assert service_info.service_version == "1.0.0"
        assert len(service_info.endpoints) == 1


class TestHealthChecker:
    """Test cases for HealthChecker."""
    
    @pytest.mark.asyncio
    async def test_check_health_success(self, sample_service_info):
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        health_checker = HealthChecker()
        health_checker.session = mock_session
        
        result = await health_checker.check_health(sample_service_info)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_health_failure(self, sample_service_info):
        """Test failed health check."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        health_checker = HealthChecker()
        health_checker.session = mock_session
        
        result = await health_checker.check_health(sample_service_info)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_health_no_endpoint(self):
        """Test health check with no health endpoint."""
        service_info = ServiceInfo(
            name="test-service",
            namespace="default",
            labels={},
            annotations={},
            endpoints=["http://test-service:8080"],
            health_endpoint=None,
            istio_sidecar=False
        )
        
        health_checker = HealthChecker()
        result = await health_checker.check_health(service_info)
        assert result is True  # Should assume healthy if no endpoint
    
    @pytest.mark.asyncio
    async def test_discover_openapi_endpoint_success(self, sample_service_info):
        """Test successful OpenAPI endpoint discovery."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        health_checker = HealthChecker()
        health_checker.session = mock_session
        
        result = await health_checker.discover_openapi_endpoint(sample_service_info)
        assert result is not None
        assert "/v3/api-docs" in result
    
    @pytest.mark.asyncio
    async def test_discover_openapi_endpoint_not_found(self, sample_service_info):
        """Test OpenAPI endpoint discovery when not found."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        health_checker = HealthChecker()
        health_checker.session = mock_session
        
        result = await health_checker.discover_openapi_endpoint(sample_service_info)
        assert result is None