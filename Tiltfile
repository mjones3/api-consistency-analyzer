# Build and deploy modern-donor-service
docker_build('modern-donor-service:latest', './modern-donor-service')
k8s_yaml('./scripts/deploy-kubernetes.sh')  # or wherever your k8s manifests are
k8s_resource('modern-donor-service', port_forwards='8080:8080')

# Build and deploy legacy-donor-service
docker_build('legacy-donor-service:latest', './legacy-donor-service')
k8s_resource('legacy-donor-service', port_forwards='8081:8080')
