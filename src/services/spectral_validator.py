"""Spectral OpenAPI Style Validator Integration."""

import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import structlog
import yaml
from pydantic import BaseModel

from src.models.compliance_models import (
    ErrorResponseInconsistency,
    NamingInconsistency,
    SeverityLevel,
    SpectralResult,
    ValidationReport,
)

logger = structlog.get_logger()


class SpectralValidator:
    """Integrates with Spectral for OpenAPI style validation."""
    
    def __init__(self, ruleset_path: str = ".spectral.yml"):
        self.ruleset_path = Path(ruleset_path)
        self.spectral_installed = self._check_spectral_installation()
        
    def _check_spectral_installation(self) -> bool:
        """Check if Spectral CLI is available."""
        try:
            result = subprocess.run(
                ["npx", "@stoplight/spectral-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("Spectral CLI available", version=result.stdout.strip())
                return True
            else:
                logger.warning("Spectral CLI not available, using fallback validation")
                return False
        except Exception as e:
            logger.warning("Failed to check Spectral installation", error=str(e))
            return False
    
    async def validate_openapi_spec(
        self, 
        spec_content: Dict, 
        service_name: str,
        namespace: str,
        spec_url: str
    ) -> ValidationReport:
        """Validate OpenAPI specification using Spectral."""
        try:
            if self.spectral_installed:
                spectral_results = await self._run_spectral_validation(spec_content)
            else:
                spectral_results = await self._fallback_validation(spec_content)
            
            # Convert Spectral results to our compliance models
            naming_issues = self._extract_naming_issues(spectral_results, spec_content)
            error_issues = self._extract_error_issues(spectral_results, spec_content)
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(
                spectral_results, naming_issues, error_issues
            )
            
            return ValidationReport(
                service_name=service_name,
                namespace=namespace,
                spec_url=spec_url,
                validation_timestamp=datetime.utcnow(),
                spectral_results=spectral_results,
                naming_issues=naming_issues,
                error_issues=error_issues,
                compliance_score=compliance_score,
                total_issues=len(spectral_results)
            )
            
        except Exception as e:
            logger.error("Failed to validate OpenAPI spec", 
                        service=service_name, error=str(e))
            # Return empty report on failure
            return ValidationReport(
                service_name=service_name,
                namespace=namespace,
                spec_url=spec_url,
                validation_timestamp=datetime.utcnow(),
                spectral_results=[],
                naming_issues=[],
                error_issues=[],
                compliance_score=0.0,
                total_issues=0
            )
    
    async def _run_spectral_validation(self, spec_content: Dict) -> List[SpectralResult]:
        """Run Spectral CLI validation."""
        try:
            # Write spec to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(spec_content, f, indent=2)
                temp_spec_path = f.name
            
            # Run Spectral validation
            cmd = [
                "npx", "@stoplight/spectral-cli", "lint",
                temp_spec_path,
                "--ruleset", str(self.ruleset_path),
                "--format", "json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temp file
            Path(temp_spec_path).unlink(missing_ok=True)
            
            if result.stdout:
                spectral_output = json.loads(result.stdout)
                return [SpectralResult(**item) for item in spectral_output]
            else:
                return []
                
        except Exception as e:
            logger.error("Spectral validation failed", error=str(e))
            return []
    
    async def _fallback_validation(self, spec_content: Dict) -> List[SpectralResult]:
        """Fallback validation when Spectral is not available."""
        issues = []
        
        # Basic naming convention checks
        if "paths" in spec_content:
            for path, methods in spec_content["paths"].items():
                # Check path naming (kebab-case)
                if not self._is_kebab_case_path(path):
                    issues.append(SpectralResult(
                        code="arc-one-path-kebab-case",
                        message=f"Path '{path}' should use kebab-case",
                        path=["paths", path],
                        severity=1,  # warn
                        range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}
                    ))
                
                for method, operation in methods.items():
                    if isinstance(operation, dict):
                        # Check for missing error responses
                        responses = operation.get("responses", {})
                        if "400" not in responses:
                            issues.append(SpectralResult(
                                code="arc-one-error-response-400",
                                message="Missing 400 Bad Request response",
                                path=["paths", path, method, "responses"],
                                severity=1,  # warn
                                range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}
                            ))
                        
                        if "500" not in responses:
                            issues.append(SpectralResult(
                                code="arc-one-error-response-500",
                                message="Missing 500 Internal Server Error response",
                                path=["paths", path, method, "responses"],
                                severity=1,  # warn
                                range={"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}
                            ))
        
        return issues
    
    def _extract_naming_issues(
        self, 
        spectral_results: List[SpectralResult], 
        spec_content: Dict
    ) -> List[NamingInconsistency]:
        """Extract naming inconsistencies from Spectral results."""
        naming_issues = []
        
        for result in spectral_results:
            if "naming" in result.code.lower() or "camelcase" in result.code.lower():
                # Extract field name from path
                field_name = self._extract_field_name_from_path(result.path)
                endpoint = self._extract_endpoint_from_path(result.path)
                
                naming_issues.append(NamingInconsistency(
                    field_name=field_name,
                    current_naming=field_name,
                    suggested_naming=self._suggest_camel_case(field_name),
                    endpoint=endpoint,
                    severity=self._map_spectral_severity(result.severity),
                    rule_violated=result.code,
                    description=result.message
                ))
        
        return naming_issues
    
    def _extract_error_issues(
        self, 
        spectral_results: List[SpectralResult], 
        spec_content: Dict
    ) -> List[ErrorResponseInconsistency]:
        """Extract error response inconsistencies from Spectral results."""
        error_issues = []
        
        for result in spectral_results:
            if "error" in result.code.lower() or "response" in result.code.lower():
                endpoint = self._extract_endpoint_from_path(result.path)
                
                # Determine HTTP status from the issue
                http_status = 400  # default
                if "400" in result.message:
                    http_status = 400
                elif "500" in result.message:
                    http_status = 500
                elif "404" in result.message:
                    http_status = 404
                elif "401" in result.message:
                    http_status = 401
                
                error_issues.append(ErrorResponseInconsistency(
                    issue_type="missing_error_response" if "Missing" in result.message else "inconsistent_schema",
                    endpoint=endpoint,
                    http_status=http_status,
                    description=result.message,
                    recommendation=self._generate_error_recommendation(result.code),
                    severity=self._map_spectral_severity(result.severity),
                    missing_fields=self._extract_missing_fields(result.message)
                ))
        
        return error_issues
    
    def _calculate_compliance_score(
        self, 
        spectral_results: List[SpectralResult],
        naming_issues: List[NamingInconsistency],
        error_issues: List[ErrorResponseInconsistency]
    ) -> float:
        """Calculate overall compliance score."""
        if not spectral_results:
            return 100.0
        
        # Weight different severity levels
        total_weight = 0
        issue_weight = 0
        
        for result in spectral_results:
            if result.severity == 0:  # error
                total_weight += 3
                issue_weight += 3
            elif result.severity == 1:  # warn
                total_weight += 2
                issue_weight += 2
            else:  # info/hint
                total_weight += 1
                issue_weight += 1
        
        # Add base weight for having any endpoints
        base_weight = 10
        total_weight += base_weight
        
        if total_weight == 0:
            return 100.0
        
        compliance = ((total_weight - issue_weight) / total_weight) * 100
        return max(0.0, min(100.0, compliance))
    
    def _is_kebab_case_path(self, path: str) -> bool:
        """Check if path uses kebab-case convention."""
        import re
        # Allow parameters in curly braces
        pattern = r'^(/[a-z0-9-]+(\{[a-zA-Z0-9]+\})?)*/?$'
        return bool(re.match(pattern, path))
    
    def _extract_field_name_from_path(self, path: List[str]) -> str:
        """Extract field name from JSONPath."""
        if path:
            return path[-1] if path[-1] != "~" else path[-2] if len(path) > 1 else "unknown"
        return "unknown"
    
    def _extract_endpoint_from_path(self, path: List[str]) -> str:
        """Extract endpoint from JSONPath."""
        if len(path) >= 2 and path[0] == "paths":
            return path[1]
        return "unknown"
    
    def _suggest_camel_case(self, field_name: str) -> str:
        """Suggest camelCase version of field name."""
        if "_" in field_name:
            parts = field_name.split("_")
            return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])
        return field_name
    
    def _map_spectral_severity(self, severity: int) -> SeverityLevel:
        """Map Spectral severity to our severity levels."""
        if severity == 0:  # error
            return SeverityLevel.CRITICAL
        elif severity == 1:  # warn
            return SeverityLevel.MAJOR
        else:  # info/hint
            return SeverityLevel.MINOR
    
    def _generate_error_recommendation(self, rule_code: str) -> str:
        """Generate recommendation based on rule code."""
        recommendations = {
            "arc-one-error-response-400": "Add 400 Bad Request response with error schema",
            "arc-one-error-response-500": "Add 500 Internal Server Error response with error schema",
            "arc-one-error-schema-consistency": "Use consistent error schema with 'error', 'message', and 'timestamp' fields"
        }
        return recommendations.get(rule_code, "Follow API governance guidelines")
    
    def _extract_missing_fields(self, message: str) -> List[str]:
        """Extract missing fields from error message."""
        missing_fields = []
        if "error" in message.lower():
            missing_fields.append("error")
        if "message" in message.lower():
            missing_fields.append("message")
        if "timestamp" in message.lower():
            missing_fields.append("timestamp")
        return missing_fields