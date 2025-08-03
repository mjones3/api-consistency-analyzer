# Arc One Blood Banking API Inconsistency Catalog

This document catalogs all the API inconsistencies implemented in the Legacy and Modern donor services for testing the API Governance Platform.

## Overview

The two services simulate a real-world scenario where Arc One Blood Banking has:
- **Legacy Donor Service**: An older system with non-FHIR field names and inconsistent patterns
- **Modern Donor Service**: A new FHIR R4 compliant system following HL7 standards

## 1. Field Naming Inconsistencies (8 violations)

### 1.1 Donor/Patient Identification
| Legacy Service | Modern Service (FHIR) | Issue |
|----------------|----------------------|-------|
| `donorId` | `identifier` | Different field names for the same concept |

**Example:**
```json
// Legacy
{"donorId": "D001"}

// Modern
{"identifier": "patient-001"}
```

### 1.2 Name Fields
| Legacy Service | Modern Service (FHIR) | Issue |
|----------------|----------------------|-------|
| `firstName` | `name.given[]` | Flat vs nested structure |
| `lastName` | `name.family` | Flat vs nested structure |

**Example:**
```json
// Legacy
{
  "firstName": "John",
  "lastName": "Smith"
}

// Modern
{
  "name": [{
    "use": "official",
    "family": "Smith",
    "given": ["John", "Michael"]
  }]
}
```

### 1.3 Contact Information
| Legacy Service | Modern Service (FHIR) | Issue |
|----------------|----------------------|-------|
| `phoneNumber` | `telecom.value` | Different structure and naming |
| `email` | `telecom.value` | Different structure and naming |

**Example:**
```json
// Legacy
{
  "phoneNumber": "5551234567",
  "email": "john@email.com"
}

// Modern
{
  "telecom": [
    {
      "system": "phone",
      "value": "5551234567",
      "use": "home"
    },
    {
      "system": "email", 
      "value": "john@email.com",
      "use": "home"
    }
  ]
}
```

### 1.4 Address Fields
| Legacy Service | Modern Service (FHIR) | Issue |
|----------------|----------------------|-------|
| `zip` | `address.postalCode` | Different naming and structure |
| `streetAddress` | `address.line[]` | Different structure |
| `city` | `address.city` | Same name, different nesting |
| `state` | `address.state` | Same name, different nesting |

### 1.5 Temporal Fields
| Legacy Service | Modern Service (FHIR) | Issue |
|----------------|----------------------|-------|
| `createdDate` | `meta.lastUpdated` | Different naming and purpose |

## 2. Data Type Inconsistencies (3 violations)

### 2.1 Postal Code Type Mismatch
| Legacy Service | Modern Service | Issue |
|----------------|----------------|-------|
| `Integer zip` (12345) | `String postalCode` ("12345") | Type incompatibility |

**Validation Differences:**
```yaml
# Legacy
zip:
  type: integer
  minimum: 10001
  maximum: 99999

# Modern  
postalCode:
  type: string
  pattern: "\\d{5}(-\\d{4})?"
```

### 2.2 Birth Date Type Mismatch
| Legacy Service | Modern Service | Issue |
|----------------|----------------|-------|
| `String birthDate` ("1985-06-15") | `LocalDate birthDate` (1985-06-15) | Type and format differences |

### 2.3 Timestamp Type Mismatch
| Legacy Service | Modern Service | Issue |
|----------------|----------------|-------|
| `LocalDateTime createdDate` | `Instant meta.lastUpdated` | Different temporal types |

## 3. Required vs Optional Field Variations

### 3.1 Contact Information Requirements
| Field | Legacy Service | Modern Service | Issue |
|-------|----------------|----------------|-------|
| Phone | Required `phoneNumber` | Optional `telecom` | Requirement inconsistency |
| Email | Optional `email` | Optional `telecom` | Structure difference |

### 3.2 Address Requirements
| Field | Legacy Service | Modern Service | Issue |
|-------|----------------|----------------|-------|
| Postal Code | Required `zip` (Integer) | Required `address.postalCode` (String) | Type and structure difference |

## 4. Validation Pattern Differences

### 4.1 Phone Number Validation
```java
// Legacy: Simple regex pattern
@Pattern(regexp = "\\d{10}")
private String phoneNumber;

// Modern: Structured with system/value
public static class ContactPoint {
    private String system; // "phone", "email", etc.
    private String value;  // actual contact value
    private String use;    // "home", "work", etc.
}
```

### 4.2 Postal Code Validation
```java
// Legacy: Integer with min/max
@Min(10001) @Max(99999)
private Integer zip;

// Modern: String with pattern
@Pattern(regexp = "\\d{5}(-\\d{4})?")
private String postalCode;
```

### 4.3 Gender Validation
```java
// Legacy: Simple M/F pattern
@Pattern(regexp = "[MF]")
private String gender;

// Modern: FHIR standard codes
@Pattern(regexp = "male|female|other|unknown")
private String gender;
```

