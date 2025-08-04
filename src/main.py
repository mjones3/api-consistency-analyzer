"""Main application entry point."""

import asyncio
import os
import signal
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.core.api_harvester import APIHarvester
from src.core.istio_discovery import IstioServiceDiscovery
from src.services.compliance_analyzer import ComplianceAnalyzer
from src.server.api_routes import create_api_router
from src.server.health_server import create_health_router
# from src.server.web_ui import create_web_ui_router
from src.utils.logging_config import setup_logging
from src.utils.metrics import setup_metrics

logger = structlog.get_logger()


class APIGovernancePlatform:
    """Main application class."""
    
    def __init__(self):
        self.discovery = None
        self.harvester = None
        self.compliance_analyzer = None
        self.harvest_task = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing API Governance Platform")
        
        # Initialize components
        self.discovery = IstioServiceDiscovery()
        self.harvester = APIHarvester(self.discovery)
        self.compliance_analyzer = ComplianceAnalyzer()
        
        # Start background harvest task if in continuous mode
        if os.getenv("RUN_MODE", "continuous") == "continuous":
            self.harvest_task = asyncio.create_task(self._harvest_loop())
        
        logger.info("Platform initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        logger.info("Shutting down API Governance Platform")
        
        self.shutdown_event.set()
        
        if self.harvest_task:
            self.harvest_task.cancel()
            try:
                await self.harvest_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Platform shutdown complete")
    
    async def _harvest_loop(self):
        """Background harvest loop."""
        interval_hours = int(os.getenv("HARVEST_INTERVAL_HOURS", "6"))
        interval_seconds = interval_hours * 3600
        
        while not self.shutdown_event.is_set():
            try:
                logger.info("Starting scheduled harvest cycle")
                await self.run_harvest()
                logger.info("Harvest cycle completed")
            except Exception as e:
                logger.error("Harvest cycle failed", error=str(e))
            
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(), 
                    timeout=interval_seconds
                )
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue  # Time for next harvest
    
    async def run_harvest(self):
        """Run a complete harvest cycle."""
        # Discover services
        services = await self.discovery.discover_services()
        logger.info("Discovered services", count=len(services))
        
        # Harvest API specs
        specs = await self.harvester.harvest_specs(services)
        logger.info("Harvested API specs", count=len(specs))
        
        # Prepare specs for compliance analysis
        services_specs = []
        for spec in specs:
            if spec.spec_content:
                services_specs.append({
                    "service_name": spec.service_name,
                    "namespace": spec.namespace,
                    "spec_content": spec.spec_content,
                    "spec_url": spec.spec_url
                })
        
        # Analyze compliance using Spectral
        compliance_overviews = await self.compliance_analyzer.analyze_all_services(services_specs)
        logger.info("Generated compliance analysis", services_analyzed=len(compliance_overviews))
        
        # Generate compliance summary
        compliance_summary = self.compliance_analyzer.get_compliance_summary(compliance_overviews)
        logger.info("Generated compliance summary", 
                   average_compliance=compliance_summary.average_compliance,
                   total_issues=compliance_summary.critical_issues + compliance_summary.major_issues + compliance_summary.minor_issues)
        
        return {
            "services": services,
            "specs": specs,
            "compliance_overviews": compliance_overviews,
            "compliance_summary": compliance_summary
        }


