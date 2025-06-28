# Rainference

A self-hosted inference stack for open-source LLMs, serving as a practical alternative to proprietary platforms.

## Overview

Rainference is a fully open-source and self-hostable inference stack providing an OpenAI-compatible API for large language models like LLaMA-8B. It is engineered to run on your own bare-metal infrastructure, offering complete control over your AI stack.

This solution is deployed on a Kubernetes cluster built from the ground up on standard CPU and GPU machines. The setup involves the direct installation of the operating system, container runtime, and essential components like NVIDIA drivers and CUDA libraries to enable hardware acceleration for inference workloads. For networking, MetalLB provides robust load-balancing, exposing the API to external traffic on your private cluster.

The model serving itself is powered by the high-performance vLLM engine. The platform is managed through a clean dashboard built with React and Tailwind CSS, which communicates with a FastAPI backend to provide API key management, usage tracking, and Stripe-integrated billing.

## Key Features

*   **Inference API**: High-throughput LLM inference powered by `vLLM`, compatible with the OpenAI API format.
*   **Usage Analytics**: Tracks token-level usage with visualizations in the user dashboard.
*   **API Key Management**: Issue, view, and rotate API keys directly from the user interface.
*   **Stripe Billing Integration**: Built-in support for metered billing and managing account balances.
*   **Lightweight UI**: A fast and responsive dashboard built with Vite, React, and Tailwind CSS.

## Tech Stack

| Component           | Technology                                                    |
| ------------------- | ------------------------------------------------------------- |
| **Infrastructure**  | GCP (L4 GPU), Kubernetes (custom master + GPU worker), MetalLB |
| **Model Serving**   | `vLLM` on LLaMA-8B                                            |
| **Backend**         | Python, FastAPI                                               |
| **Frontend**        | React, Vite, Tailwind CSS                                     |
| **Billing**         | Stripe                                                        |

## Repository Layout

```plaintext
Rainference/
├── backend/        # FastAPI service (API routers, auth, inference, payments)
├── frontend/       # React dashboard (UI pages, components)
├── k8s/            # Kubernetes manifests (deployments, services, configs)
├── k8s-setup.sh    # Cluster bootstrap and MetalLB setup script
└── README.md       # This file
```

## Quickstart

Follow these steps to deploy and run Rainference.

### 1. Kubernetes Deployment

The k8s-setup.sh script deploys all necessary Kubernetes resources—including volumes, configurations, services, deployments, secrets and ingress—in the correct order.

```bash
# Apply all Kubernetes manifests in one go
./k8s-setup.sh
```


### 2. Launch Backend

Navigate to the backend directory, install dependencies, and start the FastAPI server.

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Start Frontend

In a separate terminal, navigate to the frontend dashboard directory, install dependencies, and start the development server.

```bash
cd frontend/dashboard
npm install
npm run dev
```

You can now access the UI by visiting the external IP address assigned by MetalLB or `http://localhost:5173`.

## Environment Configuration

Before running, create `.env` files in the `backend` and `frontend/dashboard` directories by copying the examples below.

### Backend (`backend/.env`)

```env
GITHUB_CLIENT_ID=<your_github_client_id>
GITHUB_CLIENT_SECRET=<your_github_client_secret>
STRIPE_SECRET_KEY=<your_stripe_secret_key>
STRIPE_PUBLISHABLE_KEY=<your_stripe_publishable_key>
STRIPE_ENDPOINT_SECRET=<your_stripe_endpoint_secret>
STRIPE_PRODUCT_ID=<your_stripe_product_id>
KUBE_SERVER_URL=<your_kube_server_url>
POSTGRESS_PASSWD=<your_postgres_password>
CORS_ORIGINS=<your_cors_origins>
FRONTEND_URL=<your_frontend_url>

```

### Frontend (`frontend/dashboard/.env`)

For Vite, environment variables must be prefixed with `VITE_`.

```env
VITE_GITHUB_CLIENT_ID=<your_github_client_id>
VITE_BACKEND_URL=<your_backend_url>
STRIPE_SECRET_KEY=<your_stripe_secret_key>
VITE_STRIPE_PUBLISHABLE_KEY=<your_stripe_publishable_key>
VITE_STRIPE_ENDPOINT_SECRET=<your_stripe_endpoint_secret>
VITE_FRONTEND_URL=<your_frontend_url>
```

## API Usage Example

Interact with the inference API using a `curl` request. Replace the placeholder authorization token with a valid API key from your dashboard.

**Local Development**

This example targets the backend server running locally.

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer " \
-d '{
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "messages": [
    {"role": "user", "content": "What is the renaissance of an intelligent being?"}
  ],
  "stream": false,
  "max_tokens": 100,
  "temperature": 0.7
}'
```

**Hosted Deployment**

Once deployed, replace the local URL with your service's external IP or domain name.

```bash
curl -X POST https://api.your-rainference-domain.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer " \
-d '{
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "messages": [
    {"role": "user", "content": "What is the renaissance of an intelligent being?"}
  ],
  "stream": false
}'
```

## Contributing

Contributions are welcome! Please feel free to raise issues or submit pull requests with any improvements.

## License

This project is licensed under the Apache License 2.0.