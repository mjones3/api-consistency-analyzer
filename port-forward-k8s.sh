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
kubectl port-forward -n api service/api-governance 8080:80 &
kubectl port-forward -n api service/legacy-donor-service 8080:80 &
kubectl port-forward -n api service/modern-donor-service 8080:80 &

# Istio dashboards (if available)
kubectl port-forward -n istio-system service/kiali 20001:20001  &
#kubectl port-forward svc/grafana 3000:3000 -n istio-system &
#kubectl port-forward svc/prometheus 9090:9090 -n istio-system &

# Wait for all background jobs
wait
