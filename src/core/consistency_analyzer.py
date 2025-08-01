"""API consistency analyzer module."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import structlog

from src.core.api_harvester import APISpec

logger = structlog.get_logger()


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class FieldInfo:
    """Information about a field in an API spec."""
    name: str
    type: str
    service: str
    namespace: str
    path: str  # JSON path in the spec
    description: Optional[str] = None
    required: bool = False
    format: Optional[str] = None
    example: Optional[str] = None


@dataclass
class ConsistencyIssue:
    """Represents a consistency issue."""
    issue_id: str
    severity: Severity
    category: str
    title: str
    description: str
    affected_fields: List[FieldInfo]
    recommendation: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConsistencyReport:
    """Consistency analysis report."""
    report_id: str
    generated_at: datetime
    specs_analyzed: int
    total_fields: int
    issues: List[ConsistencyIssue]
    summary: Dict[str, int] = field(default_factory=dict)


class FieldComparator:
    """Compares fields across different services."""
    
    def __init__(self):
        self.normalization_rules = self._load_normalization_rules()
        self.blood_banking_patterns = self._load_blood_banking_patterns()
    
    def _load_normalization_rules(self) -> Dict[str, str]:
        """Load field name normalization rules."""
        return {
            # Common variations
            "id": "identifier",
            "uid": "identifier",
            "uuid": "identifier",
            
            # Date/time fields
            "created_at": "creation_timestamp",
            "createdAt": "creation_timestamp",
            "created_date": "creation_timestamp",
            "date_created": "creation_timestamp",
            "createddate": "creation_timestamp",
            
            "updated_at": "modification_timestamp",
            "updatedAt": "modification_timestamp",
            "modified_at": "modification_timestamp",
            "last_modified": "modification_timestamp",
            "lastupdated": "modification_timestamp",
            
            # Name fields
            "first_name": "given_name",
            "firstName": "given_name",
            "fname": "given_name",
            "given": "given_name",
            
            "last_name": "family_name",
            "lastName": "family_name",
            "surname": "family_name",
            "lname": "family_name",
            "family": "family_name",
            
            # Address fields
            "zip": "postal_code",
            "zipcode": "postal_code",
            "zip_code": "postal_code",
            "postcode": "postal_code",
            "postalcode": "postal_code",
            
            "phone": "phone_number",
            "tel": "phone_number",
            "telephone": "phone_number",
            "phonenumber": "phone_number",
            
            # Boolean fields
            "is_active": "active_status",
            "isActive": "active_status",
            "active": "active_status",
            "enabled": "active_status",
            
            # Blood banking specific
            "donorid": "donor_identifier",
            "donor_id": "donor_identifier",
            "patientid": "patient_identifier",
            "patient_id": "patient_identifier",
            
            "birthdate": "birth_date",
            "birth_date": "birth_date",
            "dateofbirth": "birth_date",
            "dob": "birth_date",
            
            "bloodtype": "blood_type",
            "blood_type": "blood_type",
            "abo_group": "blood_type",
            "abogroup": "blood_type",
        }
    
    def _load_blood_banking_patterns(self) -> Dict[str, Dict]:
        """Load blood banking specific field patterns for Arc One domain."""
        return {
            "donor_identification": {
                "legacy_patterns": ["donorId", "donor_id", "id"],
                "fhir_pattern": "identifier",
                "description": "Donor identification field inconsistency"
            },
            "name_structure": {
                "legacy_patterns": ["firstName", "lastName", "first_name", "last_name"],
                "fhir_pattern": "name.given|name.family",
                "description": "Name field structure inconsistency"
            },
            "contact_information": {
                "legacy_patterns": ["phoneNumber", "email", "phone", "phone_number"],
                "fhir_pattern": "telecom.value",
                "description": "Contact information structure inconsistency"
            },
            "address_structure": {
                "legacy_patterns": ["zip", "zipCode", "streetAddress", "city", "state"],
                "fhir_pattern": "address.postalCode|address.line|address.city|address.state",
                "description": "Address structure inconsistency"
            },
            "temporal_fields": {
                "legacy_patterns": ["createdDate", "created_at", "lastDonationDate"],
                "fhir_pattern": "meta.lastUpdated",
                "description": "Temporal field inconsistency"
            },
            "gender_representation": {
                "legacy_patterns": ["gender"],
                "fhir_pattern": "gender",
                "description": "Gender representation inconsistency (M/F vs FHIR codes)"
            }
        }
    
    def normalize_field_name(self, field_name: str) -> str:
        """Normalize field name for comparison."""
        # Convert to lowercase and replace common separators
        normalized = field_name.lower()
        normalized = re.sub(r'[-_\s]+', '_', normalized)
        
        # Apply normalization rules
        return self.normalization_rules.get(normalized, normalized)
    
    def compare_fields(self, field1: FieldInfo, field2: FieldInfo) -> Optional[ConsistencyIssue]:
        """Compare two fields and return issue if inconsistent."""
        norm1 = self.normalize_field_name(field1.name)
        norm2 = self.normalize_field_name(field2.name)
        
        # If normalized names are the same but original names differ
        if norm1 == norm2 and field1.name != field2.name:
            severity = self._determine_severity(field1, field2)
            
            return ConsistencyIssue(
                issue_id=f"naming_{norm1}_{field1.service}_{field2.service}",
                severity=severity,
                category="naming_inconsistency",
                title=f"Inconsistent naming for {norm1}",
                description=f"Field '{field1.name}' in {field1.service} and '{field2.name}' in {field2.service} represent the same concept but use different names",
                affected_fields=[field1, field2],
                recommendation=f"Consider standardizing to a common name like '{norm1}'"
            )
        
        # Check type inconsistencies
        if norm1 == norm2 and field1.type != field2.type:
            return ConsistencyIssue(
                issue_id=f"type_{norm1}_{field1.service}_{field2.service}",
                severity=Severity.MAJOR,
                category="type_inconsistency",
                title=f"Type mismatch for {norm1}",
                description=f"Field '{field1.name}' has type '{field1.type}' in {field1.service} but type '{field2.type}' in {field2.service}",
                affected_fields=[field1, field2],
                recommendation="Ensure consistent data types across services"
            )
        
        return None
    
    def _determine_severity(self, field1: FieldInfo, field2: FieldInfo) -> Severity:
        """Determine severity of naming inconsistency."""
        # Critical if both fields are required
        if field1.required and field2.required:
            return Severity.CRITICAL
        
        # Major if one is required
        if field1.required or field2.required:
            return Severity.MAJOR
        
        # Minor for optional fields
        return Severity.MINOR


class InconsistencyRule:
    """Base class for inconsistency detection rules."""
    
    def __init__(self, rule_id: str, category: str, severity: Severity):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for inconsistencies in the given fields."""
        raise NotImplementedError


