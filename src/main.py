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
        description="Automated API governance with Istio integration and FHIR compliance",
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
                    serviceName: 'legacy-donor-service',
                    namespace: 'api',
                    totalEndpoints: 12,
                    inconsistentNaming: 5,
                    inconsistentErrors: 3,
                    compliancePercentage: 75,
                    openApiUrl: 'http://localhost:8081/swagger-ui.html',
                    lastAnalyzed: new Date().toISOString()
                },
                {
                    serviceName: 'modern-donor-service',
                    namespace: 'api',
                    totalEndpoints: 8,
                    inconsistentNaming: 2,
                    inconsistentErrors: 1,
                    compliancePercentage: 85,
                    openApiUrl: 'http://localhost:8082/swagger-ui.html',
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

            // Export to CSV functionality
            const exportToCSV = () => {
                const headers = ['Service Name', 'Endpoints', 'Inconsistent Names', 'Inconsistent Errors', 'Compliance %'];
                const csvContent = [
                    headers.join(','),
                    ...services.map(service => [
                        service.serviceName,
                        service.totalEndpoints,
                        service.inconsistentNaming,
                        service.inconsistentErrors,
                        service.compliancePercentage
                    ].join(','))
                ].join('\\n');
                
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `api-compliance-report-${new Date().toISOString().split('T')[0]}.csv`;
                a.click();
                window.URL.revokeObjectURL(url);
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
                            <p className="text-gray-600">Loading FHIR compliance dashboard...</p>
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
                        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-6">
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Total Services</p>
                                <p className="text-2xl font-bold text-gray-900">{services.length}</p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Average Compliance</p>
                                <p className={`text-2xl font-bold ${averageCompliance >= 90 ? 'text-green-600' : averageCompliance >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                                    {averageCompliance}%
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">High Compliance</p>
                                <p className="text-2xl font-bold text-green-600">
                                    {services.filter(s => s.compliancePercentage >= 90).length}
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Medium Compliance</p>
                                <p className="text-2xl font-bold text-yellow-600">
                                    {services.filter(s => s.compliancePercentage >= 70 && s.compliancePercentage < 90).length}
                                </p>
                            </div>
                            <div className="bg-white rounded-lg shadow-sm border p-6">
                                <p className="text-sm font-medium text-gray-600">Low Compliance</p>
                                <p className="text-2xl font-bold text-red-600">
                                    {services.filter(s => s.compliancePercentage < 70).length}
                                </p>
                            </div>
                        </div>

                        {/* Compliance Table */}
                        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
                            <div className="px-6 py-4 border-b flex justify-between items-center">
                                <h2 className="text-lg font-semibold">Service Compliance Overview</h2>
                                <button 
                                    onClick={exportToCSV}
                                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                                >
                                    📊 Export CSV
                                </button>
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
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('totalEndpoints')}
                                            >
                                                Endpoints {sortField === 'totalEndpoints' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('inconsistentNaming')}
                                            >
                                                Inconsistent Names {sortField === 'inconsistentNaming' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('inconsistentErrors')}
                                            >
                                                Inconsistent Errors {sortField === 'inconsistentErrors' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                                onClick={() => sortServices('compliancePercentage')}
                                            >
                                                Compliance % {sortField === 'compliancePercentage' && (sortDirection === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {services.map((service, index) => (
                                            <tr key={index} className="hover:bg-gray-50">
                                                <td className="px-6 py-4">
                                                    <div>
                                                        <div className="font-medium text-gray-900">{service.serviceName}</div>
                                                        <div className="text-sm text-gray-500">{service.namespace}</div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-medium">
                                                        {service.totalEndpoints}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    {service.inconsistentNaming > 0 ? (
                                                        <button 
                                                            onClick={() => openDetailsWindow(service.serviceName, 'naming')}
                                                            className="text-red-600 hover:text-red-800 font-medium underline"
                                                        >
                                                            {service.inconsistentNaming} [details]
                                                        </button>
                                                    ) : (
                                                        <span className="text-green-600 font-medium">0</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    {service.inconsistentErrors > 0 ? (
                                                        <button 
                                                            onClick={() => openDetailsWindow(service.serviceName, 'errors')}
                                                            className="text-red-600 hover:text-red-800 font-medium underline"
                                                        >
                                                            {service.inconsistentErrors} [details]
                                                        </button>
                                                    ) : (
                                                        <span className="text-green-600 font-medium">0</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center">
                                                        <div className="w-full bg-gray-200 rounded-full h-2 mr-3">
                                                            <div 
                                                                className={`h-2 rounded-full ${
                                                                    service.compliancePercentage >= 90 ? 'bg-green-500' : 
                                                                    service.compliancePercentage >= 70 ? 'bg-yellow-500' : 
                                                                    'bg-red-500'
                                                                }`}
                                                                style={{width: `${service.compliancePercentage}%`}}
                                                            />
                                                        </div>
                                                        <span className={`font-semibold text-sm ${
                                                            service.compliancePercentage >= 90 ? 'text-green-600' : 
                                                            service.compliancePercentage >= 70 ? 'text-yellow-600' : 
                                                            'text-red-600'
                                                        }`}>
                                                            {service.compliancePercentage}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <a 
                                                        href={service.openApiUrl} 
                                                        target="_blank" 
                                                        rel="noopener noreferrer" 
                                                        className="text-blue-600 hover:text-blue-800 font-medium mr-4"
                                                    >
                                                        📋 OpenAPI
                                                    </a>
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
                                        <li>• <strong>Real-time Compliance Scoring</strong> - Average: {averageCompliance}%</li>
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