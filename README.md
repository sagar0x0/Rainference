# Rainference

> A production-grade, self-hosted LLM inference platform with OpenAI-compatible API, token-metered billing, Kubernetes-native secret management, and full observability — deployed on bare-metal GCP GPU infrastructure.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## Overview

Rainference is a vertically integrated LLM serving platform built entirely on self-managed infrastructure. Rather than wrapping a managed inference API, this system runs the full stack: bare-metal OS provisioning, GPU driver installation, Kubernetes cluster initialization, high-throughput model serving via vLLM, and a token-metered FastAPI gateway all on a single-node GCP instance with an NVIDIA L4 GPU.

The platform exposes an **OpenAI-compatible API** (`/v1/chat/completions`), enabling drop-in compatibility with any client built against the standard spec. Access is gated by per-user API keys stored in Redis for sub-millisecond validation and persisted in PostgreSQL for auditability. Credits are tracked at the token level, with Stripe handling real-money top-ups.

A Prometheus + Grafana observability stack runs in-cluster, scraping vLLM's native metrics endpoint to surface request latency, token throughput, and GPU utilization enabling proactive detection of serving degradation before users notice.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         GCP Instance (L4 GPU)                          │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Kubernetes Cluster (v1.29)                   │  │
│  │                                                                 │  │
│  │  ┌────────────┐   ┌────────────────┐   ┌──────────────────┐   │  │
│  │  │  Frontend  │   │  FastAPI       │   │  vLLM            │   │  │
│  │  │  (React)   │──▶│  Gateway       │──▶│  (LLaMA-3.1-8B)  │   │  │
│  │  │            │   │  /v1/chat/...  │   │  NVIDIA L4 GPU   │   │  │
│  │  └────────────┘   └───────┬────────┘   └──────────────────┘   │  │
│  │                           │                                     │  │
│  │                    ┌──────┴──────┐                             │  │
│  │                    │             │                             │  │
│  │               ┌────▼───┐   ┌────▼──────┐                     │  │
│  │               │ Redis  │   │ PostgreSQL │                     │  │
│  │               │(cache) │   │ (state)   │                     │  │
│  │               └────────┘   └───────────┘                     │  │
│  │                                                                 │  │
│  │  ┌────────────────────────────────────┐                        │  │
│  │  │  Monitoring                        │                        │  │
│  │  │  Prometheus ──── Grafana Dashboard │                        │  │
│  │  └────────────────────────────────────┘                        │  │
│  │                                                                 │  │
│  │  MetalLB (L2 mode) — external LoadBalancer on bare-metal       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### Design Decisions

| Decision | Rationale |
|---|---|
| **vLLM over TGI** | Paged attention gives better memory efficiency and higher throughput under concurrent load |
| **Redis for credit cache** | Sub-millisecond token balance lookups on the hot path PostgreSQL is authoritative but too slow for per-request validation |
| **MetalLB L2 mode** | Assigns real IPs to `LoadBalancer` services on bare-metal without a cloud load balancer zero extra cost |
| **Kubernetes Secrets for credentials** | Decouples lifecycle of API keys and DB credentials from the application image and runtime environment |
| **Prometheus scrape annotations** | Zero-config scraping of vLLM's native `/metrics` no sidecars, no service monitors required |

---

## Repository Structure

```
Rainference/
├── backend/                    # FastAPI inference gateway
│   ├── app/
│   │   ├── main.py             # App factory: DB pools, CORS, /metrics mount
│   │   ├── metrics.py          # prometheus_client instrumentation
│   │   └── routers/
│   │       ├── auth.py         # GitHub OAuth, bearer token issuance
│   │       ├── inference.py    # /v1/chat/completions, token metering
│   │       ├── payments.py     # Stripe webhook, credit top-up
│   │       └── users.py        # User info, API key management
│   ├── database/
│   │   └── db.py               # Async psycopg connection pool, Redis client
│   └── requirements.txt
├── frontend/                   # React dashboard (Vite + Tailwind)
├── k8s/                        # All Kubernetes manifests
│   ├── config/
│   │   ├── backend-secrets.yaml    # K8s Secret for all API credentials
│   │   ├── hf-token-secret.yaml    # Hugging Face hub token
│   │   ├── metallb-config.yaml     # MetalLB IP pool
│   │   └── l2adv.yaml              # MetalLB L2 advertisement
│   ├── deployments/
│   │   ├── llama-8b-deployment.yaml   # vLLM pod (GPU, PVC, probes)
│   │   └── backend-deployment.yaml    # FastAPI pod (secretRef env injection)
│   ├── monitoring/
│   │   ├── prometheus-configmap.yaml      # Scrape configs
│   │   ├── prometheus-deployment.yaml     # Prometheus server + RBAC
│   │   ├── prometheus-service.yaml
│   │   ├── grafana-configmap.yaml         # Datasource provisioning
│   │   ├── grafana-dashboard-configmap.yaml  # Pre-built dashboard JSON
│   │   └── grafana-deployment.yaml        # Grafana + LoadBalancer service
│   ├── services/
│   ├── volumes/
│   └── ingress/
├── scripts/
│   └── cluster-bootstrap.sh    # Full node provisioner (OS → K8s → GPU)
└── k8s-setup.sh                # Manifest apply orchestrator
```