class NamingConventionRule(InconsistencyRule):
    """Rule for checking naming conventions."""
    
    def __init__(self):
        super().__init__("naming_convention", "naming", Severity.MINOR)
        self.conventions = {
            "camelCase": re.compile(r'^[a-z][a-zA-Z0-9]*$'),
            "snake_case": re.compile(r'^[a-z][a-z0-9_]*$'),
            "kebab-case": re.compile(r'^[a-z][a-z0-9-]*$'),
            "PascalCase": re.compile(r'^[A-Z][a-zA-Z0-9]*$')
        }
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for naming convention inconsistencies."""
        issues = []
        
        # Group fields by service
        services = {}
        for field in fields:
            if field.service not in services:
                services[field.service] = []
            services[field.service].append(field)
        
        # Check each service's naming convention
        for service, service_fields in services.items():
            conventions_used = set()
            
            for field in service_fields:
                for convention, pattern in self.conventions.items():
                    if pattern.match(field.name):
                        conventions_used.add(convention)
                        break
            
            # If multiple conventions are used in the same service
            if len(conventions_used) > 1:
                issues.append(ConsistencyIssue(
                    issue_id=f"mixed_conventions_{service}",
                    severity=self.severity,
                    category=self.category,
                    title=f"Mixed naming conventions in {service}",
                    description=f"Service {service} uses multiple naming conventions: {', '.join(conventions_used)}",
                    affected_fields=service_fields,
                    recommendation="Use a consistent naming convention throughout the service"
                ))
        
        return issues


class BloodBankingFieldNamingRule(InconsistencyRule):
    """Rule for checking blood banking specific field naming inconsistencies."""
    
    def __init__(self):
        super().__init__("blood_banking_naming", "blood_banking", Severity.MAJOR)
        self.blood_banking_patterns = {
            "donor_identification": ["donorId", "donor_id", "identifier", "id"],
            "name_fields": ["firstName", "lastName", "first_name", "last_name", "given", "family"],
            "contact_fields": ["phoneNumber", "phone", "email", "telecom"],
            "address_fields": ["zip", "zipCode", "postalCode", "postal_code", "streetAddress", "address"],
            "temporal_fields": ["createdDate", "created_at", "lastUpdated", "meta"],
            "gender_fields": ["gender"]
        }
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for blood banking specific naming inconsistencies."""
        issues = []
        
        # Group fields by service
        services = {}
        for field in fields:
            if field.service not in services:
                services[field.service] = []
            services[field.service].append(field)
        
        # Check for Arc One specific patterns
        for pattern_name, pattern_fields in self.blood_banking_patterns.items():
            service_patterns = {}
            
            for service, service_fields in services.items():
                matching_fields = []
                for field in service_fields:
                    if any(pattern in field.name.lower() for pattern in [p.lower() for p in pattern_fields]):
                        matching_fields.append(field)
                
                if matching_fields:
                    service_patterns[service] = matching_fields
            
            # If multiple services have different patterns for the same concept
            if len(service_patterns) > 1:
                all_affected_fields = []
                service_names = []
                
                for service, fields_list in service_patterns.items():
                    all_affected_fields.extend(fields_list)
                    service_names.append(service)
                
                # Check if they're actually different patterns
                field_names = set(f.name for f in all_affected_fields)
                if len(field_names) > 1:
                    issues.append(ConsistencyIssue(
                        issue_id=f"blood_banking_{pattern_name}_{hash(tuple(sorted(service_names)))}",
                        severity=self.severity,
                        category=self.category,
                        title=f"Blood banking {pattern_name.replace('_', ' ')} inconsistency",
                        description=f"Services use different field naming patterns for {pattern_name}: {', '.join(field_names)}",
                        affected_fields=all_affected_fields,
                        recommendation=f"Standardize {pattern_name.replace('_', ' ')} field naming across all blood banking services"
                    ))
        
        return issues


