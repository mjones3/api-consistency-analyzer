"""Web UI routes for the API Governance Platform."""

import json
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.fhir_compliance import FHIRComplianceChecker

logger = structlog.get_logger()

# Initialize templates
templates = Jinja2Templates(directory="src/templates")

def create_web_ui_router(platform) -> APIRouter:
    """Create web UI router."""
    router = APIRouter()
    
    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Main React dashboard page."""
        try:
            return templates.TemplateResponse("react_dashboard.html", {
                "request": request
            })
            
        except Exception as e:
            logger.error("Failed to load dashboard", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to load dashboard")
    
    @router.get("/api/services")
    async def get_services_data(namespace: Optional[str] = None):
        """Get services data with FHIR compliance analysis."""
        try:
            # Get discovered services
            services = await platform.discovery.discover_services()
            
            # Filter by namespace if specified
            if namespace and namespace != "all":
                services = [s for s in services if s.namespace == namespace]
            
            # Get FHIR compliance checker
            fhir_checker = FHIRComplianceChecker()
            
            services_data = []
            total_compliance = 0
            
            for service in services:
                try:
                    # Get OpenAPI spec
                    spec = await platform.harvester._harvest_single_spec(service)
                    if not spec:
                        continue
                    
                    # Analyze FHIR compliance
                    compliance_result = await fhir_checker.analyze_service_compliance(spec)
                    detailed_recommendations = await fhir_checker.get_detailed_recommendations(spec)
                    
                    total_attributes = compliance_result.get("total_fields", 0)
                    compliant_attributes = compliance_result.get("compliant_fields", 0)
                    non_compliant = total_attributes - compliant_attributes
                    compliance_percentage = (compliant_attributes / total_attributes * 100) if total_attributes > 0 else 0
                    
                    # Extract FHIR violations with line numbers
                    fhir_violations = []
                    for recommendation in detailed_recommendations.get("recommendations", []):
                        fhir_violations.append({
                            "fieldName": recommendation.get("field_name", ""),
                            "currentType": recommendation.get("current_type", ""),
                            "requiredType": recommendation.get("required_type", ""),
                            "currentRequired": recommendation.get("current_required", False),
                            "fhirRequired": recommendation.get("fhir_required", False),
                            "issueDescription": recommendation.get("issue_description", ""),
                            "fhirCompliantValue": recommendation.get("fhir_compliant_value", ""),
                            "openApiLineNumber": recommendation.get("openapi_line_number"),
                            "severity": recommendation.get("severity", "warning"),
                            "actionRequired": recommendation.get("action_required", "")
                        })
                    
                    service_data = {
                        "namespace": service.namespace,
                        "serviceName": service.name,
                        "totalAttributes": total_attributes,
                        "nonCompliantAttributes": non_compliant,
                        "compliancePercentage": round(compliance_percentage, 1),
                        "openApiUrl": service.openapi_endpoint.replace("svc.cluster.local", "localhost"),
                        "recommendationsUrl": f"/recommendations/{service.name}",
                        "fhirViolations": fhir_violations
                    }
                    
                    services_data.append(service_data)
                    total_compliance += compliance_percentage
                    
                except Exception as e:
                    logger.error("Failed to analyze service", service=service.name, error=str(e))
                    # Add service with error state
                    services_data.append({
                        "namespace": service.namespace,
                        "serviceName": service.name,
                        "totalAttributes": 0,
                        "nonCompliantAttributes": 0,
                        "compliancePercentage": 0,
                        "openApiUrl": service.openapi_endpoint,
                        "recommendationsUrl": f"/recommendations/{service.name}",
                        "fhirViolations": [],
                        "error": str(e)
                    })
            
            # Calculate average compliance
            average_compliance = (total_compliance / len(services_data)) if services_data else 0
            
            return {
                "services": services_data,
                "summary": {
                    "totalServices": len(services_data),
                    "averageCompliance": round(average_compliance, 1),
                    "criticalServices": len([s for s in services_data if s["compliancePercentage"] < 70]),
                    "fullyCompliantServices": len([s for s in services_data if s["compliancePercentage"] == 100])
                },
                "lastUpdated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get services data", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get services data")
    
    @router.post("/api/harvest")
    async def trigger_harvest():
        """Trigger a new harvest."""
        try:
            result = await platform.run_harvest()
            return {
                "status": "success",
                "message": "Harvest completed successfully",
                "services_analyzed": len(result.get("services", [])),
                "specs_harvested": len(result.get("specs", [])),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Failed to trigger harvest", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to trigger harvest")
    
    @router.get("/api/export/compliance")
    async def export_compliance_report(namespace: Optional[str] = None):
        """Export compliance report as JSON."""
        try:
            services_data = await get_services_data(namespace)
            
            report = {
                "report_metadata": {
                    "generated_at": datetime.utcnow().isoformat(),
                    "platform_version": "1.0.0",
                    "namespace_filter": namespace or "all",
                    "total_services": len(services_data["services"])
                },
                "compliance_summary": {
                    "total_services": len(services_data["services"]),
                    "fully_compliant": len([s for s in services_data["services"] if s["compliance_percentage"] == 100]),
                    "partially_compliant": len([s for s in services_data["services"] if 0 < s["compliance_percentage"] < 100]),
                    "non_compliant": len([s for s in services_data["services"] if s["compliance_percentage"] == 0]),
                    "average_compliance": sum(s["compliance_percentage"] for s in services_data["services"]) / len(services_data["services"]) if services_data["services"] else 0
                },
                "services": services_data["services"]
            }
            
            return report
            
        except Exception as e:
            logger.error("Failed to export compliance report", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to export compliance report")
    
    @router.get("/swagger-ui/{service_name}", response_class=HTMLResponse)
    async def swagger_ui(request: Request, service_name: str):
        """Display Swagger UI for a service."""
        try:
            # Find the service
            services = await platform.discovery.discover_services()
            service = next((s for s in services if s.name == service_name), None)
            
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
            
            return templates.TemplateResponse("swagger_ui.html", {
                "request": request,
                "service_name": service_name,
                "openapi_url": service.openapi_endpoint
            })
            
        except Exception as e:
            logger.error("Failed to load Swagger UI", service=service_name, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to load Swagger UI")
    
    @router.get("/recommendations/{service_name}", response_class=HTMLResponse)
    async def service_recommendations(request: Request, service_name: str):
        """Display FHIR compliance recommendations for a service."""
        try:
            # Find the service
            services = await platform.discovery.discover_services()
            service = next((s for s in services if s.name == service_name), None)
            
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
            
            # Get OpenAPI spec
            spec = await platform.harvester._harvest_single_spec(service)
            if not spec:
                raise HTTPException(status_code=404, detail="OpenAPI spec not found")
            
            # Get FHIR compliance analysis
            fhir_checker = FHIRComplianceChecker()
            compliance_result = await fhir_checker.get_detailed_recommendations(spec)
            
            return templates.TemplateResponse("recommendations.html", {
                "request": request,
                "service_name": service_name,
                "service": service,
                "recommendations": compliance_result.get("recommendations", []),
                "compliance_score": compliance_result.get("compliance_score", 0),
                "total_fields": compliance_result.get("total_fields", 0),
                "compliant_fields": compliance_result.get("compliant_fields", 0)
            })
            
        except Exception as e:
            logger.error("Failed to load recommendations", service=service_name, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to load recommendations")
    
    @router.get("/api/recommendations/{service_name}")
    async def get_service_recommendations(service_name: str):
        """Get detailed FHIR recommendations for a service."""
        try:
            # Find the service
            services = await platform.discovery.discover_services()
            service = next((s for s in services if s.name == service_name), None)
            
            if not service:
                raise HTTPException(status_code=404, detail="Service not found")
            
            # Get OpenAPI spec
            spec = await platform.harvester._harvest_single_spec(service)
            if not spec:
                raise HTTPException(status_code=404, detail="OpenAPI spec not found")
            
            # Get FHIR compliance analysis
            fhir_checker = FHIRComplianceChecker()
            compliance_result = await fhir_checker.get_detailed_recommendations(spec)
            
            return compliance_result
            
        except Exception as e:
            logger.error("Failed to get recommendations", service=service_name, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get recommendations")
    
    return router