---

## Infrastructure: Bare-Metal Provisioning

The cluster runs on a **single GCP `g2-standard-8` instance** (8 vCPU, 32GB RAM, 1x NVIDIA L4 GPU). The entire software stack from the OS up to Kubernetes is provisioned by `scripts/cluster-bootstrap.sh`:

1. **OS configuration** — swap disabled, kernel modules (`overlay`, `br_netfilter`) loaded, sysctl tuned for container networking
2. **Container runtime** — `containerd` with `SystemdCgroup = true` (required for K8s 1.29+)
3. **Kubernetes v1.29** — `kubeadm init` with `10.244.0.0/16` pod CIDR, control-plane taint removed for single-node scheduling
4. **NVIDIA driver v535** — installed via `ubuntu-drivers`, no reboot loop required at this version
5. **NVIDIA Container Toolkit** — `nvidia-ctk runtime configure --runtime=containerd`, enables GPU passthrough into pods
6. **Flannel CNI** — applied immediately post-init
7. **MetalLB** — installed via upstream manifest, then configured via `k8s/config/`

```bash
# Full provision from a raw Ubuntu 22.04 node
sudo bash scripts/cluster-bootstrap.sh

# Re-deploy manifests on an existing cluster
bash k8s-setup.sh --skip-init
```

---

## Observability

The monitoring stack runs in-cluster alongside the inference workloads.

### Metrics

**vLLM native metrics** (scraped from `:8000/metrics`):

| Metric | Description |
|---|---|
| `vllm:e2e_request_latency_seconds` | End-to-end request latency histogram |
| `vllm:tokens_total` | Cumulative prompt + generation token count |
| `vllm:request_success_total` | Completed request counter |
| `DCGM_FI_DEV_GPU_UTIL` | GPU compute utilization (%) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | GPU memory bandwidth utilization |

**FastAPI gateway metrics** (from `backend/app/metrics.py`):

| Metric | Type | Labels |
|---|---|---|
| `inference_request_latency_seconds` | Histogram | `model` |
| `inference_tokens_total` | Counter | `type={prompt,completion}`, `model` |
| `inference_requests_total` | Counter | `status={success,error}`, `model` |
| `active_api_keys_total` | Gauge | — |

### Grafana

Grafana is provisioned automatically with a pre-built dashboard (via ConfigMap). Access it at the MetalLB-assigned LoadBalancer IP on port `80`.

Key dashboard panels:
- Token throughput (tokens/sec, sliding 1m window)
- P99 request latency (5m rate)
- GPU utilization over time
- FastAPI error rate by status code

---

## API

The gateway exposes an **OpenAI-compatible** endpoint. Any client that works with the OpenAI SDK works here.

```bash
curl -X POST http://<your-cluster-ip>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Explain paged attention."}],
    "max_tokens": 256,
    "temperature": 0.7,
    "stream": false
  }'
```

### Authentication & Billing Flow

1. **GitHub OAuth** → user authenticates, a `bearer_token` and `llm_api_token` are generated and stored in Redis + PostgreSQL
2. **Per-request validation** → `validate_token()` does a Redis `HGETALL` on `llm_api_token:<token>` to check balance in O(1)
3. **Token metering** → after each non-streaming response, `prompt_tokens` and `completion_tokens` from the vLLM usage object are counted and logged to Redis, then periodically flushed to PostgreSQL
4. **Top-up** → Stripe webhook credits the user's balance in both Redis and PostgreSQL atomically

---

## Secret Management

All sensitive credentials are stored as Kubernetes Secrets and injected into pods via `envFrom.secretRef` no plaintext values in environment files or image layers.

```yaml
# k8s/config/backend-secrets.yaml (template — replace values before apply)
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
type: Opaque
stringData:
  POSTGRESS_PASSWD: "<your-postgres-password>"
  GITHUB_CLIENT_SECRET: "<your-github-secret>"
  STRIPE_SECRET_KEY: "<your-stripe-key>"
  ...
```

The backend Deployment loads all keys via:
```yaml
envFrom:
  - secretRef:
      name: backend-secrets
```

---

## Environment Configuration

For local development outside Kubernetes, create a `backend/.env`:

```env
GITHUB_CLIENT_ID=<your_github_client_id>
GITHUB_CLIENT_SECRET=<your_github_client_secret>
STRIPE_SECRET_KEY=<your_stripe_secret_key>
STRIPE_PUBLISHABLE_KEY=<your_stripe_publishable_key>
STRIPE_ENDPOINT_SECRET=<your_stripe_endpoint_secret>
STRIPE_PRODUCT_ID=<your_stripe_product_id>
KUBE_SERVER_URL=http://localhost:8001/v1/completions
POSTGRESS_PASSWD=<your_postgres_password>
CORS_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

For the frontend (`frontend/dashboard/.env`):
```env
VITE_GITHUB_CLIENT_ID=<your_github_client_id>
VITE_BACKEND_URL=<your_backend_url>
VITE_STRIPE_PUBLISHABLE_KEY=<your_stripe_publishable_key>
VITE_FRONTEND_URL=http://localhost:5173
```

---

## Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend/dashboard
npm install && npm run dev
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).