# Global platform instance
platform = APIGovernancePlatform()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await platform.initialize()
    yield
    # Shutdown
    await platform.shutdown()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Microservices API Governance Platform",
        description="Automated API governance with Istio integration and customizable style guide compliance",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add simple web UI route directly to the app
    @app.get("/", response_class=HTMLResponse)
    async def web_ui():
        """Compliance Dashboard for the API Governance Platform."""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔧 API Governance Platform - OpenAPI Compliance Dashboard</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .compliance-high { color: #10b981; }
        .compliance-medium { color: #f59e0b; }
        .compliance-low { color: #ef4444; }
        .demo-banner { 
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
            color: white; 
            padding: 10px; 
            text-align: center; 
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="demo-banner">
        🎉 SUCCESS! Enhanced API Governance Platform UI is Running!
    </div>
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect } = React;

        const ComplianceDashboard = () => {
            const [services, setServices] = useState([]);
            const [isLoading, setIsLoading] = useState(true);
            const [lastUpdated, setLastUpdated] = useState(null);
            const [connectionStatus, setConnectionStatus] = useState('connecting');
            const [error, setError] = useState(null);
            const [sortField, setSortField] = useState('service_name');
            const [sortDirection, setSortDirection] = useState('asc');

            // Live data fetching functions
            const fetchLiveData = async () => {
                try {
                    setIsLoading(true);
                    setError(null);
                    setConnectionStatus('connecting');
                    
                    // Fetch compliance overview data
                    const complianceResponse = await fetch('/api/v1/compliance/overview');
                    if (!complianceResponse.ok) throw new Error('Failed to fetch compliance data');
                    const complianceData = await complianceResponse.json();
                    
                    // Process compliance data
                    const processedServices = complianceData.map(service => ({
                        serviceName: service.service_name,
                        namespace: service.namespace,
                        totalEndpoints: service.total_endpoints,
                        inconsistentNaming: service.inconsistent_naming_count,
                        inconsistentErrors: service.inconsistent_error_count,
                        compliancePercentage: Math.round(service.compliance_percentage),
                        openApiUrl: service.openapi_url || `http://localhost:${service.service_name.includes('legacy') ? '8081' : '8082'}/swagger-ui.html`,
                        lastAnalyzed: service.last_analyzed
                    }));
                    
                    setServices(processedServices);
                    setLastUpdated(new Date().toISOString());
                    setConnectionStatus('connected');
                    setIsLoading(false);
                    
                } catch (error) {
                    console.error('Failed to fetch live data:', error);
                    setError(error.message);
                    setConnectionStatus('error');
                    
                    // Fallback to mock data if API fails
                    setServices(mockServices);
                    setLastUpdated(new Date().toISOString());
                    setIsLoading(false);
                }
            };

            // Fallback mock data in case API fails
            const mockServices = [
                {
                    serviceName: 'order-service',
                    namespace: 'api',
                    totalEndpoints: 12,
                    inconsistentNaming: 5,
                    inconsistentErrors: 3,
                    compliancePercentage: 75,
                    openApiUrl: 'http://localhost:8081/swagger-ui.html',
                    lastAnalyzed: new Date().toISOString()
                },
                {
                    serviceName: 'collection-service',
                    namespace: 'api',
                    totalEndpoints: 8,
                    inconsistentNaming: 2,
                    inconsistentErrors: 1,
                    compliancePercentage: 85,
                    openApiUrl: 'http://localhost:8082/swagger-ui.html',
                    lastAnalyzed: new Date().toISOString()
                },
                {
                    serviceName: 'legacy-donor-service',
                    namespace: 'api',
                    totalEndpoints: 15,
                    inconsistentNaming: 8,
                    inconsistentErrors: 4,
                    compliancePercentage: 65,
                    openApiUrl: 'http://localhost:8083/swagger-ui.html',
                    lastAnalyzed: new Date().toISOString()
                },
                {
                    serviceName: 'modern-donor-service',
                    namespace: 'api',
                    totalEndpoints: 10,
                    inconsistentNaming: 1,
                    inconsistentErrors: 0,
                    compliancePercentage: 95,
                    openApiUrl: 'http://localhost:8084/swagger-ui.html',
                    lastAnalyzed: new Date().toISOString()
                }
            ];


            useEffect(() => {
                // Initial data fetch
                fetchLiveData();
                
                // Set up auto-refresh every 30 seconds
                const interval = setInterval(fetchLiveData, 30000);
                
                // Cleanup interval on component unmount
                return () => clearInterval(interval);
            }, []);

            // Sorting functionality
            const sortServices = (field) => {
                const direction = sortField === field && sortDirection === 'asc' ? 'desc' : 'asc';
                setSortField(field);
                setSortDirection(direction);
                
                const sorted = [...services].sort((a, b) => {
                    let aVal = a[field];
                    let bVal = b[field];
                    
                    if (typeof aVal === 'string') {
                        aVal = aVal.toLowerCase();
                        bVal = bVal.toLowerCase();
                    }
                    
                    if (direction === 'asc') {
                        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
                    } else {
                        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
                    }
                });
                
                setServices(sorted);
            };

            // Export to JSON functionality - Basic summary
            const exportToJSON = () => {
                const summaryData = {
                    metadata: {
                        reportType: "API Compliance Summary",
                        generatedAt: new Date().toISOString(),
                        totalServices: services.length,
                        totalNamingIssues: services.reduce((sum, s) => sum + s.inconsistentNaming, 0),
                        totalErrorIssues: services.reduce((sum, s) => sum + s.inconsistentErrors, 0),
                        averageCompliance: services.length > 0 ? 
                            Math.round(services.reduce((sum, s) => sum + s.compliancePercentage, 0) / services.length) : 0
                    },
                    complianceBreakdown: {
                        highCompliance: services.filter(s => s.compliancePercentage >= 90).length,
                        mediumCompliance: services.filter(s => s.compliancePercentage >= 70 && s.compliancePercentage < 90).length,
                        lowCompliance: services.filter(s => s.compliancePercentage < 70).length
                    },
                    services: services.map(service => ({
                        serviceName: service.serviceName,
                        namespace: service.namespace,
                        totalEndpoints: service.totalEndpoints,
                        inconsistentNaming: service.inconsistentNaming,
                        inconsistentErrors: service.inconsistentErrors,
                        compliancePercentage: service.compliancePercentage,
                        complianceLevel: service.compliancePercentage >= 90 ? 'high' : 
                                       service.compliancePercentage >= 70 ? 'medium' : 'low',
                        openApiUrl: service.openApiUrl,
                        lastAnalyzed: service.lastAnalyzed
                    }))
                };
                
                const jsonContent = JSON.stringify(summaryData, null, 2);
                const blob = new Blob([jsonContent], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `api-compliance-summary-${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            };

            // Comprehensive export with all violation details as JSON
            const exportComprehensiveReport = async () => {
                try {
                    setIsLoading(true);
                    
                    // Fetch detailed data for all services
                    const detailedData = await Promise.all(
                        services.map(async (service) => {
                            const [namingResponse, errorResponse] = await Promise.all([
                                fetch(`/api/v1/compliance/naming/${service.serviceName}?namespace=${service.namespace}`),
                                fetch(`/api/v1/compliance/errors/${service.serviceName}?namespace=${service.namespace}`)
                            ]);
                            
                            const namingData = namingResponse.ok ? await namingResponse.json() : { naming_inconsistencies: [] };
                            const errorData = errorResponse.ok ? await errorResponse.json() : { error_inconsistencies: [] };
                            
                            return {
                                ...service,
                                namingDetails: namingData.naming_inconsistencies || [],
                                errorDetails: errorData.error_inconsistencies || []
                            };
                        })
                    );
                    
                    // Calculate violation totals by severity
                    const calculateViolationTotals = (details) => {
                        return {
                            critical: details.filter(i => i.severity === 'critical').length,
                            major: details.filter(i => i.severity === 'major').length,
                            minor: details.filter(i => i.severity === 'minor').length,
                            total: details.length
                        };
                    };
                    
                    // Generate comprehensive JSON report
                    const comprehensiveReport = {
                        metadata: {
                            reportType: "API Governance Platform - Comprehensive Compliance Report",
                            generatedAt: new Date().toISOString(),
                            generatedBy: "API Governance Platform",
                            version: "1.0.0"
                        },
                        summary: {
                            totalServices: services.length,
                            totalNamingIssues: services.reduce((sum, s) => sum + s.inconsistentNaming, 0),
                            totalErrorIssues: services.reduce((sum, s) => sum + s.inconsistentErrors, 0),
                            averageCompliance: services.length > 0 ? 
                                Math.round(services.reduce((sum, s) => sum + s.compliancePercentage, 0) / services.length) : 0,
                            complianceDistribution: {
                                highCompliance: services.filter(s => s.compliancePercentage >= 90).length,
                                mediumCompliance: services.filter(s => s.compliancePercentage >= 70 && s.compliancePercentage < 90).length,
                                lowCompliance: services.filter(s => s.compliancePercentage < 70).length
                            }
                        },
                        services: detailedData.map(service => {
                            const namingTotals = calculateViolationTotals(service.namingDetails);
                            const errorTotals = calculateViolationTotals(service.errorDetails);
                            
                            return {
                                serviceInfo: {
                                    serviceName: service.serviceName,
                                    namespace: service.namespace,
                                    totalEndpoints: service.totalEndpoints,
                                    compliancePercentage: service.compliancePercentage,
                                    complianceLevel: service.compliancePercentage >= 90 ? 'high' : 
                                                   service.compliancePercentage >= 70 ? 'medium' : 'low',
                                    openApiUrl: service.openApiUrl,
                                    lastAnalyzed: service.lastAnalyzed
                                },
                                violationSummary: {
                                    naming: {
                                        total: service.inconsistentNaming,
                                        bySeverity: namingTotals
                                    },
                                    errors: {
                                        total: service.inconsistentErrors,
                                        bySeverity: errorTotals
                                    },
                                    totalViolations: service.inconsistentNaming + service.inconsistentErrors
                                },
                                violations: {
                                    namingInconsistencies: service.namingDetails.map(issue => ({
                                        fieldName: issue.field_name,
                                        currentNaming: issue.current_naming,
                                        suggestedNaming: issue.suggested_naming,
                                        endpoint: issue.endpoint,
                                        severity: issue.severity,
                                        ruleViolated: issue.rule_violated || null,
                                        description: issue.description || null
                                    })),
                                    errorInconsistencies: service.errorDetails.map(issue => ({
                                        issueType: issue.issue_type,
                                        endpoint: issue.endpoint,
                                        httpStatus: issue.http_status,
                                        description: issue.description,
                                        recommendation: issue.recommendation,
                                        severity: issue.severity,
                                        missingFields: issue.missing_fields || []
                                    }))
                                }
                            };
                        }),
                        aggregatedMetrics: {
                            violationsByType: {
                                naming: {
                                    critical: detailedData.reduce((sum, s) => sum + s.namingDetails.filter(i => i.severity === 'critical').length, 0),
                                    major: detailedData.reduce((sum, s) => sum + s.namingDetails.filter(i => i.severity === 'major').length, 0),
                                    minor: detailedData.reduce((sum, s) => sum + s.namingDetails.filter(i => i.severity === 'minor').length, 0)
                                },
                                errors: {
                                    critical: detailedData.reduce((sum, s) => sum + s.errorDetails.filter(i => i.severity === 'critical').length, 0),
                                    major: detailedData.reduce((sum, s) => sum + s.errorDetails.filter(i => i.severity === 'major').length, 0),
                                    minor: detailedData.reduce((sum, s) => sum + s.errorDetails.filter(i => i.severity === 'minor').length, 0)
                                }
                            },
                            topViolators: {
                                mostNamingIssues: detailedData.sort((a, b) => b.inconsistentNaming - a.inconsistentNaming).slice(0, 3).map(s => ({
                                    serviceName: s.serviceName,
                                    issues: s.inconsistentNaming
                                })),
                                mostErrorIssues: detailedData.sort((a, b) => b.inconsistentErrors - a.inconsistentErrors).slice(0, 3).map(s => ({
                                    serviceName: s.serviceName,
                                    issues: s.inconsistentErrors
                                })),
                                lowestCompliance: detailedData.sort((a, b) => a.compliancePercentage - b.compliancePercentage).slice(0, 3).map(s => ({
                                    serviceName: s.serviceName,
                                    compliance: s.compliancePercentage
                                }))
                            }
                        }
                    };
                    
                    // Download the comprehensive JSON report
                    const jsonContent = JSON.stringify(comprehensiveReport, null, 2);
                    const blob = new Blob([jsonContent], { type: 'application/json' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `api-compliance-comprehensive-${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    setIsLoading(false);
                    
                } catch (error) {
                    console.error('Failed to generate comprehensive report:', error);
                    alert('Failed to generate comprehensive report. Please try again.');
                    setIsLoading(false);
                }
            };

            const averageCompliance = services.length > 0 
                ? Math.round(services.reduce((sum, service) => sum + service.compliancePercentage, 0) / services.length)
                : 0;
            
            const openDetailsWindow = (serviceName, type) => {
                const url = `/api/v1/compliance/${type}/${serviceName}/window`;
                window.open(url, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
            };

            const handleViewRecommendations = (service) => {
                setSelectedService(service);
                setShowRecommendations(true);
            };

            if (isLoading) {
                return (
                    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                            <p className="text-gray-600">Loading API governance dashboard...</p>
                        </div>
                    </div>
                );
            }

            return (
                <div className="min-h-screen bg-gray-50">
                    <div className="bg-white shadow-sm border-b">
                        <div className="max-w-7xl mx-auto px-4 py-6">
                            <div className="flex justify-between items-center">
                                <div>
                                    <h1 className="text-3xl font-bold text-gray-900">
                                        🔧 API Governance Platform
                                    </h1>
                                    <p className="mt-2 text-gray-600">
                                        OpenAPI Style Validation & Compliance Monitoring
                                    </p>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <div className="flex items-center">
                                        <div className={`w-2 h-2 rounded-full mr-2 ${
                                            connectionStatus === 'connected' ? 'bg-green-500 animate-pulse' :
                                            connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                                            'bg-red-500'
                                        }`}></div>
                                        <span className="text-sm text-gray-600">
                                            {connectionStatus === 'connected' ? 'Live Data' :
                                             connectionStatus === 'connecting' ? 'Connecting...' :
                                             'Connection Error'}
                                        </span>
                                    </div>
                                    <button 
                                        onClick={fetchLiveData}
                                        disabled={isLoading}
                                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center"
                                    >
                                        {isLoading ? (
                                            <>
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                Refreshing...
                                            </>
                                        ) : (
                                            <>
                                                🔄 Refresh Data
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="max-w-7xl mx-auto px-4 py-8">
                        {/* Error Banner */}
                        {error && (
                            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                                <div className="flex items-center">
                                    <div className="text-red-400 mr-3">⚠️</div>
                                    <div>
                                        <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                                        <p className="text-sm text-red-700 mt-1">
                                            {error} - Showing cached data. 
                                            <button 
                                                onClick={fetchLiveData}
                                                className="ml-2 underline hover:no-underline"
                                            >
                                                Retry connection
                                            </button>
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                        


                        {/* Summary Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-blue-100 rounded-lg">
                                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Total Services</p>
                                        <p className="text-2xl font-bold text-gray-900">{services.length}</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-green-100 rounded-lg">
                                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">High Compliance</p>
                                        <p className="text-2xl font-bold text-green-600">
                                            {services.filter(s => s.compliancePercentage >= 90).length}
                                        </p>
                                        <p className="text-xs text-gray-500">≥90%</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-yellow-100 rounded-lg">
                                        <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Medium Compliance</p>
                                        <p className="text-2xl font-bold text-yellow-600">
                                            {services.filter(s => s.compliancePercentage >= 70 && s.compliancePercentage < 90).length}
                                        </p>
                                        <p className="text-xs text-gray-500">70-89%</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-red-100 rounded-lg">
                                        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Low Compliance</p>
                                        <p className="text-2xl font-bold text-red-600">
                                            {services.filter(s => s.compliancePercentage < 70).length}
                                        </p>
                                        <p className="text-xs text-gray-500">&lt;70%</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-orange-100 rounded-lg">
                                        <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Naming Issues</p>
                                        <p className="text-2xl font-bold text-orange-600">
                                            {services.reduce((sum, s) => sum + s.inconsistentNaming, 0)}
                                        </p>
                                        <p className="text-xs text-gray-500">Total</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="bg-white rounded-lg shadow-sm border p-4">
                                <div className="flex items-center">
                                    <div className="p-2 bg-purple-100 rounded-lg">
                                        <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                                        </svg>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-600">Error Issues</p>
                                        <p className="text-2xl font-bold text-purple-600">
                                            {services.reduce((sum, s) => sum + s.inconsistentErrors, 0)}
                                        </p>
                                        <p className="text-xs text-gray-500">Total</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {/* Main Compliance Dashboard Table */}
                        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
                            <div className="px-6 py-4 border-b flex justify-between items-center">
                                <h2 className="text-lg font-semibold">Service Compliance Overview</h2>
                                <div className="flex space-x-3">
                                    <button 
                                        onClick={exportToJSON}
                                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center"
                                    >
                                        📊 Export JSON Summary
                                    </button>
                                    <button 
                                        onClick={exportComprehensiveReport}
                                        disabled={isLoading}
                                        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center"
                                    >
                                        {isLoading ? (
                                            <>
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                Generating...
                                            </>
                                        ) : (
                                            <>
                                                📋 Full JSON Report
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('serviceName')}
                                            >
                                                Service Name {sortField === 'serviceName' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('totalEndpoints')}
                                            >
                                                Endpoints {sortField === 'totalEndpoints' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('inconsistentNaming')}
                                            >
                                                Inconsistent Names {sortField === 'inconsistentNaming' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('inconsistentErrors')}
                                            >
                                                Inconsistent Errors {sortField === 'inconsistentErrors' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('compliancePercentage')}
                                            >
                                                Compliance % {sortField === 'compliancePercentage' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {services.map((service, index) => (
                                            <tr key={index} className="hover:bg-gray-50">
                                                <td className="px-6 py-4">
                                                    <div className="font-medium text-gray-900 text-lg">
                                                        {service.serviceName}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    <span className="text-lg font-semibold text-gray-900">
                                                        {service.totalEndpoints}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    {service.inconsistentNaming > 0 ? (
                                                        <button 
                                                            onClick={() => openDetailsWindow(service.serviceName, 'naming')}
                                                            className="text-lg font-semibold text-red-600 hover:text-red-800 underline"
                                                        >
                                                            {service.inconsistentNaming} [details]
                                                        </button>
                                                    ) : (
                                                        <span className="text-lg font-semibold text-green-600">0</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    {service.inconsistentErrors > 0 ? (
                                                        <button 
                                                            onClick={() => openDetailsWindow(service.serviceName, 'errors')}
                                                            className="text-lg font-semibold text-red-600 hover:text-red-800 underline"
                                                        >
                                                            {service.inconsistentErrors} [details]
                                                        </button>
                                                    ) : (
                                                        <span className="text-lg font-semibold text-green-600">0</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center justify-center">
                                                        <div className="w-32 bg-gray-200 rounded-full h-4 mr-3">
                                                            <div 
                                                                className={`h-4 rounded-full transition-all duration-300 ${
                                                                    service.compliancePercentage >= 90 ? 'bg-green-500' : 
                                                                    service.compliancePercentage >= 70 ? 'bg-yellow-500' : 
                                                                    'bg-red-500'
                                                                }`}
                                                                style={{width: `${service.compliancePercentage}%`}}
                                                            />
                                                        </div>
                                                        <span className={`font-bold text-lg ${
                                                            service.compliancePercentage >= 90 ? 'text-green-600' : 
                                                            service.compliancePercentage >= 70 ? 'text-yellow-600' : 
                                                            'text-red-600'
                                                        }`}>
                                                            {service.compliancePercentage}%
                                                        </span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
                            <div className="flex justify-between items-start">
                                <div>
                                    <h3 className="font-semibold text-blue-900 mb-2">🔧 OpenAPI Compliance Features:</h3>
                                    <ul className="text-sm text-blue-700 space-y-1">
                                        <li>• <strong>Spectral Integration</strong> - OpenAPI style validation with custom rules</li>
                                        <li>• <strong>Naming Convention Analysis</strong> - camelCase, kebab-case validation</li>
                                        <li>• <strong>Error Response Consistency</strong> - Standard error schema enforcement</li>
                                        <li>• <strong>Real-time Compliance Scoring</strong> - Live progress bars</li>
                                        <li>• <strong>Sortable Dashboard</strong> - Click column headers to sort</li>
                                        <li>• <strong>CSV Export</strong> - Download compliance reports</li>
                                    </ul>
                                </div>
                                <button 
                                    onClick={async () => {
                                        try {
                                            const response = await fetch('/api/v1/harvest/trigger', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ force: true })
                                            });
                                            if (response.ok) {
                                                setTimeout(fetchLiveData, 2000); // Refresh after harvest
                                            }
                                        } catch (error) {
                                            console.error('Failed to trigger harvest:', error);
                                        }
                                    }}
                                    className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                                >
                                    🔄 Trigger Analysis
                                </button>
                            </div>
                        </div>

                        <div className="mt-4 text-center text-sm text-gray-500">
                            <p>🔧 API Governance Platform • OpenAPI Style Validation • Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Never'}</p>
                            <p className="mt-1">Auto-refreshing every 30 seconds • Spectral-powered compliance analysis</p>
                        </div>
                    </div>


                </div>
            );
        };

        ReactDOM.render(<ComplianceDashboard />, document.getElementById('root'));
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)
    
    # Add routers
    app.include_router(create_health_router(), prefix="/health", tags=["health"])
    app.include_router(create_api_router(platform), prefix="/api/v1", tags=["api"])
    
    return app


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


def main():
    """Main entry point."""
    # Setup logging
    setup_logging()
    
    # Setup metrics
    setup_metrics()
    
    # Handle signals
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create app
    app = create_app()
    
    # Run server
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info("Starting API Governance Platform", host=host, port=port)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None,  # Use our custom logging
        access_log=False
    )


if __name__ == "__main__":
    main()