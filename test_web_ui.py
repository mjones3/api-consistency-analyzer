#!/usr/bin/env python3
"""Test script to verify web UI functionality."""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from src.core.fhir_compliance import FHIRComplianceChecker
from src.core.api_harvester import APISpec

async def test_fhir_compliance():
    """Test FHIR compliance checker with our OpenAPI specs."""
    print("🧪 Testing FHIR Compliance Checker...")
    
    # Load the legacy spec
    with open('legacy_spec.json', 'r') as f:
        legacy_spec_content = json.load(f)
    
    # Create APISpec object
    legacy_spec = APISpec(
        service_name="legacy-donor-service",
        namespace="api",
        spec_url="http://localhost:8081/v3/api-docs",
        spec_content=legacy_spec_content
    )
    
    # Initialize FHIR checker
    fhir_checker = FHIRComplianceChecker()
    
    # Analyze compliance
    print("📊 Analyzing legacy service FHIR compliance...")
    compliance_result = await fhir_checker.analyze_service_compliance(legacy_spec)
    
    print(f"✅ Compliance Score: {compliance_result['compliance_score']}%")
    print(f"📋 Total Fields: {compliance_result['total_fields']}")
    print(f"✅ Compliant Fields: {compliance_result['compliant_fields']}")
    print(f"❌ Issues Found: {len(compliance_result['issues'])}")
    
    print("\n🔍 Top Issues:")
    for i, issue in enumerate(compliance_result['issues'][:5], 1):
        print(f"  {i}. {issue.field_name}: {issue.issue_description}")
    
    # Get detailed recommendations
    print("\n💡 Getting detailed recommendations...")
    detailed_result = await fhir_checker.get_detailed_recommendations(legacy_spec)
    
    print(f"📋 Recommendations Generated: {len(detailed_result.get('recommendations', []))}")
    
    # Test with modern spec
    print("\n🔄 Testing modern service...")
    with open('modern_spec.json', 'r') as f:
        modern_spec_content = json.load(f)
    
    modern_spec = APISpec(
        service_name="modern-donor-service",
        namespace="api", 
        spec_url="http://localhost:8082/v3/api-docs",
        spec_content=modern_spec_content
    )
    
    modern_compliance = await fhir_checker.analyze_service_compliance(modern_spec)
    print(f"✅ Modern Service Compliance Score: {modern_compliance['compliance_score']}%")
    
    # Create sample data for web UI
    services_data = [
        {
            "namespace": "api",
            "service_name": "legacy-donor-service",
            "total_attributes": compliance_result['total_fields'],
            "non_compliant_attributes": compliance_result['total_fields'] - compliance_result['compliant_fields'],
            "compliance_percentage": compliance_result['compliance_score'],
            "openapi_url": "http://localhost:8081/v3/api-docs",
            "swagger_ui_url": "/swagger-ui/legacy-donor-service",
            "recommendations_url": "/recommendations/legacy-donor-service"
        },
        {
            "namespace": "api",
            "service_name": "modern-donor-service", 
            "total_attributes": modern_compliance['total_fields'],
            "non_compliant_attributes": modern_compliance['total_fields'] - modern_compliance['compliant_fields'],
            "compliance_percentage": modern_compliance['compliance_score'],
            "openapi_url": "http://localhost:8082/v3/api-docs",
            "swagger_ui_url": "/swagger-ui/modern-donor-service",
            "recommendations_url": "/recommendations/modern-donor-service"
        }
    ]
    
    # Save sample data
    with open('sample_ui_data.json', 'w') as f:
        json.dump({
            "services": services_data,
            "last_updated": "2025-08-01T21:20:00Z",
            "summary": {
                "total_services": len(services_data),
                "fully_compliant": len([s for s in services_data if s["compliance_percentage"] == 100]),
                "partially_compliant": len([s for s in services_data if 0 < s["compliance_percentage"] < 100]),
                "non_compliant": len([s for s in services_data if s["compliance_percentage"] == 0])
            }
        }, f, indent=2)
    
    print("\n✅ FHIR Compliance testing completed!")
    print("📄 Sample UI data saved to sample_ui_data.json")
    
    return services_data

if __name__ == "__main__":
    asyncio.run(test_fhir_compliance())