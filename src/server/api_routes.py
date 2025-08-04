"""API routes for the governance platform."""

from datetime import datetime
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = structlog.get_logger()


# Pydantic models for API responses
class ServiceInfoResponse(BaseModel):
    name: str
    namespace: str
    labels: Dict[str, str]
    endpoints: List[str]
    health_endpoint: Optional[str]
    openapi_endpoint: Optional[str]
    istio_sidecar: bool
    service_version: Optional[str]


class APISpecResponse(BaseModel):
    service_name: str
    namespace: str
    spec_url: str
    version: Optional[str]
    harvested_at: datetime
    is_valid: bool
    validation_errors: List[str]


class ConsistencyIssueResponse(BaseModel):
    issue_id: str
    severity: str
    category: str
    title: str
    description: str
    recommendation: str
    affected_services: List[str]


class ConsistencyReportResponse(BaseModel):
    report_id: str
    generated_at: datetime
    specs_analyzed: int
    total_fields: int
    issues: List[ConsistencyIssueResponse]
    summary: Dict[str, int]


class FHIRRecommendationResponse(BaseModel):
    recommendation_id: str
    field_name: str
    current_usage: List[str]
    recommended_name: str
    fhir_path: str
    impact_level: str
    services_affected: List[str]
    implementation_notes: str


class HarvestTriggerRequest(BaseModel):
    namespaces: Optional[List[str]] = None
    force: bool = False


class HarvestStatusResponse(BaseModel):
    status: str
    services_discovered: int
    specs_harvested: int
    success_rate: float
    last_harvest: Optional[datetime]


