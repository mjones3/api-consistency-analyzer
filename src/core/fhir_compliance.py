"""FHIR compliance checker for API governance."""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog

from src.core.api_harvester import APISpec

logger = structlog.get_logger()


class FHIRResourceType(Enum):
    """FHIR resource types relevant to blood banking."""
    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    OBSERVATION = "Observation"
    DIAGNOSTIC_REPORT = "DiagnosticReport"


@dataclass
class FHIRFieldRequirement:
    """FHIR field requirement definition."""
    field_name: str
    fhir_path: str
    data_type: str
    required: bool
    description: str
    example_value: Optional[str] = None
    validation_pattern: Optional[str] = None


@dataclass
class ComplianceIssue:
    """Represents a FHIR compliance issue."""
    field_name: str
    current_type: str
    required_type: str
    current_required: bool
    fhir_required: bool
    issue_description: str
    fhir_compliant_value: str
    openapi_line_number: Optional[int] = None
    severity: str = "error"


class FHIRComplianceChecker:
    """Checks API compliance against FHIR R4 standards."""
    
    def __init__(self):
        self.fhir_patient_requirements = self._load_fhir_patient_requirements()
        self.fhir_data_types = self._load_fhir_data_types()
    
    def _load_fhir_patient_requirements(self) -> Dict[str, FHIRFieldRequirement]:
        """Load FHIR Patient resource requirements."""
        return {
            "resourceType": FHIRFieldRequirement(
                field_name="resourceType",
                fhir_path="Patient.resourceType",
                data_type="string",
                required=True,
                description="FHIR resource type identifier",
                example_value="Patient"
            ),
            "identifier": FHIRFieldRequirement(
                field_name="identifier",
                fhir_path="Patient.identifier",
                data_type="Identifier[]",
                required=True,
                description="An identifier for this patient",
                example_value="[{\"system\": \"http://hospital.org/patient-ids\", \"value\": \"12345\"}]"
            ),
            "name": FHIRFieldRequirement(
                field_name="name",
                fhir_path="Patient.name",
                data_type="HumanName[]",
                required=True,
                description="A name associated with the patient",
                example_value="[{\"use\": \"official\", \"family\": \"Smith\", \"given\": [\"John\"]}]"
            ),
            "telecom": FHIRFieldRequirement(
                field_name="telecom",
                fhir_path="Patient.telecom",
                data_type="ContactPoint[]",
                required=False,
                description="A contact detail for the individual",
                example_value="[{\"system\": \"phone\", \"value\": \"555-1234\", \"use\": \"home\"}]"
            ),
            "gender": FHIRFieldRequirement(
                field_name="gender",
                fhir_path="Patient.gender",
                data_type="code",
                required=True,
                description="Administrative Gender",
                example_value="male",
                validation_pattern="^(male|female|other|unknown)$"
            ),
            "birthDate": FHIRFieldRequirement(
                field_name="birthDate",
                fhir_path="Patient.birthDate",
                data_type="date",
                required=True,
                description="The date of birth for the individual",
                example_value="1985-06-15",
                validation_pattern="^\\d{4}-\\d{2}-\\d{2}$"
            ),
            "address": FHIRFieldRequirement(
                field_name="address",
                fhir_path="Patient.address",
                data_type="Address[]",
                required=False,
                description="An address for the individual",
                example_value="[{\"use\": \"home\", \"line\": [\"123 Main St\"], \"city\": \"Springfield\", \"postalCode\": \"12345\"}]"
            ),
            "active": FHIRFieldRequirement(
                field_name="active",
                fhir_path="Patient.active",
                data_type="boolean",
                required=False,
                description="Whether this patient record is in active use",
                example_value="true"
            ),
            "meta": FHIRFieldRequirement(
                field_name="meta",
                fhir_path="Patient.meta",
                data_type="Meta",
                required=False,
                description="Metadata about the resource",
                example_value="{\"lastUpdated\": \"2023-01-01T12:00:00Z\"}"
            )
        }
    
    def _load_fhir_data_types(self) -> Dict[str, Dict]:
        """Load FHIR data type definitions."""
        return {
            "string": {
                "type": "string",
                "description": "A sequence of Unicode characters"
            },
            "boolean": {
                "type": "boolean",
                "description": "Value of true or false"
            },
            "integer": {
                "type": "integer",
                "description": "A signed integer"
            },
            "date": {
                "type": "string",
                "format": "date",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                "description": "A date in YYYY-MM-DD format"
            },
            "dateTime": {
                "type": "string",
                "format": "date-time",
                "description": "A date and time in ISO 8601 format"
            },
            "code": {
                "type": "string",
                "description": "A string from a controlled vocabulary"
            },
            "Identifier": {
                "type": "object",
                "properties": {
                    "system": {"type": "string"},
                    "value": {"type": "string"}
                },
                "required": ["value"]
            },
            "HumanName": {
                "type": "object",
                "properties": {
                    "use": {"type": "string", "enum": ["usual", "official", "temp", "nickname"]},
                    "family": {"type": "string"},
                    "given": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["family"]
            },
            "ContactPoint": {
                "type": "object",
                "properties": {
                    "system": {"type": "string", "enum": ["phone", "fax", "email", "pager", "url", "sms"]},
                    "value": {"type": "string"},
                    "use": {"type": "string", "enum": ["home", "work", "temp", "old", "mobile"]}
                },
                "required": ["value"]
            },
            "Address": {
                "type": "object",
                "properties": {
                    "use": {"type": "string", "enum": ["home", "work", "temp", "old", "billing"]},
                    "line": {"type": "array", "items": {"type": "string"}},
                    "city": {"type": "string"},
                    "state": {"type": "string"},
                    "postalCode": {"type": "string"},
                    "country": {"type": "string"}
                }
            },
            "Meta": {
                "type": "object",
                "properties": {
                    "lastUpdated": {"type": "string", "format": "date-time"},
                    "versionId": {"type": "string"}
                }
            }
        }
    
    async def analyze_service_compliance(self, spec: APISpec) -> Dict[str, Any]:
        """Analyze a service's FHIR compliance."""
        try:
            openapi_spec = spec.spec_content
            
            # Extract schema information
            schemas = openapi_spec.get("components", {}).get("schemas", {})
            
            # Find the main resource schema (look for Patient-like schemas)
            main_schema = self._identify_main_resource_schema(schemas)
            
            if not main_schema:
                return {
                    "compliance_score": 0,
                    "total_fields": 0,
                    "compliant_fields": 0,
                    "issues": ["No Patient-like resource schema found"],
                    "recommendations": []
                }
            
            # Analyze compliance
            compliance_result = self._analyze_schema_compliance(main_schema, schemas)
            
            return {
                "compliance_score": compliance_result["score"],
                "total_fields": compliance_result["total_fields"],
                "compliant_fields": compliance_result["compliant_fields"],
                "issues": compliance_result["issues"],
                "recommendations": compliance_result["recommendations"]
            }
            
        except Exception as e:
            logger.error("Failed to analyze FHIR compliance", error=str(e))
            return {
                "compliance_score": 0,
                "total_fields": 0,
                "compliant_fields": 0,
                "issues": [f"Analysis failed: {str(e)}"],
                "recommendations": []
            }
    
    def _identify_main_resource_schema(self, schemas: Dict) -> Optional[Dict]:
        """Identify the main resource schema (Patient-like)."""
        # Look for schemas that might represent a Patient resource
        patient_indicators = ["patient", "donor", "person", "individual"]
        
        for schema_name, schema_def in schemas.items():
            name_lower = schema_name.lower()
            if any(indicator in name_lower for indicator in patient_indicators):
                return schema_def
        
        # If no obvious Patient schema, return the first complex schema
        for schema_name, schema_def in schemas.items():
            if isinstance(schema_def, dict) and "properties" in schema_def:
                return schema_def
        
        return None
    
    def _analyze_schema_compliance(self, schema: Dict, all_schemas: Dict) -> Dict[str, Any]:
        """Analyze a schema's FHIR compliance."""
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        total_fields = len(self.fhir_patient_requirements)
        compliant_fields = 0
        issues = []
        recommendations = []
        
        # Check each FHIR requirement
        for fhir_field, requirement in self.fhir_patient_requirements.items():
            compliance_issue = self._check_field_compliance(
                fhir_field, requirement, properties, required_fields, all_schemas
            )
            
            if compliance_issue:
                issues.append(compliance_issue)
                recommendations.append(self._generate_recommendation(compliance_issue))
            else:
                compliant_fields += 1
        
        # Check for non-FHIR fields that should be mapped
        for field_name, field_def in properties.items():
            if field_name not in self.fhir_patient_requirements:
                mapped_field = self._suggest_fhir_mapping(field_name, field_def)
                if mapped_field:
                    issue = ComplianceIssue(
                        field_name=field_name,
                        current_type=field_def.get("type", "unknown"),
                        required_type=mapped_field["fhir_type"],
                        current_required=field_name in required_fields,
                        fhir_required=mapped_field["required"],
                        issue_description=f"Non-FHIR field '{field_name}' should be mapped to FHIR field '{mapped_field['fhir_field']}'",
                        fhir_compliant_value=mapped_field["example"],
                        severity="warning"
                    )
                    issues.append(issue)
                    recommendations.append(self._generate_recommendation(issue))
        
        score = (compliant_fields / total_fields * 100) if total_fields > 0 else 0
        
        return {
            "score": round(score, 1),
            "total_fields": total_fields,
            "compliant_fields": compliant_fields,
            "issues": issues,
            "recommendations": recommendations
        }
    
    def _check_field_compliance(
        self, 
        fhir_field: str, 
        requirement: FHIRFieldRequirement, 
        properties: Dict, 
        required_fields: List[str],
        all_schemas: Dict
    ) -> Optional[ComplianceIssue]:
        """Check if a field complies with FHIR requirements."""
        
        if fhir_field not in properties:
            return ComplianceIssue(
                field_name=fhir_field,
                current_type="missing",
                required_type=requirement.data_type,
                current_required=False,
                fhir_required=requirement.required,
                issue_description=f"Missing required FHIR field '{fhir_field}'",
                fhir_compliant_value=requirement.example_value or f"Add {requirement.data_type} field",
                severity="error" if requirement.required else "warning"
            )
        
        field_def = properties[fhir_field]
        current_type = self._get_field_type(field_def, all_schemas)
        is_required = fhir_field in required_fields
        
        # Check type compliance
        if not self._is_type_compliant(current_type, requirement.data_type):
            return ComplianceIssue(
                field_name=fhir_field,
                current_type=current_type,
                required_type=requirement.data_type,
                current_required=is_required,
                fhir_required=requirement.required,
                issue_description=f"Field '{fhir_field}' has type '{current_type}' but FHIR requires '{requirement.data_type}'",
                fhir_compliant_value=requirement.example_value or f"Change to {requirement.data_type}",
                severity="error"
            )
        
        # Check required compliance
        if requirement.required and not is_required:
            return ComplianceIssue(
                field_name=fhir_field,
                current_type=current_type,
                required_type=requirement.data_type,
                current_required=is_required,
                fhir_required=requirement.required,
                issue_description=f"Field '{fhir_field}' should be required according to FHIR",
                fhir_compliant_value="Mark as required in schema",
                severity="warning"
            )
        
        # Check validation pattern if applicable
        if requirement.validation_pattern:
            current_pattern = field_def.get("pattern")
            if current_pattern != requirement.validation_pattern:
                return ComplianceIssue(
                    field_name=fhir_field,
                    current_type=current_type,
                    required_type=requirement.data_type,
                    current_required=is_required,
                    fhir_required=requirement.required,
                    issue_description=f"Field '{fhir_field}' pattern doesn't match FHIR requirements",
                    fhir_compliant_value=f"Use pattern: {requirement.validation_pattern}",
                    severity="warning"
                )
        
        return None
    
    def _get_field_type(self, field_def: Dict, all_schemas: Dict) -> str:
        """Get the effective type of a field."""
        if "$ref" in field_def:
            ref_name = field_def["$ref"].split("/")[-1]
            return ref_name
        
        field_type = field_def.get("type", "unknown")
        
        if field_type == "array":
            items = field_def.get("items", {})
            if "$ref" in items:
                ref_name = items["$ref"].split("/")[-1]
                return f"{ref_name}[]"
            else:
                item_type = items.get("type", "unknown")
                return f"{item_type}[]"
        
        return field_type
    
    def _is_type_compliant(self, current_type: str, fhir_type: str) -> bool:
        """Check if current type is compliant with FHIR type."""
        # Handle array types
        if fhir_type.endswith("[]"):
            base_fhir_type = fhir_type[:-2]
            if current_type.endswith("[]"):
                base_current_type = current_type[:-2]
                return self._is_base_type_compliant(base_current_type, base_fhir_type)
            return False
        
        return self._is_base_type_compliant(current_type, fhir_type)
    
    def _is_base_type_compliant(self, current_type: str, fhir_type: str) -> bool:
        """Check if base types are compliant."""
        # Direct match
        if current_type == fhir_type:
            return True
        
        # Type mappings
        type_mappings = {
            "string": ["string", "code"],
            "integer": ["integer"],
            "boolean": ["boolean"],
            "date": ["string"],  # Date can be represented as string
            "dateTime": ["string"],  # DateTime can be represented as string
        }
        
        fhir_acceptable = type_mappings.get(fhir_type, [fhir_type])
        return current_type in fhir_acceptable
    
    def _suggest_fhir_mapping(self, field_name: str, field_def: Dict) -> Optional[Dict]:
        """Suggest FHIR mapping for non-FHIR fields."""
        field_mappings = {
            "donorId": {"fhir_field": "identifier", "fhir_type": "Identifier[]", "required": True, "example": "[{\"value\": \"D123456\"}]"},
            "firstName": {"fhir_field": "name.given", "fhir_type": "string[]", "required": True, "example": "[\"John\"]"},
            "lastName": {"fhir_field": "name.family", "fhir_type": "string", "required": True, "example": "Smith"},
            "phoneNumber": {"fhir_field": "telecom", "fhir_type": "ContactPoint[]", "required": False, "example": "[{\"system\": \"phone\", \"value\": \"555-1234\"}]"},
            "email": {"fhir_field": "telecom", "fhir_type": "ContactPoint[]", "required": False, "example": "[{\"system\": \"email\", \"value\": \"john@example.com\"}]"},
            "zip": {"fhir_field": "address.postalCode", "fhir_type": "string", "required": False, "example": "12345"},
            "createdDate": {"fhir_field": "meta.lastUpdated", "fhir_type": "dateTime", "required": False, "example": "2023-01-01T12:00:00Z"}
        }
        
        return field_mappings.get(field_name)
    
    def _generate_recommendation(self, issue: ComplianceIssue) -> Dict[str, Any]:
        """Generate a recommendation for fixing a compliance issue."""
        return {
            "field_name": issue.field_name,
            "current_type": issue.current_type,
            "required_type": issue.required_type,
            "current_required": issue.current_required,
            "fhir_required": issue.fhir_required,
            "issue_description": issue.issue_description,
            "fhir_compliant_value": issue.fhir_compliant_value,
            "severity": issue.severity,
            "openapi_line_number": issue.openapi_line_number,
            "action_required": self._get_action_required(issue)
        }
    
    def _get_action_required(self, issue: ComplianceIssue) -> str:
        """Get the action required to fix the issue."""
        if issue.current_type == "missing":
            return f"Add field '{issue.field_name}' with type '{issue.required_type}'"
        elif issue.current_type != issue.required_type:
            return f"Change field '{issue.field_name}' from '{issue.current_type}' to '{issue.required_type}'"
        elif issue.fhir_required and not issue.current_required:
            return f"Mark field '{issue.field_name}' as required"
        else:
            return f"Update field '{issue.field_name}' to match FHIR specification"
    
    async def get_detailed_recommendations(self, spec: APISpec) -> Dict[str, Any]:
        """Get detailed recommendations with line numbers."""
        compliance_result = await self.analyze_service_compliance(spec)
        
        # Add line numbers to recommendations
        openapi_content = json.dumps(spec.spec_content, indent=2)
        lines = openapi_content.split('\n')
        
        for recommendation in compliance_result.get("recommendations", []):
            line_number = self._find_field_line_number(
                recommendation["field_name"], 
                lines
            )
            recommendation["openapi_line_number"] = line_number
        
        return compliance_result
    
    def _find_field_line_number(self, field_name: str, lines: List[str]) -> Optional[int]:
        """Find the line number where a field is defined in the OpenAPI spec."""
        for i, line in enumerate(lines, 1):
            if f'"{field_name}"' in line and ":" in line:
                return i
        return None