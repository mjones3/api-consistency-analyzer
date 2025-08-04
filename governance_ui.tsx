import React, { useState, useEffect } from "react";
import {
  RefreshCw,
  Download,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  FileText,
  Lightbulb,
  X,
} from "lucide-react";

// TypeScript interfaces
interface Service {
  namespace: string;
  serviceName: string;
  totalAttributes: number;
  nonCompliantAttributes: number;
  compliancePercentage: number;
  openApiUrl: string;
  recommendationsUrl: string;
  fhirViolations: FHIRViolation[];
}

interface FHIRViolation {
  fieldName: string;
  currentType: string;
  requiredType: string;
  currentRequired: boolean;
  fhirRequired: boolean;
  issueDescription: string;
  fhirCompliantValue: string;
  openApiLineNumber: number | null;
  severity: "error" | "warning";
  actionRequired: string;
}

interface ComplianceReport {
  services: Service[];
  summary: {
    totalServices: number;
    averageCompliance: number;
    criticalServices: number;
    fullyCompliantServices: number;
  };
  lastUpdated: string;
}

const GovernanceDashboard: React.FC = () => {
  const [selectedNamespace, setSelectedNamespace] = useState<string>("all");
  const [services, setServices] = useState<Service[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>(["all"]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isHarvesting, setIsHarvesting] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [showRecommendations, setShowRecommendations] =
    useState<boolean>(false);

  // Enhanced mock data with FHIR compliance analysis
  const mockServices: Service[] = [
    {
      namespace: "api",
      serviceName: "legacy-donor-service",
      totalAttributes: 9,
      nonCompliantAttributes: 8,
      compliancePercentage: 11.1,
      openApiUrl: "http://localhost:8081/swagger-ui.html",
      recommendationsUrl: "/recommendations/legacy-donor-service",
      fhirViolations: [
        {
          fieldName: "resourceType",
          currentType: "missing",
          requiredType: "string",
          currentRequired: false,
          fhirRequired: true,
          issueDescription: 'Missing required FHIR field "resourceType"',
          fhirCompliantValue: '"Patient"',
          openApiLineNumber: null,
          severity: "error",
          actionRequired: 'Add resourceType field with value "Patient"',
        },
        {
          fieldName: "donorId",
          currentType: "string",
          requiredType: "Identifier[]",
          currentRequired: true,
          fhirRequired: true,
          issueDescription:
            'Non-FHIR field "donorId" should be mapped to FHIR field "identifier"',
          fhirCompliantValue: '[{"value": "D123456"}]',
          openApiLineNumber: 45,
          severity: "error",
          actionRequired: "Replace donorId with identifier array structure",
        },
        {
          fieldName: "firstName",
          currentType: "string",
          requiredType: "string[]",
          currentRequired: true,
          fhirRequired: true,
          issueDescription:
            'Non-FHIR field "firstName" should be mapped to FHIR field "name.given"',
          fhirCompliantValue: '["John"]',
          openApiLineNumber: 52,
          severity: "error",
          actionRequired: "Map firstName to name.given array",
        },
        {
          fieldName: "lastName",
          currentType: "string",
          requiredType: "string",
          currentRequired: true,
          fhirRequired: true,
          issueDescription:
            'Non-FHIR field "lastName" should be mapped to FHIR field "name.family"',
          fhirCompliantValue: '"Smith"',
          openApiLineNumber: 58,
          severity: "error",
          actionRequired: "Map lastName to name.family",
        },
        {
          fieldName: "phoneNumber",
          currentType: "string",
          requiredType: "ContactPoint[]",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            'Non-FHIR field "phoneNumber" should be mapped to FHIR field "telecom"',
          fhirCompliantValue: '[{"system": "phone", "value": "555-1234"}]',
          openApiLineNumber: 64,
          severity: "warning",
          actionRequired: "Transform to FHIR ContactPoint structure",
        },
        {
          fieldName: "email",
          currentType: "string",
          requiredType: "ContactPoint[]",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            'Non-FHIR field "email" should be mapped to FHIR field "telecom"',
          fhirCompliantValue:
            '[{"system": "email", "value": "john@example.com"}]',
          openApiLineNumber: 70,
          severity: "warning",
          actionRequired: "Transform to FHIR ContactPoint structure",
        },
        {
          fieldName: "zip",
          currentType: "integer",
          requiredType: "string",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            'Non-FHIR field "zip" should be mapped to FHIR field "address.postalCode"',
          fhirCompliantValue: '"12345"',
          openApiLineNumber: 78,
          severity: "warning",
          actionRequired: "Convert to string and map to address.postalCode",
        },
        {
          fieldName: "createdDate",
          currentType: "string",
          requiredType: "dateTime",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            'Non-FHIR field "createdDate" should be mapped to FHIR field "meta.lastUpdated"',
          fhirCompliantValue: '"2023-01-01T12:00:00Z"',
          openApiLineNumber: 85,
          severity: "warning",
          actionRequired: "Map to meta.lastUpdated with ISO 8601 format",
        },
      ],
    },
    {
      namespace: "api",
      serviceName: "modern-donor-service",
      totalAttributes: 9,
      nonCompliantAttributes: 1,
      compliancePercentage: 88.9,
      openApiUrl: "http://localhost:8082/swagger-ui.html",
      recommendationsUrl: "/recommendations/modern-donor-service",
      fhirViolations: [
        {
          fieldName: "active",
          currentType: "missing",
          requiredType: "boolean",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            'Optional FHIR field "active" is missing but recommended for Patient resources',
          fhirCompliantValue: "true",
          openApiLineNumber: null,
          severity: "warning",
          actionRequired:
            "Add optional active field to indicate patient record status",
        },
      ],
    },
    {
      namespace: "production",
      serviceName: "patient-service",
      totalAttributes: 12,
      nonCompliantAttributes: 3,
      compliancePercentage: 75.0,
      openApiUrl:
        "http://patient-service.production.svc.cluster.local:8080/swagger-ui.html",
      recommendationsUrl: "/recommendations/patient-service",
      fhirViolations: [
        {
          fieldName: "patientId",
          currentType: "string",
          requiredType: "Identifier[]",
          currentRequired: true,
          fhirRequired: true,
          issueDescription:
            'Field "patientId" should use FHIR Identifier structure',
          fhirCompliantValue:
            '[{"system": "http://hospital.org/patient-ids", "value": "P123456"}]',
          openApiLineNumber: 32,
          severity: "error",
          actionRequired: "Convert to FHIR Identifier array",
        },
        {
          fieldName: "contactInfo",
          currentType: "string",
          requiredType: "ContactPoint[]",
          currentRequired: false,
          fhirRequired: false,
          issueDescription:
            "Contact information should use FHIR ContactPoint structure",
          fhirCompliantValue: '[{"system": "phone", "value": "555-0123"}]',
          openApiLineNumber: 48,
          severity: "warning",
          actionRequired: "Transform to ContactPoint array",
        },
        {
          fieldName: "birthDate",
          currentType: "string",
          requiredType: "date",
          currentRequired: true,
          fhirRequired: true,
          issueDescription:
            "Birth date format should comply with FHIR date format",
          fhirCompliantValue: '"1985-06-15"',
          openApiLineNumber: 55,
          severity: "warning",
          actionRequired: "Ensure YYYY-MM-DD format",
        },
      ],
    },
    {
      namespace: "production",
      serviceName: "collection-service",
      totalAttributes: 8,
      nonCompliantAttributes: 0,
      compliancePercentage: 100.0,
      openApiUrl:
        "http://collection-service.production.svc.cluster.local:8080/swagger-ui.html",
      recommendationsUrl: "/recommendations/collection-service",
      fhirViolations: [],
    },
  ];

  useEffect(() => {
    // Simulate API call to load services data
    const loadData = async () => {
      setIsLoading(true);

      try {
        // In real implementation, this would be:
        // const response = await fetch('/api/services');
        // const data = await response.json();

        // Extract unique namespaces
        const uniqueNamespaces = [
          "all",
          ...new Set(mockServices.map((s) => s.namespace)),
        ];
        setNamespaces(uniqueNamespaces);

        // Set services
        setServices(mockServices);
        setLastUpdated(new Date().toISOString());

        setTimeout(() => setIsLoading(false), 800);
      } catch (error) {
        console.error("Failed to load services:", error);
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Filter services based on selected namespace
  const filteredServices =
    selectedNamespace === "all"
      ? services
      : services.filter((service) => service.namespace === selectedNamespace);

  // Calculate average compliance percentage
  const averageCompliance =
    filteredServices.length > 0
      ? Math.round(
          filteredServices.reduce(
            (sum, service) => sum + service.compliancePercentage,
            0
          ) / filteredServices.length
        )
      : 0;

  // Get compliance status color
  const getComplianceColor = (percentage: number): string => {
    if (percentage >= 90) return "text-green-600";
    if (percentage >= 70) return "text-yellow-600";
    return "text-red-600";
  };

  // Get severity color
  const getSeverityColor = (severity: string): string => {
    return severity === "error" ? "text-red-600" : "text-yellow-600";
  };

  // Handle harvest now button
  const handleHarvestNow = async () => {
    setIsHarvesting(true);

    try {
      const response = await fetch("/api/v1/harvest/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        // Refresh data after harvest
        setTimeout(() => {
          setLastUpdated(new Date().toISOString());
          setIsHarvesting(false);
        }, 3000);
      }
    } catch (error) {
      console.error("Harvest failed:", error);
      setIsHarvesting(false);
    }
  };

  // Handle export compliance report
  const handleExportReport = async () => {
    try {
      const reportData: ComplianceReport = {
        services: filteredServices,
        summary: {
          totalServices: filteredServices.length,
          averageCompliance,
          criticalServices: filteredServices.filter(
            (service) => service.compliancePercentage < 70
          ).length,
          fullyCompliantServices: filteredServices.filter(
            (service) => service.compliancePercentage === 100
          ).length,
        },
        lastUpdated: lastUpdated || new Date().toISOString(),
      };

      const blob = new Blob([JSON.stringify(reportData, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fhir-compliance-report-${selectedNamespace}-${
        new Date().toISOString().split("T")[0]
      }.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  // Handle view recommendations
  const handleViewRecommendations = (service: Service) => {
    setSelectedService(service);
    setShowRecommendations(true);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading FHIR compliance dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <h1 className="text-3xl font-bold text-gray-900">
              🩸 API Governance Platform
            </h1>
            <p className="mt-2 text-gray-600">
              FHIR R4 Compliance Monitoring for Blood Banking Microservices
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Controls Section */}
        <div className="bg-white rounded-lg shadow-sm border mb-6 p-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
              {/* Namespace Selector */}
              <div className="flex items-center gap-2">
                <label
                  htmlFor="namespace"
                  className="text-sm font-medium text-gray-700"
                >
                  Namespace:
                </label>
                <select
                  id="namespace"
                  value={selectedNamespace}
                  onChange={(e) => setSelectedNamespace(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {namespaces.map((ns) => (
                    <option key={ns} value={ns}>
                      {ns === "all" ? "All Namespaces" : ns}
                    </option>
                  ))}
                </select>
              </div>

              {/* Last Updated */}
              <div className="text-sm text-gray-600">
                <span className="font-medium">Last updated:</span>{" "}
                {lastUpdated ? new Date(lastUpdated).toLocaleString() : "Never"}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleHarvestNow}
                disabled={isHarvesting}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <RefreshCw
                  className={`w-4 h-4 ${isHarvesting ? "animate-spin" : ""}`}
                />
                {isHarvesting ? "Harvesting..." : "Run Harvest Now"}
              </button>

              <button
                onClick={handleExportReport}
                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export Compliance Report
              </button>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Total Services
                </p>
                <p className="text-2xl font-bold text-gray-900">
                  {filteredServices.length}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-blue-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Average Compliance
                </p>
                <p
                  className={`text-2xl font-bold ${getComplianceColor(
                    averageCompliance
                  )}`}
                >
                  {averageCompliance}%
                </p>
              </div>
              <AlertCircle
                className={`w-8 h-8 ${getComplianceColor(averageCompliance)}`}
              />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Critical Services
                </p>
                <p className="text-2xl font-bold text-red-600">
                  {
                    filteredServices.filter(
                      (service) => service.compliancePercentage < 70
                    ).length
                  }
                </p>
              </div>
              <AlertCircle className="w-8 h-8 text-red-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Fully Compliant
                </p>
                <p className="text-2xl font-bold text-green-600">
                  {
                    filteredServices.filter(
                      (service) => service.compliancePercentage === 100
                    ).length
                  }
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          </div>
        </div>

        {/* Services Table */}
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              FHIR Compliance Analysis -{" "}
              {selectedNamespace === "all"
                ? "All Namespaces"
                : selectedNamespace}
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Namespace
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Service Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Attributes
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Non-compliant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Compliance %
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    OpenAPI Spec
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    FHIR Recommendations
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredServices.map((service) => (
                  <tr
                    key={`${service.namespace}-${service.serviceName}`}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {service.namespace}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {service.serviceName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {service.totalAttributes}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span
                        className={`font-semibold ${
                          service.nonCompliantAttributes > 0
                            ? "text-red-600"
                            : "text-gray-900"
                        }`}
                      >
                        {service.nonCompliantAttributes}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center">
                        <span
                          className={`font-semibold ${getComplianceColor(
                            service.compliancePercentage
                          )}`}
                        >
                          {service.compliancePercentage}%
                        </span>
                        <div className="ml-3 w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              service.compliancePercentage >= 90
                                ? "bg-green-500"
                                : service.compliancePercentage >= 70
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{
                              width: `${service.compliancePercentage}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <a
                        href={service.openApiUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium"
                      >
                        <ExternalLink className="w-4 h-4" />
                        View Spec
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => handleViewRecommendations(service)}
                        className="inline-flex items-center gap-1 text-orange-600 hover:text-orange-800 font-medium"
                      >
                        <Lightbulb className="w-4 h-4" />
                        View ({service.fhirViolations.length})
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredServices.length === 0 && (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No services found
                </h3>
                <p className="text-gray-600">
                  {selectedNamespace === "all"
                    ? "No services discovered yet. Try running a harvest."
                    : `No services found in the ${selectedNamespace} namespace.`}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            API Governance Platform • FHIR R4 Compliance Analysis • Powered by
            Kubernetes & Istio
          </p>
        </div>
      </div>

      {/* FHIR Recommendations Modal */}
      {showRecommendations && selectedService && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">
                    FHIR R4 Compliance Recommendations
                  </h3>
                  <p className="text-sm opacity-90">
                    {selectedService.serviceName} • {selectedService.namespace}{" "}
                    namespace
                  </p>
                </div>
                <button
                  onClick={() => setShowRecommendations(false)}
                  className="text-white hover:text-gray-200"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {/* Compliance Summary */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-gray-900">
                      {selectedService.compliancePercentage}%
                    </p>
                    <p className="text-sm text-gray-600">FHIR Compliance</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-600">
                      {selectedService.fhirViolations.length}
                    </p>
                    <p className="text-sm text-gray-600">Issues Found</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-blue-600">
                      {selectedService.totalAttributes}
                    </p>
                    <p className="text-sm text-gray-600">Total Fields</p>
                  </div>
                </div>
              </div>

              {/* Recommendations Table */}
              {selectedService.fhirViolations.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Field Name
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Current Type
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          FHIR Type
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          FHIR Compliant Value
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Line #
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                          Severity
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {selectedService.fhirViolations.map(
                        (violation, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-4 text-sm">
                              <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono">
                                {violation.fieldName}
                              </code>
                            </td>
                            <td className="px-4 py-4 text-sm">
                              <code className="text-gray-600">
                                {violation.currentType}
                              </code>
                            </td>
                            <td className="px-4 py-4 text-sm">
                              <code className="text-blue-600 font-semibold">
                                {violation.requiredType}
                              </code>
                            </td>
                            <td className="px-4 py-4 text-sm">
                              <code className="bg-blue-50 text-blue-800 px-2 py-1 rounded text-xs">
                                {violation.fhirCompliantValue}
                              </code>
                            </td>
                            <td className="px-4 py-4 text-sm">
                              {violation.openApiLineNumber ? (
                                <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-mono">
                                  Line {violation.openApiLineNumber}
                                </span>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            <td className="px-4 py-4 text-sm">
                              <span
                                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  violation.severity === "error"
                                    ? "bg-red-100 text-red-800"
                                    : "bg-yellow-100 text-yellow-800"
                                }`}
                              >
                                {violation.severity === "error" ? "🚨" : "⚠️"}{" "}
                                {violation.severity.toUpperCase()}
                              </span>
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Fully FHIR Compliant!
                  </h3>
                  <p className="text-gray-600">
                    This service meets all FHIR R4 requirements.
                  </p>
                </div>
              )}

              {/* FHIR Reference */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-blue-900">
                      FHIR R4 Reference
                    </h4>
                    <p className="text-sm text-blue-700 mt-1">
                      For detailed FHIR specifications, visit{" "}
                      <a
                        href="https://hl7.org/fhir/R4/patient.html"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-blue-800"
                      >
                        HL7 FHIR R4 Patient Resource
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GovernanceDashboard;
