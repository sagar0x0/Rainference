#  Kubernetes Setup for Rainference

This directory contains all the Kubernetes manifests needed to deploy the Rainference LLM inference server (e.g., vLLM running LLaMA 3 8B) on a GPU-enabled Kubernetes cluster.

---

## Directory Structure

```bash
k8s/
├── config/                  # Secrets and MetalLB configurations
│   ├── hf-token-secret.yaml      # Hugging Face token 
│   ├── l2adv.yaml                # Layer 2 advertisement config (MetalLB)
│   └── metallb-config.yaml      # MetalLB IP pool configuration
├── deployments/            # Deployment manifests
│   └── llama-8b-deployment.yaml
├── ingress/                # Ingress routing
│   └── llama-8b-ingress.yaml
├── services/               # Kubernetes Services
│   └── llama-8b-service.yaml
├── volumes/                # Persistent Volume and PVC
│   ├── llama-8b-pv.yaml
│   └── llama-8b-pvc.yaml
└── README.md               # This file
```

---

## Hugging Face Token Secret

Hugging Face access requires an authentication token. This is stored as a Kubernetes Secret.

- The file `config/hf-token-secret.yaml` should contain a placeholder:

```yaml
data:
  token: <BASE64_ENCODED_HF_TOKEN_HERE>
```

### To Create the Secret:

1. Base64 encode your token:
   ```bash
   echo -n "hf_xxx..." | base64
   ```

2. Replace `<BASE64_ENCODED_HF_TOKEN_HERE>` in the YAML.


---

## MetalLB IP Address Configuration

MetalLB is used to assign IPs to exposed services (LoadBalancer type).

- The file `config/metallb-config.yaml` defines IP address pools.


### Example:

```yaml
spec:
  addresses:
    - <REPLACE_WITH_YOUR_PUBLIC_OR_PRIVATE_IP_RANGE>
```


```yaml
# Replace with actual public or private IP range
- <REPLACE_WITH_YOUR_PUBLIC_OR_PRIVATE_IP_RANGE>
```

---


## Deployment

You can deploy all manifests manually or use a shell script.

### Option 1: Manual

```bash
kubectl apply -f volumes/
kubectl apply -f config/
kubectl apply -f services/
kubectl apply -f deployments/
kubectl apply -f ingress/
```

### Option 2: Automated

```bash
bash k8s-setup.sh
```

Ensure the script has execution permission:

```bash
chmod +x k8s-setup.sh
```

