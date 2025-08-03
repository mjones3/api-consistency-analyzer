#!/bin/bash
echo "Starting port forwarding for Kubernetes services..."
echo ""
echo "API Governance Platform:"
echo "  Health Dashboard: http://localhost:8080/health/status"
echo "  API Endpoints: http://localhost:8080/api/v1/"
echo ""
echo "Blood Banking Services:"
echo "  Legacy Service: http://localhost:8081/swagger-ui.html"
echo "  Modern Service: http://localhost:8082/swagger-ui.html"
echo ""
echo "Istio Dashboards:"
echo "  Kiali: http://localhost:20001"
echo "  Grafana: http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo ""
echo "Press Ctrl+C to stop all port forwards"

# Start port forwards in background
kubectl port-forward svc/api-governance 8080:80 -n api-governance &
kubectl port-forward svc/legacy-donor-service 8081:8081 -n api &
kubectl port-forward svc/modern-donor-service 8082:8082 -n api &

# Istio dashboards (if available)
kubectl port-forward svc/kiali 20001:20001 -n istio-system &
kubectl port-forward svc/grafana 3000:3000 -n istio-system &
kubectl port-forward svc/prometheus 9090:9090 -n istio-system &

# Wait for all background jobs
wait