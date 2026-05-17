# k8s — Kubernetes Infrastructure for Rainference

This directory contains all Kubernetes manifests that define the production deployment of the Rainference inference platform. Everything here is applied directly against a self-managed cluster; there is no Helm chart abstraction manifests are explicit and auditable.

---

## Directory Structure

```
k8s/
├── config/                       # Cluster-level configuration and secrets
│   ├── backend-secrets.yaml         # K8s Secret: DB, Stripe, GitHub, CORS credentials
│   ├── hf-token-secret.yaml         # K8s Secret: Hugging Face hub token (for model pull)
│   ├── metallb-config.yaml          # MetalLB IPAddressPool definition
│   └── l2adv.yaml                   # MetalLB L2Advertisement (enables L2 mode)
├── deployments/                  # Workload manifests
│   ├── llama-8b-deployment.yaml     # vLLM pod: GPU limits, PVC mount, startup/liveness probes
│   └── backend-deployment.yaml      # FastAPI pod: secretRef env injection, /metrics annotations
├── monitoring/                   # Observability stack
│   ├── prometheus-configmap.yaml      # Prometheus scrape configuration
│   ├── prometheus-deployment.yaml     # Prometheus server + ClusterRole/Binding
│   ├── prometheus-service.yaml        # ClusterIP service for Prometheus
│   ├── grafana-configmap.yaml         # Grafana datasource provisioning (auto-connects Prometheus)
│   ├── grafana-dashboard-configmap.yaml  # Pre-built vLLM + API dashboard JSON
│   └── grafana-deployment.yaml        # Grafana deployment + LoadBalancer service
├── ingress/
│   └── llama-8b-ingress.yaml        # Ingress routing for the inference service
├── services/
│   └── llama-8b-service.yaml        # ClusterIP service for vLLM
├── volumes/
│   ├── llama-8b-pv.yaml             # HostPath PV for HuggingFace model cache
│   └── llama-8b-pvc.yaml            # PVC bound to the above PV
└── README.md
```

---

## Phase 1: Node Bootstrap

Before applying any manifests, the node itself must be provisioned. `scripts/cluster-bootstrap.sh` (at the repo root) is an idempotent shell script that takes a raw Ubuntu 22.04 machine to a functional single-node Kubernetes cluster:

```
Raw Ubuntu 22.04
  → swap disabled, sysctl tuned
  → containerd (SystemdCgroup=true)
  → kubeadm 1.29 / kubelet / kubectl
  → NVIDIA driver 535 (ubuntu-drivers)
  → nvidia-container-toolkit (GPU → containerd passthrough)
  → kubeadm init (pod-cidr 10.244.0.0/16, control-plane taint removed)
  → Flannel CNI
```

```bash
sudo bash scripts/cluster-bootstrap.sh
```

> A reboot may be required for NVIDIA drivers to fully initialize. After reboot, verify with `nvidia-smi` before proceeding.

---

## Phase 2: Manifest Apply

Once the cluster is healthy (`kubectl get nodes` shows `Ready`), apply manifests in dependency order:

### Automated (recommended)

```bash
# Full deploy (bootstrap + manifests)
bash k8s-setup.sh

# Manifests only (cluster already initialized)
bash k8s-setup.sh --skip-init
```

### Manual (for debugging individual layers)

```bash
kubectl apply -f k8s/volumes/          # PV + PVC for model cache
kubectl apply -f k8s/config/           # Secrets + MetalLB config
kubectl apply -f k8s/services/         # Services
kubectl apply -f k8s/deployments/      # vLLM + FastAPI pods
kubectl apply -f k8s/ingress/          # Ingress routing
kubectl apply -f k8s/monitoring/       # Prometheus + Grafana
```

---

## Secret Configuration

Secrets are stored in Kubernetes and injected into pods via `envFrom.secretRef`. No credentials live in container images or environment files on the node.

### Hugging Face Token

Required to pull gated models (LLaMA-3.1-8B-Instruct) from the HuggingFace Hub.

1. Base64-encode your token:
   ```bash
   echo -n "hf_xxxxxxxxxxxxxxxxxxxxxxxx" | base64
   ```
2. Paste the result into `config/hf-token-secret.yaml` under `data.token`.

### Backend Secrets

Edit `config/backend-secrets.yaml` and replace placeholder values before applying:

```yaml
stringData:
  POSTGRESS_PASSWD: "<your-postgres-password>"
  GITHUB_CLIENT_ID: "<your-github-client-id>"
  GITHUB_CLIENT_SECRET: "<your-github-client-secret>"
  STRIPE_SECRET_KEY: "<your-stripe-secret-key>"
  STRIPE_ENDPOINT_SECRET: "<your-stripe-endpoint-secret>"
  KUBE_SERVER_URL: "http://llama-8b-service:8000/v1/completions"
```

### MetalLB IP Pool

Edit `config/metallb-config.yaml` to reflect the IP range available on your node's network interface:

```yaml
spec:
  addresses:
    - 10.x.x.100-10.x.x.110   # Replace with your actual IP range
```

---

## Monitoring Stack

The `monitoring/` directory deploys a self-contained Prometheus + Grafana stack with zero external dependencies.

### Prometheus

- Scrapes vLLM's `/metrics` endpoint on `llama-8b-service:8000`
- Scrapes the FastAPI gateway's `/metrics` endpoint on `backend-service:8000`
- Scrape interval: `15s`
- Access: `ClusterIP` (port `9090`) use `kubectl port-forward` for local access

### Grafana

- Deployed with `LoadBalancer` type service (MetalLB assigns an IP)
- Pre-provisioned datasource: Prometheus at `http://prometheus-service:9090`
- Pre-loaded dashboard tracking:

| Panel | Query |
|---|---|
| Token Throughput | `rate(vllm:tokens_total[1m])` |
| P99 Request Latency | `histogram_quantile(0.99, rate(vllm:e2e_request_latency_seconds_bucket[5m]))` |
| GPU Utilization | `DCGM_FI_DEV_GPU_UTIL` |
| FastAPI Token Rate | `rate(inference_tokens_total[1m])` |

```bash
# Quick local access if LoadBalancer IP isn't routable from your machine
kubectl port-forward svc/grafana-service 3000:80
# Then open http://localhost:3000 (admin/admin)
```

---

## Probes & Readiness

The vLLM deployment uses a three-tier probe strategy to handle the slow model load time (~3–4 minutes):

| Probe | Path | Initial Delay | Period |
|---|---|---|---|
| `startupProbe` | `/health` | 120s | 15s (12 failures max = 180s window) |
| `readinessProbe` | `/health` | 240s | 30s |
| `livenessProbe` | `/health` | 300s | 20s |

This prevents Kubernetes from prematurely killing the pod during model weight loading, which is the most common cause of `CrashLoopBackOff` in GPU inference deployments.

---

## GPU Resource Allocation

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"     # Exclusive GPU access
    memory: 20G             # Overhead + KV cache
    cpu: "10"
  requests:
    nvidia.com/gpu: "1"
    memory: 6G
    cpu: "2"
```

The `shm` volume (`/dev/shm`, 4Gi) is required for vLLM's tensor-parallel shared memory communication, even for single-GPU setups.
