#!/bin/bash
kubectl apply -f k8s/volumes/
kubectl apply -f k8s/config/
kubectl apply -f k8s/services/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/ingress/