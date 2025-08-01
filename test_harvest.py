#!/usr/bin/env python3
"""Simple test script to bypass metrics and test harvest directly."""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from src.core.istio_discovery import IstioServiceDiscovery
from src.core.api_harvester import APIHarvester

async def test_harvest():
    """Test the harvest process directly."""
    print("🔍 Testing API harvest process...")
    
    # Initialize discovery
    discovery = IstioServiceDiscovery()
    
    # Discover services
    print("📡 Discovering services...")
    services = await discovery.discover_services()
    print(f"✅ Found {len(services)} services:")
    for service in services:
        print(f"  - {service.name} in {service.namespace}")
        print(f"    OpenAPI: {service.openapi_endpoint}")
    
    # Initialize harvester
    harvester = APIHarvester(discovery)
    
    # Test direct API calls to services
    print("\n🌐 Testing direct API access...")
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        for service in services:
            if service.openapi_endpoint:
                try:
                    # Try to access the OpenAPI endpoint directly
                    url = service.openapi_endpoint.replace(
                        "svc.cluster.local", 
                        "localhost"
                    ).replace(":8081", ":8081").replace(":8082", ":8082")
                    
                    print(f"  📋 Fetching spec from {url}")
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            spec_data = await response.json()
                            print(f"    ✅ Success! Title: {spec_data.get('info', {}).get('title', 'Unknown')}")
                            
                            # Save spec to file for analysis
                            filename = f"{service.name}_spec.json"
                            with open(filename, 'w') as f:
                                json.dump(spec_data, f, indent=2)
                            print(f"    💾 Saved to {filename}")
                        else:
                            print(f"    ❌ Failed with status {response.status}")
                except Exception as e:
                    print(f"    ❌ Error: {e}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_harvest())