# 🔍 Microservices API Governance

> Automated API consistency analysis and governance for Spring Boot microservices in Istio service mesh

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-1.28+-blue.svg)](https://kubernetes.io/)
[![Istio](https://img.shields.io/badge/istio-1.20+-blue.svg)](https://istio.io/)

## 🚀 What This Solves

Managing API consistency across dozens of Spring Boot microservices is challenging. This tool automatically:

- 🔍 **Discovers** all Spring Boot services through Istio service mesh
- 📊 **Harvests** OpenAPI specifications from `/v3/api-docs` endpoints  
- 🎯 **Identifies** field naming inconsistencies (e.g., `zip` vs `zipCode` vs `postalCode`)
- 🏥 **Recommends** FHIR-compliant standardizations for healthcare APIs
- 📈 **Monitors** API evolution over time with scheduled analysis

## ✨ Features

### 🤖 Automatic Service Discovery
- Integrates with Istio service mesh for comprehensive service registry access
- Discovers Spring Boot services across multiple Kubernetes namespaces
- Filters services based on actuator endpoints and OpenAPI availability

### 📊 Comprehensive Analysis
- Harvests OpenAPI 3.0 specifications from all discovered services
- Analyzes field name patterns and type inconsistencies
- Generates detailed reports with severity levels (Critical/Major/Minor)
- Exports results in both Markdown and CSV formats

### 🏥 Healthcare Domain Expertise
- Built-in FHIR (Fast Healthcare Interoperability Resources) mappings
- Recommends healthcare-standard field names and types
- Supports blood banking, patient management, and clinical data standards

### 🔄 Production-Ready Deployment
- Kubernetes-native with Helm charts and manifests
- Istio service mesh integration with mTLS support
- Health checks, metrics endpoints, and Prometheus integration
- Scheduled harvesting with configurable intervals

## 🏗️ Architecture
