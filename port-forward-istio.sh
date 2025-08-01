#!/bin/bash
echo "Starting port forwarding for Istio addons..."
echo "Kiali: http://localhost:20001"
echo "Grafana: http://localhost:3000"  
echo "Prometheus: http://localhost:9090"
echo "Sample App: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all port forwards"

# Start port forwards in background
kubectl port-forward svc/kiali 20001:20001 -n istio-system &
kubectl port-forward svc/grafana 3000:3000 -n istio-system &
kubectl port-forward svc/prometheus 9090:9090 -n istio-system &
kubectl port-forward svc/httpbin 8000:8000 -n sample-app &

# Wait for all background jobs
wait
