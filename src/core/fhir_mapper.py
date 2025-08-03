"""FHIR compliance mapper and recommendation engine."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set

import structlog

from src.core.consistency_analyzer import ConsistencyReport, FieldInfo

logger = structlog.get_logger()


@dataclass
class FHIRMapping:
    """Represents a FHIR field mapping."""
    source_field: str
    fhir_path: str
    fhir_type: str
    confidence: float  # 0.0 to 1.0
    description: str
    example: Optional[str] = None


@dataclass
class FHIRRecommendation:
    """FHIR standardization recommendation."""
    recommendation_id: str
    field_name: str
    current_usage: List[str]  # Current field names across services
    recommended_name: str
    fhir_mapping: FHIRMapping
    impact_level: str  # low, medium, high
    services_affected: List[str]
    implementation_notes: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceScore:
    """FHIR compliance scoring."""
    overall_score: float  # 0.0 to 100.0
    category_scores: Dict[str, float]
    total_fields: int
    compliant_fields: int
    recommendations_count: int


class FHIRMappingDictionary:
    """Dictionary of FHIR field mappings."""
    
    def __init__(self):
        self.mappings = self._load_default_mappings()
        self.custom_mappings = {}
    
    def _load_default_mappings(self) -> Dict[str, FHIRMapping]:
        """Load default FHIR mappings."""
        mappings = {}
        
        # Patient resource mappings
        patient_mappings = {
            'first_name': FHIRMapping(
                source_field='first_name',
                fhir_path='Patient.name.given',
                fhir_type='string',
                confidence=0.95,
                description='Patient given name',
                example='John'
            ),
            'given_name': FHIRMapping(
                source_field='given_name',
                fhir_path='Patient.name.given',
                fhir_type='string',
                confidence=1.0,
                description='Patient given name',
                example='John'
            ),
            'last_name': FHIRMapping(
                source_field='last_name',
                fhir_path='Patient.name.family',
                fhir_type='string',
                confidence=0.95,
                description='Patient family name',
                example='Doe'
            ),
            'family_name': FHIRMapping(
                source_field='family_name',
                fhir_path='Patient.name.family',
                fhir_type='string',
                confidence=1.0,
                description='Patient family name',
                example='Doe'
            ),
            'birth_date': FHIRMapping(
                source_field='birth_date',
                fhir_path='Patient.birthDate',
                fhir_type='date',
                confidence=1.0,
                description='Patient birth date',
                example='1990-01-01'
            ),
            'dob': FHIRMapping(
                source_field='dob',
                fhir_path='Patient.birthDate',
                fhir_type='date',
                confidence=0.9,
                description='Patient birth date',
                example='1990-01-01'
            ),
            'gender': FHIRMapping(
                source_field='gender',
                fhir_path='Patient.gender',
                fhir_type='code',
                confidence=1.0,
                description='Patient gender',
                example='male'
            ),
            'phone': FHIRMapping(
                source_field='phone',
                fhir_path='Patient.telecom.value',
                fhir_type='string',
                confidence=0.8,
                description='Patient phone number',
                example='+1-555-123-4567'
            ),
            'phone_number': FHIRMapping(
                source_field='phone_number',
                fhir_path='Patient.telecom.value',
                fhir_type='string',
                confidence=0.9,
                description='Patient phone number',
                example='+1-555-123-4567'
            ),
            'email': FHIRMapping(
                source_field='email',
                fhir_path='Patient.telecom.value',
                fhir_type='string',
                confidence=1.0,
                description='Patient email address',
                example='john.doe@example.com'
            ),
        }
        
        # Address mappings
        address_mappings = {
            'street': FHIRMapping(
                source_field='street',
                fhir_path='Patient.address.line',
                fhir_type='string',
                confidence=0.9,
                description='Street address',
                example='123 Main St'
            ),
            'city': FHIRMapping(
                source_field='city',
                fhir_path='Patient.address.city',
                fhir_type='string',
                confidence=1.0,
                description='City name',
                example='Springfield'
            ),
            'state': FHIRMapping(
                source_field='state',
                fhir_path='Patient.address.state',
                fhir_type='string',
                confidence=1.0,
                description='State or province',
                example='IL'
            ),
            'zip': FHIRMapping(
                source_field='zip',
                fhir_path='Patient.address.postalCode',
                fhir_type='string',
                confidence=0.8,
                description='Postal code',
                example='62701'
            ),
            'zipcode': FHIRMapping(
                source_field='zipcode',
                fhir_path='Patient.address.postalCode',
                fhir_type='string',
                confidence=0.9,
                description='Postal code',
                example='62701'
            ),
            'postal_code': FHIRMapping(
                source_field='postal_code',
                fhir_path='Patient.address.postalCode',
                fhir_type='string',
                confidence=1.0,
                description='Postal code',
                example='62701'
            ),
            'country': FHIRMapping(
                source_field='country',
                fhir_path='Patient.address.country',
                fhir_type='string',
                confidence=1.0,
                description='Country code',
                example='US'
            ),
        }
        
        # Metadata mappings
        metadata_mappings = {
            'created_at': FHIRMapping(
                source_field='created_at',
                fhir_path='Resource.meta.lastUpdated',
                fhir_type='instant',
                confidence=0.8,
                description='Resource creation timestamp',
                example='2023-01-01T12:00:00Z'
            ),
            'updated_at': FHIRMapping(
                source_field='updated_at',
                fhir_path='Resource.meta.lastUpdated',
                fhir_type='instant',
                confidence=0.9,
                description='Resource last updated timestamp',
                example='2023-01-01T12:00:00Z'
            ),
            'version': FHIRMapping(
                source_field='version',
                fhir_path='Resource.meta.versionId',
                fhir_type='id',
                confidence=0.9,
                description='Resource version identifier',
                example='1'
            ),
        }
        
        # Identifier mappings
        identifier_mappings = {
            'id': FHIRMapping(
                source_field='id',
                fhir_path='Resource.id',
                fhir_type='id',
                confidence=0.7,
                description='Resource identifier',
                example='patient-123'
            ),
            'identifier': FHIRMapping(
                source_field='identifier',
                fhir_path='Resource.id',
                fhir_type='id',
                confidence=1.0,
                description='Resource identifier',
                example='patient-123'
            ),
            'uuid': FHIRMapping(
                source_field='uuid',
                fhir_path='Resource.id',
                fhir_type='id',
                confidence=0.8,
                description='Resource identifier',
                example='550e8400-e29b-41d4-a716-446655440000'
            ),
        }
        
        # Combine all mappings
        mappings.update(patient_mappings)
        mappings.update(address_mappings)
        mappings.update(metadata_mappings)
        mappings.update(identifier_mappings)
        
        return mappings
    
    def get_mapping(self, field_name: str) -> Optional[FHIRMapping]:
        """Get FHIR mapping for a field name."""
        # Normalize field name
        normalized = field_name.lower().replace('-', '_')
        
        # Check custom mappings first
        if normalized in self.custom_mappings:
            return self.custom_mappings[normalized]
        
        # Check default mappings
        return self.mappings.get(normalized)
    
    def add_custom_mapping(self, mapping: FHIRMapping):
        """Add a custom FHIR mapping."""
        normalized = mapping.source_field.lower().replace('-', '_')
        self.custom_mappings[normalized] = mapping
        logger.info("Added custom FHIR mapping", field=mapping.source_field)
    
    def get_all_mappings(self) -> Dict[str, FHIRMapping]:
        """Get all available mappings."""
        all_mappings = self.mappings.copy()
        all_mappings.update(self.custom_mappings)
        return all_mappings


class ComplianceScorer:
    """Calculates FHIR compliance scores."""
    
    def __init__(self, mapping_dict: FHIRMappingDictionary):
        self.mapping_dict = mapping_dict
    
    def calculate_compliance_score(self, fields: List[FieldInfo]) -> ComplianceScore:
        """Calculate overall compliance score."""
        total_fields = len(fields)
        if total_fields == 0:
            return ComplianceScore(
                overall_score=0.0,
                category_scores={},
                total_fields=0,
                compliant_fields=0,
                recommendations_count=0
            )
        
        compliant_fields = 0
        category_scores = {
            'patient_data': 0.0,
            'address_data': 0.0,
            'metadata': 0.0,
            'identifiers': 0.0
        }
        category_counts = {
            'patient_data': 0,
            'address_data': 0,
            'metadata': 0,
            'identifiers': 0
        }
        
        for field in fields:
            mapping = self.mapping_dict.get_mapping(field.name)
            if mapping:
                compliant_fields += 1
                
                # Categorize field
                category = self._categorize_field(mapping)
                if category in category_counts:
                    category_counts[category] += 1
                    category_scores[category] += mapping.confidence
        
        # Calculate category scores
        for category in category_scores:
            if category_counts[category] > 0:
                category_scores[category] = (category_scores[category] / category_counts[category]) * 100
        
        # Calculate overall score
        overall_score = (compliant_fields / total_fields) * 100
        
        return ComplianceScore(
            overall_score=overall_score,
            category_scores=category_scores,
            total_fields=total_fields,
            compliant_fields=compliant_fields,
            recommendations_count=total_fields - compliant_fields
        )
    
    def _categorize_field(self, mapping: FHIRMapping) -> str:
        """Categorize a FHIR mapping."""
        fhir_path = mapping.fhir_path.lower()
        
        if 'patient.name' in fhir_path or 'patient.gender' in fhir_path or 'patient.birthdate' in fhir_path:
            return 'patient_data'
        elif 'address' in fhir_path:
            return 'address_data'
        elif 'meta' in fhir_path:
            return 'metadata'
        elif 'id' in fhir_path or 'identifier' in fhir_path:
            return 'identifiers'
        else:
            return 'other'


class FHIRMapper:
    """FHIR compliance mapper and recommendation engine."""
    
    def __init__(self, custom_mappings_file: Optional[str] = None):
        self.mapping_dict = FHIRMappingDictionary()
        self.scorer = ComplianceScorer(self.mapping_dict)
        
        if custom_mappings_file and os.path.exists(custom_mappings_file):
            self._load_custom_mappings(custom_mappings_file)
    
    def _load_custom_mappings(self, file_path: str):
        """Load custom mappings from file."""
        try:
            with open(file_path, 'r') as f:
                custom_data = json.load(f)
            
            for field_name, mapping_data in custom_data.items():
                mapping = FHIRMapping(
                    source_field=field_name,
                    fhir_path=mapping_data['fhir_path'],
                    fhir_type=mapping_data['fhir_type'],
                    confidence=mapping_data.get('confidence', 1.0),
                    description=mapping_data.get('description', ''),
                    example=mapping_data.get('example')
                )
                self.mapping_dict.add_custom_mapping(mapping)
            
            logger.info("Loaded custom FHIR mappings", file=file_path)
        
        except Exception as e:
            logger.error("Failed to load custom mappings", file=file_path, error=str(e))
    
    async def generate_recommendations(self, consistency_report: ConsistencyReport) -> List[FHIRRecommendation]:
        """Generate FHIR compliance recommendations."""
        logger.info("Generating FHIR recommendations")
        
        recommendations = []
        
        # Extract all fields from consistency issues
        all_fields = []
        for issue in consistency_report.issues:
            all_fields.extend(issue.affected_fields)
        
        # Group fields by normalized name
        field_groups = self._group_fields_by_concept(all_fields)
        
        # Generate recommendations for each group
        for concept, fields in field_groups.items():
            recommendation = self._create_recommendation(concept, fields)
            if recommendation:
                recommendations.append(recommendation)
        
        logger.info("Generated FHIR recommendations", count=len(recommendations))
        return recommendations
    
    def _group_fields_by_concept(self, fields: List[FieldInfo]) -> Dict[str, List[FieldInfo]]:
        """Group fields by conceptual similarity."""
        groups = {}
        
        for field in fields:
            # Try to find FHIR mapping
            mapping = self.mapping_dict.get_mapping(field.name)
            if mapping:
                concept = mapping.fhir_path
            else:
                # Use normalized field name as concept
                concept = field.name.lower().replace('-', '_')
            
            if concept not in groups:
                groups[concept] = []
            groups[concept].append(field)
        
        return groups
    
    def _create_recommendation(self, concept: str, fields: List[FieldInfo]) -> Optional[FHIRRecommendation]:
        """Create a FHIR recommendation for a group of fields."""
        if len(fields) < 2:
            return None
        
        # Find the best FHIR mapping
        best_mapping = None
        best_confidence = 0.0
        
        for field in fields:
            mapping = self.mapping_dict.get_mapping(field.name)
            if mapping and mapping.confidence > best_confidence:
                best_mapping = mapping
                best_confidence = mapping.confidence
        
        if not best_mapping:
            return None
        
        # Determine impact level
        services_affected = list(set(f.service for f in fields))
        impact_level = self._determine_impact_level(len(services_affected), len(fields))
        
        # Create recommendation
        current_usage = list(set(f.name for f in fields))
        
        return FHIRRecommendation(
            recommendation_id=f"fhir_{concept.replace('.', '_')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            field_name=concept,
            current_usage=current_usage,
            recommended_name=self._suggest_field_name(best_mapping),
            fhir_mapping=best_mapping,
            impact_level=impact_level,
            services_affected=services_affected,
            implementation_notes=self._generate_implementation_notes(best_mapping, fields)
        )
    
    def _determine_impact_level(self, service_count: int, field_count: int) -> str:
        """Determine the impact level of a recommendation."""
        if service_count >= 5 or field_count >= 10:
            return "high"
        elif service_count >= 3 or field_count >= 5:
            return "medium"
        else:
            return "low"
    
    def _suggest_field_name(self, mapping: FHIRMapping) -> str:
        """Suggest a standardized field name based on FHIR mapping."""
        # Extract the last part of the FHIR path as the suggested name
        path_parts = mapping.fhir_path.split('.')
        if len(path_parts) > 1:
            return path_parts[-1].lower()
        return mapping.source_field
    
    def _generate_implementation_notes(self, mapping: FHIRMapping, fields: List[FieldInfo]) -> str:
        """Generate implementation notes for a recommendation."""
        notes = []
        
        notes.append(f"Standardize to FHIR path: {mapping.fhir_path}")
        notes.append(f"Expected type: {mapping.fhir_type}")
        
        if mapping.example:
            notes.append(f"Example value: {mapping.example}")
        
        # Check for type inconsistencies
        types = set(f.type for f in fields)
        if len(types) > 1:
            notes.append(f"Current types vary: {', '.join(types)}. Consider standardizing to {mapping.fhir_type}")
        
        # Check for required field inconsistencies
        required_count = sum(1 for f in fields if f.required)
        if 0 < required_count < len(fields):
            notes.append("Consider making this field consistently required or optional across all services")
        
        return "; ".join(notes)
    
    async def calculate_compliance_score(self, fields: List[FieldInfo]) -> ComplianceScore:
        """Calculate FHIR compliance score for a set of fields."""
        return self.scorer.calculate_compliance_score(fields)
    
    async def validate_fhir_compliance(self, field_info: FieldInfo) -> Dict:
        """Validate FHIR compliance for a single field."""
        mapping = self.mapping_dict.get_mapping(field_info.name)
        
        if not mapping:
            return {
                "compliant": False,
                "confidence": 0.0,
                "issues": ["No FHIR mapping found"],
                "recommendations": ["Consider adding a custom FHIR mapping"]
            }
        
        issues = []
        recommendations = []
        
        # Check type compatibility
        if field_info.type != mapping.fhir_type:
            issues.append(f"Type mismatch: expected {mapping.fhir_type}, got {field_info.type}")
            recommendations.append(f"Consider changing type to {mapping.fhir_type}")
        
        return {
            "compliant": len(issues) == 0,
            "confidence": mapping.confidence,
            "fhir_path": mapping.fhir_path,
            "issues": issues,
            "recommendations": recommendations,
            "mapping": {
                "fhir_path": mapping.fhir_path,
                "fhir_type": mapping.fhir_type,
                "description": mapping.description,
                "example": mapping.example
            }
        }
    
    def export_mappings(self, file_path: str):
        """Export current mappings to a file."""
        all_mappings = self.mapping_dict.get_all_mappings()
        
        export_data = {}
        for field_name, mapping in all_mappings.items():
            export_data[field_name] = {
                "fhir_path": mapping.fhir_path,
                "fhir_type": mapping.fhir_type,
                "confidence": mapping.confidence,
                "description": mapping.description,
                "example": mapping.example
            }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info("Exported FHIR mappings", file=file_path, count=len(export_data))