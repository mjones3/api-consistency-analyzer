"""Data models for API compliance analysis."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class SeverityLevel(str, Enum):
    """Severity levels for compliance issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class IssueType(str, Enum):
    """Types of compliance issues."""
    NAMING_CONVENTION = "naming_convention"
    ERROR_RESPONSE = "error_response"
    HTTP_METHOD = "http_method"
    ENDPOINT_PATTERN = "endpoint_pattern"


class NamingInconsistency(BaseModel):
    """Model for naming inconsistency issues."""
    field_name: str
    current_naming: str
    suggested_naming: str
    endpoint: str
    severity: SeverityLevel
    rule_violated: str
    description: str


class ErrorResponseInconsistency(BaseModel):
    """Model for error response inconsistency issues."""
    issue_type: str
    endpoint: str
    http_status: int
    description: str
    recommendation: str
    severity: SeverityLevel
    missing_fields: List[str] = []
    incorrect_schema: Optional[Dict] = None


class ServiceComplianceOverview(BaseModel):
    """Overview of service compliance status."""
    service_name: str
    namespace: str
    total_endpoints: int
    inconsistent_naming_count: int
    inconsistent_error_count: int
    compliance_percentage: float
    naming_issues: List[NamingInconsistency]
    error_issues: List[ErrorResponseInconsistency]
    last_analyzed: datetime
    openapi_url: Optional[str] = None


class ComplianceRule(BaseModel):
    """Configuration for compliance rules."""
    rule_id: str
    rule_type: IssueType
    severity: SeverityLevel
    enabled: bool
    description: str
    pattern: Optional[str] = None
    suggestion_template: Optional[str] = None


class ComplianceSummary(BaseModel):
    """Summary of compliance across all services."""
    total_services: int
    average_compliance: float
    critical_issues: int
    major_issues: int
    minor_issues: int
    services_by_compliance: Dict[str, int]  # e.g., {"high": 5, "medium": 3, "low": 2}
    last_updated: datetime


class SpectralResult(BaseModel):
    """Result from Spectral validation."""
    code: str
    message: str
    path: List[str]
    severity: int  # 0=error, 1=warn, 2=info, 3=hint
    range: Dict
    source: Optional[str] = None


class ValidationReport(BaseModel):
    """Complete validation report for a service."""
    service_name: str
    namespace: str
    spec_url: str
    validation_timestamp: datetime
    spectral_results: List[SpectralResult]
    naming_issues: List[NamingInconsistency]
    error_issues: List[ErrorResponseInconsistency]
    compliance_score: float
    total_issues: int