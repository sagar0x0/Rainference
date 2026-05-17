#!/bin/bash

# Parse arguments
SKIP_INIT=false
for arg in "$@"; do
    if [ "$arg" == "--skip-init" ]; then
        SKIP_INIT=true
    fi
done

if [ "$SKIP_INIT" = false ]; then
    echo "Running full cluster bootstrap..."
    sudo bash scripts/cluster-bootstrap.sh
    
    echo "Waiting for node to become ready before proceeding..."
    sleep 30
else
    echo "Skipping cluster bootstrap (--skip-init flag provided)."
fi

echo "Deploying Kubernetes Manifests..."
# Apply MetalLB via external manifest first, then our config
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.3/config/manifests/metallb-native.yaml
echo "Waiting for MetalLB controller to start..."
sleep 15

kubectl apply -f k8s/volumes/
kubectl apply -f k8s/config/
kubectl apply -f k8s/services/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/ingress/

# If monitoring stack is added, apply it too
if [ -d "k8s/monitoring" ]; then
    kubectl apply -f k8s/monitoring/
fi

echo "Setup complete!"