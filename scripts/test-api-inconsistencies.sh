#!/bin/bash

# Test script to demonstrate API inconsistencies between Legacy and Modern services
# This script will call both services and show the differences

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_inconsistency() {
    echo -e "${CYAN}[INCONSISTENCY]${NC} $1"
}

check_services() {
    log_info "Checking if services are running..."
    
    # Check Legacy Service
    if curl -s http://localhost:8081/actuator/health > /dev/null; then
        log_success "Legacy Donor Service is running on port 8081"
    else
        log_error "Legacy Donor Service is not running. Please start with: docker-compose up -d"
        exit 1
    fi
    
    # Check Modern Service
    if curl -s http://localhost:8082/actuator/health > /dev/null; then
        log_success "Modern FHIR Donor Service is running on port 8082"
    else
        log_error "Modern FHIR Donor Service is not running. Please start with: docker-compose up -d"
        exit 1
    fi
}

test_field_naming_inconsistencies() {
    echo ""
    log_info "=== TESTING FIELD NAMING INCONSISTENCIES ==="
    
    log_info "Fetching donor from Legacy Service..."
    legacy_response=$(curl -s http://localhost:8081/api/v1/donors/D001)
    
    log_info "Fetching patient from Modern FHIR Service..."
    modern_response=$(curl -s http://localhost:8082/api/fhir/r4/Patient/patient-001)
    
    echo ""
    log_inconsistency "1. DONOR IDENTIFICATION:"
    echo "Legacy: 'donorId' → $(echo $legacy_response | jq -r '.donorId // "null"')"
    echo "Modern: 'identifier' → $(echo $modern_response | jq -r '.identifier // "null"')"
    
    echo ""
    log_inconsistency "2. NAME FIELDS:"
    echo "Legacy: 'firstName' → $(echo $legacy_response | jq -r '.firstName // "null"')"
    echo "Legacy: 'lastName' → $(echo $legacy_response | jq -r '.lastName // "null"')"
    echo "Modern: 'name.given' → $(echo $modern_response | jq -r '.name[0].given[0] // "null"')"
    echo "Modern: 'name.family' → $(echo $modern_response | jq -r '.name[0].family // "null"')"
    
    echo ""
    log_inconsistency "3. CONTACT INFORMATION:"
    echo "Legacy: 'phoneNumber' → $(echo $legacy_response | jq -r '.phoneNumber // "null"')"
    echo "Legacy: 'email' → $(echo $legacy_response | jq -r '.email // "null"')"
    echo "Modern: 'telecom[phone].value' → $(echo $modern_response | jq -r '.telecom[] | select(.system=="phone") | .value // "null"')"
    echo "Modern: 'telecom[email].value' → $(echo $modern_response | jq -r '.telecom[] | select(.system=="email") | .value // "null"')"
    
    echo ""
    log_inconsistency "4. ADDRESS FIELDS:"
    echo "Legacy: 'zip' (integer) → $(echo $legacy_response | jq -r '.zip // "null"')"
    echo "Modern: 'address.postalCode' (string) → $(echo $modern_response | jq -r '.address[0].postalCode // "null"')"
    
    echo ""
    log_inconsistency "5. TEMPORAL FIELDS:"
    echo "Legacy: 'createdDate' → $(echo $legacy_response | jq -r '.createdDate // "null"')"
    echo "Modern: 'meta.lastUpdated' → $(echo $modern_response | jq -r '.meta.lastUpdated // "null"')"
}

test_data_type_inconsistencies() {
    echo ""
    log_info "=== TESTING DATA TYPE INCONSISTENCIES ==="
    
    log_info "Analyzing data types from OpenAPI specs..."
    
    # Get OpenAPI specs
    legacy_spec=$(curl -s http://localhost:8081/v3/api-docs)
    modern_spec=$(curl -s http://localhost:8082/v3/api-docs)
    
    echo ""
    log_inconsistency "1. POSTAL CODE TYPE MISMATCH:"
    legacy_zip_type=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.zip.type // "unknown"')
    modern_postal_type=$(echo $modern_spec | jq -r '.components.schemas.FhirPatient.properties.address.items.properties.postalCode.type // "unknown"')
    echo "Legacy 'zip': $legacy_zip_type (with min/max validation)"
    echo "Modern 'postalCode': $modern_postal_type (with pattern validation)"
    
    echo ""
    log_inconsistency "2. BIRTH DATE TYPE MISMATCH:"
    legacy_birth_type=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.birthDate.type // "unknown"')
    modern_birth_type=$(echo $modern_spec | jq -r '.components.schemas.FhirPatient.properties.birthDate.type // "unknown"')
    echo "Legacy 'birthDate': $legacy_birth_type (with pattern validation)"
    echo "Modern 'birthDate': $modern_birth_type (LocalDate)"
    
    echo ""
    log_inconsistency "3. TIMESTAMP TYPE MISMATCH:"
    legacy_created_type=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.createdDate.type // "unknown"')
    modern_meta_type=$(echo $modern_spec | jq -r '.components.schemas.Meta.properties.lastUpdated.type // "unknown"')
    echo "Legacy 'createdDate': $legacy_created_type (LocalDateTime)"
    echo "Modern 'meta.lastUpdated': $modern_meta_type (Instant)"
}

test_validation_patterns() {
    echo ""
    log_info "=== TESTING VALIDATION PATTERN DIFFERENCES ==="
    
    legacy_spec=$(curl -s http://localhost:8081/v3/api-docs)
    modern_spec=$(curl -s http://localhost:8082/v3/api-docs)
    
    echo ""
    log_inconsistency "1. PHONE NUMBER VALIDATION:"
    legacy_phone_pattern=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.phoneNumber.pattern // "none"')
    echo "Legacy: Pattern validation '$legacy_phone_pattern'"
    echo "Modern: Structured ContactPoint with system/value"
    
    echo ""
    log_inconsistency "2. POSTAL CODE VALIDATION:"
    legacy_zip_min=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.zip.minimum // "none"')
    legacy_zip_max=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.zip.maximum // "none"')
    modern_postal_pattern=$(echo $modern_spec | jq -r '.components.schemas.Address.properties.postalCode.pattern // "none"')
    echo "Legacy: Integer with min=$legacy_zip_min, max=$legacy_zip_max"
    echo "Modern: String with pattern '$modern_postal_pattern'"
    
    echo ""
    log_inconsistency "3. GENDER VALIDATION:"
    legacy_gender_pattern=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.properties.gender.pattern // "none"')
    modern_gender_enum=$(echo $modern_spec | jq -r '.components.schemas.FhirPatient.properties.gender.pattern // "none"')
    echo "Legacy: Pattern '$legacy_gender_pattern' (M/F only)"
    echo "Modern: FHIR codes 'male|female|other|unknown'"
}

test_required_optional_differences() {
    echo ""
    log_info "=== TESTING REQUIRED/OPTIONAL FIELD DIFFERENCES ==="
    
    legacy_spec=$(curl -s http://localhost:8081/v3/api-docs)
    modern_spec=$(curl -s http://localhost:8082/v3/api-docs)
    
    echo ""
    log_inconsistency "FIELD REQUIREMENT DIFFERENCES:"
    
    # Legacy required fields
    legacy_required=$(echo $legacy_spec | jq -r '.components.schemas.LegacyDonor.required[]?' | tr '\n' ', ' | sed 's/,$//')
    echo "Legacy Required: [$legacy_required]"
    
    # Modern required fields
    modern_required=$(echo $modern_spec | jq -r '.components.schemas.FhirPatient.required[]?' | tr '\n' ', ' | sed 's/,$//')
    echo "Modern Required: [$modern_required]"
    
    echo ""
    echo "Key Differences:"
    echo "- Legacy requires 'phoneNumber', Modern has optional 'telecom'"
    echo "- Legacy requires 'zip' (integer), Modern requires 'address.postalCode' (string)"
    echo "- Legacy has optional 'email', Modern structures all contact in 'telecom'"
}

test_api_endpoint_patterns() {
    echo ""
    log_info "=== TESTING API ENDPOINT PATTERN DIFFERENCES ==="
    
    echo ""
    log_inconsistency "ENDPOINT STRUCTURE COMPARISON:"
    echo "Legacy REST Patterns:"
    echo "  GET    /api/v1/donors"
    echo "  POST   /api/v1/donors"
    echo "  GET    /api/v1/donors/{donorId}"
    echo "  PUT    /api/v1/donors/{donorId}"
    echo "  DELETE /api/v1/donors/{donorId}"
    echo "  GET    /api/v1/donors/{donorId}/eligibility"
    echo "  GET    /api/v1/donors/search/phone/{phoneNumber}"
    
    echo ""
    echo "Modern FHIR Patterns:"
    echo "  GET    /api/fhir/r4/Patient"
    echo "  POST   /api/fhir/r4/Patient"
    echo "  GET    /api/fhir/r4/Patient/{id}"
    echo "  PUT    /api/fhir/r4/Patient/{id}"
    echo "  DELETE /api/fhir/r4/Patient/{id}"
    echo "  GET    /api/fhir/r4/Patient/{id}/\$eligibility"
    
    echo ""
    log_inconsistency "RESPONSE FORMAT DIFFERENCES:"
    echo "Legacy: Returns simple arrays and objects"
    echo "Modern: Returns FHIR Bundle for collections with metadata"
}

test_openapi_schema_variations() {
    echo ""
    log_info "=== TESTING OPENAPI SCHEMA VARIATIONS ==="
    
    legacy_spec=$(curl -s http://localhost:8081/v3/api-docs)
    modern_spec=$(curl -s http://localhost:8082/v3/api-docs)
    
    echo ""
    log_inconsistency "SCHEMA COMPLEXITY COMPARISON:"
    
    # Count properties in main schemas
    legacy_props=$(echo $legacy_spec | jq '.components.schemas.LegacyDonor.properties | length')
    modern_props=$(echo $modern_spec | jq '.components.schemas.FhirPatient.properties | length')
    
    echo "Legacy Schema Properties: $legacy_props (flat structure)"
    echo "Modern Schema Properties: $modern_props (nested FHIR structure)"
    
    echo ""
    echo "Legacy Schema: Simple flat fields"
    echo "Modern Schema: Complex nested structures with:"
    echo "  - HumanName (use, family, given[])"
    echo "  - ContactPoint[] (system, value, use)"
    echo "  - Address[] (use, line[], city, state, postalCode)"
    echo "  - Meta (lastUpdated, versionId)"
    echo "  - Extensions (bloodType, donorStatus)"
}

run_governance_analysis() {
    echo ""
    log_info "=== RUNNING API GOVERNANCE ANALYSIS ==="
    
    log_info "Triggering API Governance Platform analysis..."
    
    # Trigger harvest
    governance_response=$(curl -s -X POST http://localhost:8080/api/v1/harvest/trigger \
        -H "Content-Type: application/json" \
        -d '{"force": true}')
    
    if [ $? -eq 0 ]; then
        log_success "Governance analysis triggered successfully"
        echo "Response: $governance_response"
        
        echo ""
        log_info "Waiting for analysis to complete..."
        sleep 5
        
        # Get latest report
        log_info "Fetching consistency report..."
        report=$(curl -s http://localhost:8080/api/v1/reports/latest)
        
        if [ $? -eq 0 ]; then
            echo ""
            log_success "CONSISTENCY ANALYSIS RESULTS:"
            echo $report | jq '.summary'
            
            echo ""
            log_info "Sample Issues Found:"
            echo $report | jq -r '.issues[0:3][] | "- \(.title): \(.description)"'
        else
            log_warning "Could not fetch consistency report"
        fi
        
        # Get FHIR recommendations
        echo ""
        log_info "Fetching FHIR recommendations..."
        fhir_recs=$(curl -s http://localhost:8080/api/v1/fhir/recommendations)
        
        if [ $? -eq 0 ]; then
            echo ""
            log_success "FHIR COMPLIANCE RECOMMENDATIONS:"
            echo $fhir_recs | jq -r '.[] | "- \(.field_name): \(.recommended_name) (\(.impact_level) impact)"'
        else
            log_warning "Could not fetch FHIR recommendations"
        fi
        
    else
        log_error "Failed to trigger governance analysis"
    fi
}

generate_summary_report() {
    echo ""
    echo "========================================"
    log_info "API INCONSISTENCY TEST SUMMARY"
    echo "========================================"
    
    echo ""
    echo "✅ INCONSISTENCIES SUCCESSFULLY DEMONSTRATED:"
    echo ""
    echo "1. Field Naming Inconsistencies (8 violations):"
    echo "   - donorId → identifier"
    echo "   - firstName/lastName → name.given/name.family"
    echo "   - phoneNumber/email → telecom.value"
    echo "   - zip → address.postalCode"
    echo "   - createdDate → meta.lastUpdated"
    echo ""
    echo "2. Data Type Inconsistencies (3 violations):"
    echo "   - zip: Integer → String postalCode"
    echo "   - birthDate: String → LocalDate"
    echo "   - createdDate: LocalDateTime → Instant"
    echo ""
    echo "3. Required/Optional Variations:"
    echo "   - phoneNumber: Required → Optional telecom"
    echo "   - email: Optional → Structured telecom"
    echo "   - zip: Required Integer → Required String postalCode"
    echo ""
    echo "4. Validation Pattern Differences:"
    echo "   - Phone: \\d{10} → Structured ContactPoint"
    echo "   - Postal: min/max Integer → \\d{5} String pattern"
    echo "   - Gender: [MF] → FHIR codes"
    echo ""
    echo "5. API Endpoint Pattern Differences:"
    echo "   - Legacy REST → FHIR REST patterns"
    echo "   - Simple responses → FHIR Bundle collections"
    echo ""
    echo "6. OpenAPI Schema Variations:"
    echo "   - Flat structure → Nested FHIR structure"
    echo "   - Simple validation → Complex FHIR validation"
    echo ""
    echo "🎯 The API Governance Platform should detect and report all these inconsistencies!"
}

main() {
    echo "========================================"
    log_info "ARC ONE BLOOD BANKING API INCONSISTENCY TESTER"
    echo "========================================"
    
    # Check if services are running
    check_services
    
    # Run all tests
    test_field_naming_inconsistencies
    test_data_type_inconsistencies
    test_validation_patterns
    test_required_optional_differences
    test_api_endpoint_patterns
    test_openapi_schema_variations
    
    # Run governance analysis
    run_governance_analysis
    
    # Generate summary
    generate_summary_report
    
    echo ""
    log_success "API Inconsistency testing completed!"
    echo ""
    log_info "Next steps:"
    echo "1. Check the API Governance Platform dashboard: http://localhost:8080/health/status"
    echo "2. View detailed reports: http://localhost:8080/api/v1/reports/latest"
    echo "3. Review FHIR recommendations: http://localhost:8080/api/v1/fhir/recommendations"
    echo "4. Access service documentation:"
    echo "   - Legacy Service: http://localhost:8081/swagger-ui.html"
    echo "   - Modern Service: http://localhost:8082/swagger-ui.html"
}

# Run main function
main "$@"