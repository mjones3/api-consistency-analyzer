# API Consistency Report

**Report ID:** consistency_20240101_120000
**Generated:** 2024-01-01T12:00:00Z
**Specs Analyzed:** 5
**Total Fields:** 127

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| Major | 8 |
| Minor | 15 |
| Info | 3 |

## Issues

### Inconsistent naming for given_name

**Severity:** Major
**Category:** naming_inconsistency
**Description:** Field 'firstName' in user-service and 'first_name' in order-service represent the same concept but use different names
**Recommendation:** Consider standardizing to a common name like 'given_name'

**Affected Fields:**
- `firstName` (string) in user-service.default
- `first_name` (string) in order-service.default
- `givenName` (string) in patient-service.healthcare

### Type mismatch for postal_code

**Severity:** Critical
**Category:** type_inconsistency
**Description:** Field 'zipCode' has type 'string' in user-service but type 'integer' in address-service
**Recommendation:** Ensure consistent data types across services

**Affected Fields:**
- `zipCode` (string) in user-service.default
- `zip` (integer) in address-service.default

### Mixed naming conventions in payment-service

**Severity:** Minor
**Category:** naming
**Description:** Service payment-service uses multiple naming conventions: camelCase, snake_case
**Recommendation:** Use a consistent naming convention throughout the service

**Affected Fields:**
- `paymentId` (string) in payment-service.default
- `payment_method` (string) in payment-service.default
- `created_at` (string) in payment-service.default

### Required field inconsistency for phone_number

**Severity:** Major
**Category:** validation
**Description:** Field phone_number is required in some services but optional in others
**Recommendation:** Ensure consistent required/optional status across services

**Affected Fields:**
- `phoneNumber` (string) in user-service.default
- `phone` (string) in contact-service.default
- `telephone` (string) in customer-service.crm