class DataTypeInconsistencyRule(InconsistencyRule):
    """Rule for checking data type inconsistencies in blood banking domain."""
    
    def __init__(self):
        super().__init__("data_type_inconsistency", "data_types", Severity.CRITICAL)
        self.critical_type_mappings = {
            "postal_code": ["string", "integer"],  # zip vs postalCode
            "birth_date": ["string", "date", "localdate"],  # birthDate formats
            "timestamp": ["localdatetime", "instant", "string"]  # timestamp formats
        }
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for critical data type inconsistencies."""
        issues = []
        
        # Group fields by normalized concept
        from src.core.consistency_analyzer import FieldComparator
        comparator = FieldComparator()
        
        concept_groups = {}
        for field in fields:
            normalized = comparator.normalize_field_name(field.name)
            if normalized not in concept_groups:
                concept_groups[normalized] = []
            concept_groups[normalized].append(field)
        
        # Check each concept group for type inconsistencies
        for concept, field_group in concept_groups.items():
            if len(field_group) < 2:
                continue
            
            # Get unique types in this group
            types_in_group = set(f.type.lower() for f in field_group)
            
            # Check if this concept has critical type variations
            for critical_concept, expected_types in self.critical_type_mappings.items():
                if critical_concept in concept.lower():
                    # Check if we have conflicting types
                    conflicting_types = types_in_group.intersection(set(expected_types))
                    if len(conflicting_types) > 1:
                        issues.append(ConsistencyIssue(
                            issue_id=f"type_inconsistency_{concept}_{hash(tuple(sorted(conflicting_types)))}",
                            severity=self.severity,
                            category=self.category,
                            title=f"Critical data type inconsistency for {concept}",
                            description=f"Field {concept} has conflicting data types: {', '.join(conflicting_types)}. This can cause integration issues.",
                            affected_fields=field_group,
                            recommendation=f"Standardize {concept} to use consistent data type across all services"
                        ))
        
        return issues


class ValidationPatternRule(InconsistencyRule):
    """Rule for checking validation pattern inconsistencies."""
    
    def __init__(self):
        super().__init__("validation_patterns", "validation", Severity.MAJOR)
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for validation pattern inconsistencies."""
        issues = []
        
        # This would analyze validation annotations from the OpenAPI specs
        # For now, we'll create a placeholder that identifies common validation issues
        
        phone_fields = [f for f in fields if 'phone' in f.name.lower()]
        if len(phone_fields) > 1:
            # Check if phone validation patterns differ
            issues.append(ConsistencyIssue(
                issue_id=f"phone_validation_patterns",
                severity=self.severity,
                category=self.category,
                title="Phone number validation pattern inconsistency",
                description="Phone number fields use different validation patterns across services",
                affected_fields=phone_fields,
                recommendation="Standardize phone number validation to use consistent pattern (e.g., \\d{10} or structured ContactPoint)"
            ))
        
        return issues