## 5. OpenAPI Schema Variations

### 5.1 Schema Complexity
| Aspect | Legacy Service | Modern Service |
|--------|----------------|----------------|
| Structure | Flat fields | Nested FHIR structure |
| Properties | ~15 simple properties | ~8 complex nested properties |
| Validation | Basic annotations | Complex FHIR validation |
| Response Format | Simple objects/arrays | FHIR Bundle collections |

### 5.2 Documentation Differences
```yaml
# Legacy OpenAPI
LegacyDonor:
  type: object
  properties:
    donorId:
      type: string
      description: "Legacy donor identifier"
    firstName:
      type: string
      description: "Donor first name"

# Modern OpenAPI  
FhirPatient:
  type: object
  properties:
    resourceType:
      type: string
      example: "Patient"
    identifier:
      type: string
      description: "Logical id of this artifact"
    name:
      type: array
      items:
        $ref: "#/components/schemas/HumanName"
```

## 6. API Endpoint Pattern Differences

### 6.1 REST Patterns
| Operation | Legacy Service | Modern Service |
|-----------|----------------|----------------|
| List | `GET /api/v1/donors` | `GET /api/fhir/r4/Patient` |
| Create | `POST /api/v1/donors` | `POST /api/fhir/r4/Patient` |
| Read | `GET /api/v1/donors/{id}` | `GET /api/fhir/r4/Patient/{id}` |
| Update | `PUT /api/v1/donors/{id}` | `PUT /api/fhir/r4/Patient/{id}` |
| Delete | `DELETE /api/v1/donors/{id}` | `DELETE /api/fhir/r4/Patient/{id}` |

### 6.2 Special Operations
| Operation | Legacy Service | Modern Service |
|-----------|----------------|----------------|
| Eligibility | `GET /donors/{id}/eligibility` | `GET /Patient/{id}/$eligibility` |
| Search | `GET /donors/search/phone/{phone}` | `GET /Patient?telecom={phone}` |

### 6.3 Response Formats
```json
// Legacy: Simple array
[
  {"donorId": "D001", "firstName": "John"},
  {"donorId": "D002", "firstName": "Jane"}
]

// Modern: FHIR Bundle
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 2,
  "entry": [
    {
      "fullUrl": "Patient/patient-001",
      "resource": {"resourceType": "Patient", "identifier": "patient-001"}
    }
  ]
}
```

## 7. Blood Banking Domain Specific Issues

### 7.1 Blood Type Representation
```json
// Legacy: Simple string
{"bloodType": "O+"}

// Modern: Structured extension
{
  "bloodType": {
    "aboGroup": "O",
    "rhFactor": "+"
  }
}
```

### 7.2 Donor Status
```json
// Legacy: Simple status string
{"status": "ACTIVE"}

// Modern: Complex extension with dates
{
  "donorStatus": {
    "status": "active",
    "lastDonationDate": "2023-12-01",
    "nextEligibleDate": "2024-01-26"
  }
}
```

## 8. Testing the API Governance Platform

### 8.1 Expected Detections
The API Governance Platform should detect and report:

1. **Field Naming Issues**: 8 different naming patterns
2. **Data Type Mismatches**: 3 critical type incompatibilities  
3. **Validation Inconsistencies**: Different validation approaches
4. **Structure Differences**: Flat vs nested field organization
5. **Requirement Mismatches**: Required vs optional field variations
6. **FHIR Compliance Gaps**: Non-standard vs FHIR-compliant patterns

### 8.2 FHIR Recommendations
The platform should recommend:

1. Standardize `donorId` → `identifier`
2. Restructure names to FHIR `name.given`/`name.family`
3. Convert contact fields to FHIR `telecom` structure
4. Standardize postal codes to string type with pattern validation
5. Use FHIR temporal fields (`meta.lastUpdated`)
6. Adopt FHIR gender codes
7. Implement FHIR Bundle responses for collections

### 8.3 Running the Tests
```bash
# Start the services
docker-compose up -d

# Run the inconsistency test
./scripts/test-api-inconsistencies.sh

# Check governance platform results
curl http://localhost:8080/api/v1/reports/latest
curl http://localhost:8080/api/v1/fhir/recommendations
```

## 9. Real-World Impact

These inconsistencies represent common challenges in healthcare API integration:

1. **Integration Complexity**: Different field names require mapping logic
2. **Data Quality Issues**: Type mismatches can cause data corruption
3. **Validation Conflicts**: Different validation rules cause integration failures
4. **Maintenance Overhead**: Multiple patterns increase development complexity
5. **Compliance Risks**: Non-FHIR patterns may not meet healthcare standards
6. **Interoperability Problems**: Inconsistent APIs hinder system integration

The API Governance Platform addresses these issues by:
- **Automatically detecting** inconsistencies across services
- **Providing FHIR-compliant recommendations** for standardization
- **Generating actionable reports** for development teams
- **Monitoring compliance** over time
- **Facilitating** gradual migration to consistent patterns