def create_api_router(platform) -> APIRouter:
    """Create API router with all endpoints."""
    router = APIRouter()
    
    @router.get("/discovered-services", response_model=List[ServiceInfoResponse])
    async def get_discovered_services(
        namespace: Optional[str] = Query(None, description="Filter by namespace")
    ):
        """Get list of discovered services."""
        try:
            services = await platform.discovery.discover_services()
            
            # Filter by namespace if specified
            if namespace:
                services = [s for s in services if s.namespace == namespace]
            
            # Convert to response model
            response_services = []
            for service in services:
                response_services.append(ServiceInfoResponse(
                    name=service.name,
                    namespace=service.namespace,
                    labels=service.labels,
                    endpoints=service.endpoints,
                    health_endpoint=service.health_endpoint,
                    openapi_endpoint=service.openapi_endpoint,
                    istio_sidecar=service.istio_sidecar,
                    service_version=service.service_version
                ))
            
            logger.info("Retrieved discovered services", count=len(response_services))
            return response_services
        
        except Exception as e:
            logger.error("Failed to get discovered services", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve services")
    
    @router.get("/services/{service_name}")
    async def get_service_details(service_name: str, namespace: str = "default"):
        """Get detailed information about a specific service."""
        try:
            services = await platform.discovery.discover_services()
            
            # Find the specific service
            service = next(
                (s for s in services if s.name == service_name and s.namespace == namespace),
                None
            )
            
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
            
            # Get Istio configuration
            istio_config = await platform.discovery.get_istio_configuration(service)
            
            # Get latest API spec if available
            latest_spec = None
            if hasattr(platform.harvester, 'storage'):
                latest_spec = await platform.harvester.storage.get_latest_spec(
                    service_name, namespace
                )
            
            return {
                "service": ServiceInfoResponse(
                    name=service.name,
                    namespace=service.namespace,
                    labels=service.labels,
                    endpoints=service.endpoints,
                    health_endpoint=service.health_endpoint,
                    openapi_endpoint=service.openapi_endpoint,
                    istio_sidecar=service.istio_sidecar,
                    service_version=service.service_version
                ),
                "istio_configuration": istio_config,
                "latest_spec": latest_spec.spec_content if latest_spec else None
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get service details", service=service_name, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve service details")
    
    @router.get("/specs", response_model=List[APISpecResponse])
    async def get_api_specs(
        service_name: Optional[str] = Query(None, description="Filter by service name"),
        namespace: Optional[str] = Query(None, description="Filter by namespace")
    ):
        """Get list of harvested API specifications."""
        try:
            # This would typically query the storage system
            # For now, return empty list as storage integration would be needed
            specs = []
            
            logger.info("Retrieved API specs", count=len(specs))
            return specs
        
        except Exception as e:
            logger.error("Failed to get API specs", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve API specs")
    
    @router.get("/reports/latest", response_model=ConsistencyReportResponse)
    async def get_latest_report():
        """Get the latest consistency report."""
        try:
            # Run a fresh analysis
            services = await platform.discovery.discover_services()
            specs = await platform.harvester.harvest_specs(services)
            report = await platform.analyzer.analyze_consistency(specs)
            
            # Convert issues to response format
            response_issues = []
            for issue in report.issues:
                affected_services = list(set(f.service for f in issue.affected_fields))
                response_issues.append(ConsistencyIssueResponse(
                    issue_id=issue.issue_id,
                    severity=issue.severity.value,
                    category=issue.category,
                    title=issue.title,
                    description=issue.description,
                    recommendation=issue.recommendation,
                    affected_services=affected_services
                ))
            
            return ConsistencyReportResponse(
                report_id=report.report_id,
                generated_at=report.generated_at,
                specs_analyzed=report.specs_analyzed,
                total_fields=report.total_fields,
                issues=response_issues,
                summary=report.summary
            )
        
        except Exception as e:
            logger.error("Failed to get latest report", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to generate report")
    
    @router.get("/reports/{report_id}")
    async def get_report_by_id(report_id: str):
        """Get a specific consistency report by ID."""
        try:
            # This would typically query stored reports
            # For now, return 404 as report storage would be needed
            raise HTTPException(status_code=404, detail="Report not found")
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get report", report_id=report_id, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve report")
    
    @router.get("/fhir/recommendations", response_model=List[FHIRRecommendationResponse])
    async def get_fhir_recommendations():
        """Get FHIR compliance recommendations."""
        try:
            # Run analysis to get recommendations
            services = await platform.discovery.discover_services()
            specs = await platform.harvester.harvest_specs(services)
            report = await platform.analyzer.analyze_consistency(specs)
            recommendations = await platform.fhir_mapper.generate_recommendations(report)
            
            # Convert to response format
            response_recommendations = []
            for rec in recommendations:
                response_recommendations.append(FHIRRecommendationResponse(
                    recommendation_id=rec.recommendation_id,
                    field_name=rec.field_name,
                    current_usage=rec.current_usage,
                    recommended_name=rec.recommended_name,
                    fhir_path=rec.fhir_mapping.fhir_path,
                    impact_level=rec.impact_level,
                    services_affected=rec.services_affected,
                    implementation_notes=rec.implementation_notes
                ))
            
            logger.info("Retrieved FHIR recommendations", count=len(response_recommendations))
            return response_recommendations
        
        except Exception as e:
            logger.error("Failed to get FHIR recommendations", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve recommendations")
    
    @router.get("/fhir/compliance-score")
    async def get_compliance_score():
        """Get overall FHIR compliance score."""
        try:
            # Get all fields from current specs
            services = await platform.discovery.discover_services()
            specs = await platform.harvester.harvest_specs(services)
            
            # Extract all fields
            all_fields = []
            for spec in specs:
                fields = platform.analyzer._extract_fields(spec)
                all_fields.extend(fields)
            
            # Calculate compliance score
            score = await platform.fhir_mapper.calculate_compliance_score(all_fields)
            
            return {
                "overall_score": score.overall_score,
                "category_scores": score.category_scores,
                "total_fields": score.total_fields,
                "compliant_fields": score.compliant_fields,
                "recommendations_count": score.recommendations_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error("Failed to get compliance score", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to calculate compliance score")
    
    @router.post("/harvest/trigger")
    async def trigger_harvest(request: HarvestTriggerRequest):
        """Trigger a manual harvest cycle."""
        try:
            logger.info("Manual harvest triggered", namespaces=request.namespaces, force=request.force)
            
            # Run harvest
            result = await platform.run_harvest()
            
            return {
                "status": "completed",
                "services_discovered": len(result["services"]),
                "specs_harvested": len(result["specs"]),
                "issues_found": len(result["report"].issues),
                "recommendations_generated": len(result["recommendations"]),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error("Failed to trigger harvest", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to trigger harvest")
    
    @router.get("/harvest/status", response_model=HarvestStatusResponse)
    async def get_harvest_status():
        """Get current harvest status."""
        try:
            status = await platform.harvester.get_harvest_status()
            
            return HarvestStatusResponse(
                status="operational",
                services_discovered=status["metrics"]["services_discovered"],
                specs_harvested=status["metrics"]["specs_successful"],
                success_rate=status["metrics"]["success_rate"],
                last_harvest=datetime.utcnow()  # This would be tracked properly
            )
        
        except Exception as e:
            logger.error("Failed to get harvest status", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve harvest status")
    
    @router.get("/namespaces")
    async def get_monitored_namespaces():
        """Get list of monitored namespaces."""
        try:
            namespaces = platform.discovery.discovery_config.namespaces
            
            # Get service counts per namespace
            services = await platform.discovery.discover_services()
            namespace_counts = {}
            for service in services:
                namespace_counts[service.namespace] = namespace_counts.get(service.namespace, 0) + 1
            
            return {
                "namespaces": [
                    {
                        "name": ns,
                        "service_count": namespace_counts.get(ns, 0)
                    }
                    for ns in namespaces
                ],
                "total_namespaces": len(namespaces),
                "total_services": len(services)
            }
        
        except Exception as e:
            logger.error("Failed to get namespaces", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to retrieve namespaces")
    
    @router.get("/dashboard", response_class=HTMLResponse)
    async def web_ui():
        """Simple web UI for the API Governance Platform."""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Governance Platform - FHIR Compliance Dashboard</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .compliance-high { color: #10b981; }
        .compliance-medium { color: #f59e0b; }
        .compliance-low { color: #ef4444; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect } = React;

        const GovernanceDashboard = () => {
            const [services, setServices] = useState([]);
            const [isLoading, setIsLoading] = useState(true);
            const [lastUpdated, setLastUpdated] = useState(null);

            // Mock data for demonstration
            const mockServices = [
                {
                    namespace: 'api',
                    serviceName: 'legacy-donor-service',
                    totalAttributes: 9,
                    nonCompliantAttributes: 8,
                    compliancePercentage: 11.1,
                    openApiUrl: 'http://localhost:8081/swagger-ui.html'
                },
                {
                    namespace: 'api',
                    serviceName: 'modern-donor-service',
                    totalAttributes: 9,
                    nonCompliantAttributes: 1,
                    compliancePercentage: 88.9,
                    openApiUrl: 'http://localhost:8082/swagger-ui.html'
                }
            ];

            useEffect(() => {
                setTimeout(() => {
                    setServices(mockServices);
                    setLastUpdated(new Date().toISOString());
                    setIsLoading(false);
                }, 1000);
            }, []);

            const averageCompliance = services.length > 0 
                ? Math.round(services.reduce((sum, service) => sum + service.compliancePercentage, 0) / services.length)
                : 0;

            if (isLoading) {
                return (
                    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                            <p className="text-gray-600">Loading FHIR compliance dashboard...</p>
                        </div>
                    </div>
                );
            }

            return (
                <div className="min-h-screen bg-gray-50">
                    <div className="bg-white shadow-sm border-b">
                        <div className="max-w-7xl mx-auto px-4 py-6">
                            <h1 className="text-3xl font-bold text-gray-900">
                                🩸 API Governance Platform
                            </h1>
                            <p className="mt-2 text-gray-600">
                                FHIR R4 Compliance Monitoring for Blood Banking Microservices
                            </p>
                        </div>
                    </div>

                    <div className="max-w-7xl mx-auto px-4 py-8">
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Total Services</p>
                                <p className="text-2xl font-bold text-gray-900">{services.length}</p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Average Compliance</p>
                                <p className={`text-2xl font-bold ${averageCompliance >= 70 ? 'compliance-high' : averageCompliance >= 50 ? 'compliance-medium' : 'compliance-low'}`}>
                                    {averageCompliance}%
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Critical Services</p>
                                <p className="text-2xl font-bold text-red-600">
                                    {services.filter(s => s.compliancePercentage < 70).length}
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Fully Compliant</p>
                                <p className="text-2xl font-bold text-green-600">
                                    {services.filter(s => s.compliancePercentage >= 90).length}
                                </p>
                            </div>
                        </div>

                        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
                            <div className="px-6 py-4 border-b">
                                <h2 className="text-lg font-semibold">FHIR Compliance Analysis</h2>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Namespace</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Service Name</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total Attributes</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Non-compliant</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Compliance %</th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">OpenAPI Spec</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {services.map((service, index) => (
                                            <tr key={index} className="hover:bg-gray-50">
                                                <td className="px-6 py-4">
                                                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                                                        {service.namespace}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 font-medium">{service.serviceName}</td>
                                                <td className="px-6 py-4">
                                                    <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                                                        {service.totalAttributes}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`font-semibold ${service.nonCompliantAttributes > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                                        {service.nonCompliantAttributes}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center">
                                                        <span className={`font-semibold ${service.compliancePercentage >= 70 ? 'compliance-high' : service.compliancePercentage >= 50 ? 'compliance-medium' : 'compliance-low'}`}>
                                                            {service.compliancePercentage}%
                                                        </span>
                                                        <div className="ml-3 w-16 bg-gray-200 rounded-full h-2">
                                                            <div 
                                                                className={`h-2 rounded-full ${service.compliancePercentage >= 70 ? 'bg-green-500' : service.compliancePercentage >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                                style={{width: `${service.compliancePercentage}%`}}
                                                            />
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <a href={service.openApiUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800 font-medium">
                                                        📋 View Spec
                                                    </a>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="mt-8 text-center text-sm text-gray-500">
                            <p>API Governance Platform • FHIR R4 Compliance Analysis • Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Never'}</p>
                        </div>
                    </div>
                </div>
            );
        };

        ReactDOM.render(<GovernanceDashboard />, document.getElementById('root'));
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)
    
    return router