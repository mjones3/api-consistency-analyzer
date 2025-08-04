"""Enhanced compliance analyzer for OpenAPI style validation."""

from datetime import datetime
from typing import Dict, List, Optional

import structlog

from src.models.compliance_models import (
    ComplianceSummary,
    ServiceComplianceOverview,
    SeverityLevel,
)
from src.services.spectral_validator import SpectralValidator

logger = structlog.get_logger()


class ComplianceAnalyzer:
    """Analyzes API compliance using Spectral validation."""
    
    def __init__(self):
        self.spectral_validator = SpectralValidator()
        self.compliance_cache: Dict[str, ServiceComplianceOverview] = {}
    
    async def analyze_service_compliance(
        self, 
        service_name: str,
        namespace: str,
        spec_content: Dict,
        spec_url: str
    ) -> ServiceComplianceOverview:
        """Analyze compliance for a single service."""
        try:
            logger.info("Analyzing service compliance", 
                       service=service_name, namespace=namespace)
            
            # Run Spectral validation
            validation_report = await self.spectral_validator.validate_openapi_spec(
                spec_content, service_name, namespace, spec_url
            )
            
            # Count endpoints
            total_endpoints = self._count_endpoints(spec_content)
            
            # Create compliance overview
            compliance_overview = ServiceComplianceOverview(
                service_name=service_name,
                namespace=namespace,
                total_endpoints=total_endpoints,
                inconsistent_naming_count=len(validation_report.naming_issues),
                inconsistent_error_count=len(validation_report.error_issues),
                compliance_percentage=validation_report.compliance_score,
                naming_issues=validation_report.naming_issues,
                error_issues=validation_report.error_issues,
                last_analyzed=datetime.utcnow(),
                openapi_url=spec_url
            )
            
            # Cache the result
            cache_key = f"{namespace}:{service_name}"
            self.compliance_cache[cache_key] = compliance_overview
            
            logger.info("Service compliance analysis completed",
                       service=service_name,
                       compliance_score=validation_report.compliance_score,
                       naming_issues=len(validation_report.naming_issues),
                       error_issues=len(validation_report.error_issues))
            
            return compliance_overview
            
        except Exception as e:
            logger.error("Failed to analyze service compliance",
                        service=service_name, error=str(e))
            
            # Return minimal compliance overview on error
            return ServiceComplianceOverview(
                service_name=service_name,
                namespace=namespace,
                total_endpoints=0,
                inconsistent_naming_count=0,
                inconsistent_error_count=0,
                compliance_percentage=0.0,
                naming_issues=[],
                error_issues=[],
                last_analyzed=datetime.utcnow(),
                openapi_url=spec_url
            )
    
    async def analyze_all_services(
        self, 
        services_specs: List[Dict]
    ) -> List[ServiceComplianceOverview]:
        """Analyze compliance for all services."""
        compliance_overviews = []
        
        for service_spec in services_specs:
            try:
                overview = await self.analyze_service_compliance(
                    service_spec["service_name"],
                    service_spec["namespace"],
                    service_spec["spec_content"],
                    service_spec["spec_url"]
                )
                compliance_overviews.append(overview)
            except Exception as e:
                logger.error("Failed to analyze service",
                           service=service_spec.get("service_name", "unknown"),
                           error=str(e))
        
        return compliance_overviews
    
    def get_compliance_summary(
        self, 
        compliance_overviews: List[ServiceComplianceOverview]
    ) -> ComplianceSummary:
        """Generate compliance summary across all services."""
        if not compliance_overviews:
            return ComplianceSummary(
                total_services=0,
                average_compliance=0.0,
                critical_issues=0,
                major_issues=0,
                minor_issues=0,
                services_by_compliance={"high": 0, "medium": 0, "low": 0},
                last_updated=datetime.utcnow()
            )
        
        total_services = len(compliance_overviews)
        total_compliance = sum(overview.compliance_percentage for overview in compliance_overviews)
        average_compliance = total_compliance / total_services if total_services > 0 else 0.0
        
        # Count issues by severity
        critical_issues = 0
        major_issues = 0
        minor_issues = 0
        
        for overview in compliance_overviews:
            for issue in overview.naming_issues + overview.error_issues:
                if issue.severity == SeverityLevel.CRITICAL:
                    critical_issues += 1
                elif issue.severity == SeverityLevel.MAJOR:
                    major_issues += 1
                else:
                    minor_issues += 1
        
        # Categorize services by compliance level
        high_compliance = sum(1 for o in compliance_overviews if o.compliance_percentage >= 90)
        medium_compliance = sum(1 for o in compliance_overviews if 70 <= o.compliance_percentage < 90)
        low_compliance = sum(1 for o in compliance_overviews if o.compliance_percentage < 70)
        
        return ComplianceSummary(
            total_services=total_services,
            average_compliance=round(average_compliance, 1),
            critical_issues=critical_issues,
            major_issues=major_issues,
            minor_issues=minor_issues,
            services_by_compliance={
                "high": high_compliance,
                "medium": medium_compliance,
                "low": low_compliance
            },
            last_updated=datetime.utcnow()
        )
    
    def get_cached_compliance(self, service_name: str, namespace: str) -> Optional[ServiceComplianceOverview]:
        """Get cached compliance data for a service."""
        cache_key = f"{namespace}:{service_name}"
        return self.compliance_cache.get(cache_key)
    
    def clear_cache(self):
        """Clear the compliance cache."""
        self.compliance_cache.clear()
        logger.info("Compliance cache cleared")
    
    def _count_endpoints(self, spec_content: Dict) -> int:
        """Count total endpoints in OpenAPI spec."""
        if "paths" not in spec_content:
            return 0
        
        endpoint_count = 0
        for path, methods in spec_content["paths"].items():
            if isinstance(methods, dict):
                # Count HTTP methods (excluding parameters and other non-method keys)
                http_methods = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}
                endpoint_count += sum(1 for method in methods.keys() if method.lower() in http_methods)
        
        return endpoint_count
    
    def get_service_naming_details(
        self, 
        service_name: str, 
        namespace: str
    ) -> Optional[List[Dict]]:
        """Get detailed naming inconsistencies for a service."""
        compliance = self.get_cached_compliance(service_name, namespace)
        if not compliance:
            return None
        
        return [
            {
                "field_name": issue.field_name,
                "current_naming": issue.current_naming,
                "suggested_naming": issue.suggested_naming,
                "endpoint": issue.endpoint,
                "severity": issue.severity.value,
                "rule_violated": issue.rule_violated,
                "description": issue.description
            }
            for issue in compliance.naming_issues
        ]
    
    def get_service_error_details(
        self, 
        service_name: str, 
        namespace: str
    ) -> Optional[List[Dict]]:
        """Get detailed error inconsistencies for a service."""
        compliance = self.get_cached_compliance(service_name, namespace)
        if not compliance:
            return None
        
        return [
            {
                "issue_type": issue.issue_type,
                "endpoint": issue.endpoint,
                "http_status": issue.http_status,
                "description": issue.description,
                "recommendation": issue.recommendation,
                "severity": issue.severity.value,
                "missing_fields": issue.missing_fields
            }
            for issue in compliance.error_issues
        ]