class RequiredFieldRule(InconsistencyRule):
    """Rule for checking required field consistency."""
    
    def __init__(self):
        super().__init__("required_fields", "validation", Severity.MAJOR)
    
    def check(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Check for required field inconsistencies."""
        issues = []
        
        # Group fields by normalized name
        field_groups = {}
        comparator = FieldComparator()
        
        for field in fields:
            normalized = comparator.normalize_field_name(field.name)
            if normalized not in field_groups:
                field_groups[normalized] = []
            field_groups[normalized].append(field)
        
        # Check each group for required field inconsistencies
        for normalized_name, group_fields in field_groups.items():
            if len(group_fields) < 2:
                continue
            
            required_fields = [f for f in group_fields if f.required]
            optional_fields = [f for f in group_fields if not f.required]
            
            if required_fields and optional_fields:
                issues.append(ConsistencyIssue(
                    issue_id=f"required_inconsistency_{normalized_name}",
                    severity=self.severity,
                    category=self.category,
                    title=f"Required field inconsistency for {normalized_name}",
                    description=f"Field {normalized_name} is required in some services but optional in others",
                    affected_fields=group_fields,
                    recommendation="Ensure consistent required/optional status across services"
                ))
        
        return issues


class ReportGenerator:
    """Generates consistency reports."""
    
    def generate_markdown_report(self, report: ConsistencyReport) -> str:
        """Generate Markdown format report."""
        md = f"""# API Consistency Report

**Report ID:** {report.report_id}
**Generated:** {report.generated_at.isoformat()}
**Specs Analyzed:** {report.specs_analyzed}
**Total Fields:** {report.total_fields}

## Summary

| Severity | Count |
|----------|-------|
"""
        
        for severity in Severity:
            count = report.summary.get(severity.value, 0)
            md += f"| {severity.value.title()} | {count} |\n"
        
        md += "\n## Issues\n\n"
        
        for issue in sorted(report.issues, key=lambda x: (x.severity.value, x.title)):
            md += f"### {issue.title}\n\n"
            md += f"**Severity:** {issue.severity.value.title()}\n"
            md += f"**Category:** {issue.category}\n"
            md += f"**Description:** {issue.description}\n"
            md += f"**Recommendation:** {issue.recommendation}\n\n"
            
            md += "**Affected Fields:**\n"
            for field in issue.affected_fields:
                md += f"- `{field.name}` ({field.type}) in {field.service}.{field.namespace}\n"
            md += "\n"
        
        return md
    
    def generate_json_report(self, report: ConsistencyReport) -> Dict:
        """Generate JSON format report."""
        return {
            "report_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "specs_analyzed": report.specs_analyzed,
            "total_fields": report.total_fields,
            "summary": report.summary,
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "title": issue.title,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "affected_fields": [
                        {
                            "name": field.name,
                            "type": field.type,
                            "service": field.service,
                            "namespace": field.namespace,
                            "path": field.path,
                            "required": field.required
                        }
                        for field in issue.affected_fields
                    ]
                }
                for issue in report.issues
            ]
        }


class ConsistencyAnalyzer:
    """Analyzes API specifications for consistency issues."""
    
    def __init__(self):
        self.comparator = FieldComparator()
        self.rules = [
            NamingConventionRule(),
            RequiredFieldRule(),
            BloodBankingFieldNamingRule(),
            DataTypeInconsistencyRule(),
            ValidationPatternRule()
        ]
        self.report_generator = ReportGenerator()
    
    async def analyze_consistency(self, specs: List[APISpec]) -> ConsistencyReport:
        """Analyze consistency across API specifications."""
        logger.info("Starting consistency analysis", spec_count=len(specs))
        
        # Extract all fields from specs
        all_fields = []
        for spec in specs:
            fields = self._extract_fields(spec)
            all_fields.extend(fields)
        
        logger.info("Extracted fields", field_count=len(all_fields))
        
        # Find consistency issues
        issues = []
        
        # Apply comparison rules
        issues.extend(self._find_comparison_issues(all_fields))
        
        # Apply custom rules
        for rule in self.rules:
            rule_issues = rule.check(all_fields)
            issues.extend(rule_issues)
        
        # Generate summary
        summary = {}
        for severity in Severity:
            summary[severity.value] = len([i for i in issues if i.severity == severity])
        
        # Create report
        report = ConsistencyReport(
            report_id=f"consistency_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.utcnow(),
            specs_analyzed=len(specs),
            total_fields=len(all_fields),
            issues=issues,
            summary=summary
        )
        
        logger.info(
            "Consistency analysis completed",
            issues_found=len(issues),
            critical=summary.get("critical", 0),
            major=summary.get("major", 0),
            minor=summary.get("minor", 0)
        )
        
        return report
    
    def _extract_fields(self, spec: APISpec) -> List[FieldInfo]:
        """Extract field information from an API spec."""
        fields = []
        
        try:
            # Extract from OpenAPI components/schemas
            components = spec.spec_content.get("components", {})
            schemas = components.get("schemas", {})
            
            for schema_name, schema_def in schemas.items():
                schema_fields = self._extract_schema_fields(
                    schema_def, spec, f"components.schemas.{schema_name}"
                )
                fields.extend(schema_fields)
            
            # Extract from paths (request/response bodies)
            paths = spec.spec_content.get("paths", {})
            for path, path_def in paths.items():
                path_fields = self._extract_path_fields(path_def, spec, f"paths.{path}")
                fields.extend(path_fields)
        
        except Exception as e:
            logger.error(
                "Failed to extract fields from spec",
                service=spec.service_name,
                error=str(e)
            )
        
        return fields
    
    def _extract_schema_fields(self, schema: Dict, spec: APISpec, path: str) -> List[FieldInfo]:
        """Extract fields from a schema definition."""
        fields = []
        
        if "properties" in schema:
            required_fields = set(schema.get("required", []))
            
            for field_name, field_def in schema["properties"].items():
                field_info = FieldInfo(
                    name=field_name,
                    type=field_def.get("type", "unknown"),
                    service=spec.service_name,
                    namespace=spec.namespace,
                    path=f"{path}.properties.{field_name}",
                    description=field_def.get("description"),
                    required=field_name in required_fields,
                    format=field_def.get("format"),
                    example=field_def.get("example")
                )
                fields.append(field_info)
        
        return fields
    
    def _extract_path_fields(self, path_def: Dict, spec: APISpec, path: str) -> List[FieldInfo]:
        """Extract fields from path definitions."""
        fields = []
        
        for method, method_def in path_def.items():
            if method.startswith("x-"):
                continue
            
            # Extract from request body
            request_body = method_def.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                for content_type, content_def in content.items():
                    schema = content_def.get("schema", {})
                    if schema:
                        schema_fields = self._extract_schema_fields(
                            schema, spec, f"{path}.{method}.requestBody.content.{content_type}.schema"
                        )
                        fields.extend(schema_fields)
            
            # Extract from responses
            responses = method_def.get("responses", {})
            for status_code, response_def in responses.items():
                content = response_def.get("content", {})
                for content_type, content_def in content.items():
                    schema = content_def.get("schema", {})
                    if schema:
                        schema_fields = self._extract_schema_fields(
                            schema, spec, f"{path}.{method}.responses.{status_code}.content.{content_type}.schema"
                        )
                        fields.extend(schema_fields)
        
        return fields
    
    def _find_comparison_issues(self, fields: List[FieldInfo]) -> List[ConsistencyIssue]:
        """Find issues by comparing fields."""
        issues = []
        
        # Compare each field with every other field
        for i, field1 in enumerate(fields):
            for field2 in fields[i+1:]:
                issue = self.comparator.compare_fields(field1, field2)
                if issue:
                    issues.append(issue)
        
        return issues
    
    async def generate_report(self, report: ConsistencyReport, format: str = "json") -> str:
        """Generate report in specified format."""
        if format == "markdown":
            return self.report_generator.generate_markdown_report(report)
        elif format == "json":
            import json
            return json.dumps(self.report_generator.generate_json_report(report), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def add_custom_rule(self, rule: InconsistencyRule):
        """Add a custom inconsistency rule."""
        self.rules.append(rule)
        logger.info("Added custom rule", rule_id=rule.rule_id)