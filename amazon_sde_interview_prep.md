# Amazon SDE Intern — Interview Prep: Rainference

---

## 1. Project Summary

Rainference is a **self-hosted, open-source LLM inference platform** that provides an **OpenAI-compatible API** for deploying and serving open-source models like Meta's LLaMA-3.1-8B-Instruct.  It solves the problem of vendor lock-in and cost opacity in managed LLM services (like the OpenAI API itself) by letting users run the entire stack on their own bare-metal Kubernetes infrastructure.  The backend is a **FastAPI** service that handles authentication (GitHub OAuth), API key management, token-level usage logging, and **Stripe-integrated metered billing**, backed by **PostgreSQL** for persistent state and **Redis** for low-latency token validation and session caching. The inference engine is **vLLM**, deployed as a Kubernetes pod with NVIDIA L4 GPU resources, exposed externally through **MetalLB** and **NGINX Ingress**.  A **React + Vite + Tailwind CSS** dashboard provides users a management UI for keys, billing, and usage analytics.

---

## 2. The Elevator Pitch (30–60 seconds)

> **Hook:**  
> "Every time a developer calls the OpenAI API, they're paying a premium for compute they could own, with zero visibility into what that cost is actually covering."
>
> **Action:**  
> "To solve that, I built Rainference — a fully open-source, self-hosted LLM inference stack. I set up a bare-metal Kubernetes cluster from scratch with an NVIDIA L4 GPU worker, deployed Meta's LLaMA-8B model using vLLM for high-throughput serving, and built a FastAPI backend that exposes an OpenAI-compatible API. I integrated a dual-layer data store — PostgreSQL for durable user and billing records, and Redis for sub-millisecond API key validation on every inference request. I also wired in Stripe for metered billing and built a React dashboard so users can manage keys, view token-level usage analytics, and add balance — all in one place."
>
> **Result:**  
> "The end result is a platform that gives developers the same `curl`-compatible interface they already know from OpenAI, but running entirely on infrastructure they control, with full cost transparency and built-in billing from day one."

---

## 3. Interview Q&A (Amazon Leadership Principles)

---

### Q1 · Technical Breadth — "Why did you choose PostgreSQL *and* Redis? Isn't that redundant?"

**LP Focus:** *Dive Deep*, *Deliver Results*

> **Model Answer:**
>
> They serve fundamentally different access patterns.
>
> **PostgreSQL** is the system of record. It stores durable, relational data: the `users` table (user_id, email, api keys, bearer tokens, balance) and the `logs` table (per-request token counts, spending, timestamps grouped by model). This data needs ACID guarantees — when a Stripe webhook fires and we credit a user's balance, that update must be atomic and durable. I use `psycopg`'s `AsyncConnectionPool` to manage connections efficiently under concurrent request load.
>
> **Redis** is the hot path cache. Every single inference request must validate the caller's API key and check their balance *before* we forward the prompt to the GPU. Doing a PostgreSQL round-trip for every request would add unacceptable latency to the inference pipeline. So, on user creation, I hash the API token data (`user_id`, `balance`) into a Redis hash at `llm_api_token:{token}`. Token validation becomes a single `HGETALL` — sub-millisecond.
>
> The trade-off is **consistency**: when a user's balance updates (e.g., after a Stripe payment), I must update *both* stores. I handle this by updating PostgreSQL first (source of truth), then writing to Redis. If Redis fails, the user might temporarily be denied service, but they'll never be overcharged — which is the safer failure mode.
>
> If I had infinite time, I'd add a reconciliation worker that periodically syncs Redis balances from PostgreSQL to handle any drift.

---

### Q2 · Technical Breadth — "Why vLLM over other serving solutions like Triton, TGI, or just raw PyTorch?"

**LP Focus:** *Dive Deep*, *Customer Obsession*

> **Model Answer:**
>
> The decision came down to three factors: **throughput**, **API compatibility**, and **operational simplicity**.
>
> vLLM implements **PagedAttention**, which manages the KV-cache like virtual memory pages. This is critical when you're serving an 8B parameter model on a single L4 GPU with only 24GB VRAM — naive KV-cache allocation wastes 60–80% of memory on fragmentation. PagedAttention lets vLLM serve significantly more concurrent requests with the same hardware.
>
> Second, vLLM ships a built-in **OpenAI-compatible server** (the `vllm/vllm-openai` Docker image). I invoke it with `vllm serve meta-llama/Llama-3.1-8B-Instruct --dtype half --max-model-len 1024`. This means my FastAPI backend can forward requests to the vLLM pod using the *exact same schema* that users send to the external API — model, messages, max_tokens, temperature, stream. No translation layer needed.
>
> NVIDIA Triton is more powerful for multi-model, multi-framework serving, but it's operationally complex — I'd need to write model configuration files, build custom inference backends, and manage an ensemble pipeline. For a single-model deployment, it was over-engineered. Hugging Face TGI was a close alternative, but at the time vLLM had better throughput benchmarks on LLaMA-class models and the OpenAI-compatible endpoint was a strong differentiator.
>
> The `--dtype half` flag tells vLLM to use FP16 precision, which halves the memory footprint compared to FP32 without meaningful quality degradation for inference. And `--max-model-len 1024` caps the context window to fit within the L4's VRAM budget.

---

### Q3 · Ownership — "You built the Kubernetes cluster from scratch. Walk me through *why* you didn't just use EKS or GKE managed Kubernetes."

**LP Focus:** *Ownership*, *Dive Deep*

> **Model Answer:**
>
> I used GCP VMs but set up Kubernetes manually (kubeadm) because the project's goal was to demonstrate *self-hosted* infrastructure — proving that an organization can run production LLM inference without being locked into a managed service's pricing and configuration constraints.
>
> A managed service like GKE abstracts away the control plane, but it also abstracts away things I needed to control directly:
>
> 1. **GPU scheduling**: I needed to install the NVIDIA device plugin, CUDA drivers, and container toolkit on the worker node myself so that Kubernetes could allocate `nvidia.com/gpu: "1"` to my vLLM pod. With GKE, you'd use their pre-built GPU node pools, but you lose visibility into driver versions and compatibility.
>
> 2. **Networking**: Since this is bare-metal (no cloud load balancer), I deployed **MetalLB** in Layer 2 mode to assign external IPs from an address pool I control. In GKE, `Service` type `LoadBalancer` automatically provisions a GCP load balancer — but that costs money per hour and hides the networking model. MetalLB taught me how ARP announcements work to attract traffic to a node.
>
> 3. **Cost**: A GKE control plane charges ~$75/month. For a side project, I wanted $0 overhead on the control plane.
>
> The downside is I own all the operational burden: etcd backups, API server availability, certificate rotation. For a production company, I'd absolutely recommend managed Kubernetes — but for this project, the learning and control justified the trade-off.

---

### Q4 · Deliver Results — "How did you handle payments? What happens if a Stripe webhook fails mid-flight?"

**LP Focus:** *Deliver Results*, *Dive Deep*

> **Model Answer:**
>
> I integrated **Stripe Checkout Sessions** for payments. The flow is:
>
> 1. The user clicks "Add Balance" in the React dashboard → selects an amount ($5, $25, $50, $100, or custom).
> 2. The frontend calls `POST /create-checkout-session` on my FastAPI backend, passing the amount and the user's bearer token.
> 3. My backend creates a Stripe Checkout Session with the user's `user_id` embedded in the session metadata, and returns the Stripe-hosted checkout URL.
> 4. The user completes payment on Stripe's page.
> 5. Stripe sends a `checkout.session.completed` webhook to my `POST /webhook` endpoint.
>
> In the webhook handler, I:
> - Verify the event signature using `stripe.Webhook.construct_event()` to prevent spoofed webhooks.
> - Extract `user_id` from the session metadata and `amount_total` from the event payload.
> - Read the current balance from PostgreSQL, add the payment amount, and `UPDATE` the new balance using a `RETURNING` clause to confirm the write.
> - Then update the Redis hash so subsequent inference requests immediately see the new balance.
>
> **Failure mode**: If Redis update fails after PostgreSQL succeeds, the user's balance in the hot cache is stale. The worst case is that inference requests get rejected temporarily because Redis shows a low/zero balance. But the source of truth (PostgreSQL) is correct, and when the user refreshes the dashboard (which reads from PostgreSQL), they see the right balance. This is a safe failure mode — we'd rather temporarily deny service than allow unpaid inference.
>
> If I were hardening this, I'd wrap the PostgreSQL + Redis updates in a compensating transaction pattern or use a transactional outbox to guarantee eventual consistency.

---

### Q5 · Conflict / Trade-offs — "You have both a WebSocket endpoint and an HTTP POST endpoint for `/v1/chat/completions`. Why both? When would you use one over the other?"

**LP Focus:** *Ownership*, *Dive Deep*

> **Model Answer:**
>
> The **HTTP POST** endpoint handles the standard request-response cycle — a client sends a prompt, gets a full JSON response back (or a streaming `StreamingResponse`). This is what you'd use from a `curl` command, a Python `requests` call, or any OpenAI SDK client. It's stateless and simple.
>
> The **WebSocket** endpoint serves a different use case: the React dashboard's chat interface. WebSockets give us a persistent, bidirectional connection. The user can send multiple prompts in a session without re-authenticating for each one, and the server can push tokens to the client as they're generated, enabling a real-time chat UX.
>
> The trade-off is complexity. The WebSocket path requires a `ConnectionManager` class to track active connections per API token, handle disconnects gracefully, and manage the lifecycle. The HTTP path is stateless and horizontally scalable — you can just add more FastAPI workers behind a load balancer. WebSockets require sticky sessions or a Redis pub/sub backplane if you scale out.
>
> For the MVP, both exist side-by-side because they serve different user personas: **developers** (who want a `curl`-compatible API) and **dashboard users** (who want a real-time chat experience). If I had to prioritize one, I'd keep the HTTP endpoint because it covers more use cases and is easier to scale.

---

### Q6 · Leadership Principle: Customer Obsession — "Why did you make the API OpenAI-compatible instead of designing your own schema?"

**LP Focus:** *Customer Obsession*, *Deliver Results*

> **Model Answer:**
>
> **Adoption friction is the death of developer tools.** If I designed a custom API schema, every potential user would need to read my docs, learn my request format, and rewrite their client code. That's a high barrier for what's essentially a commodity interface — send a prompt, get a completion.
>
> By matching the OpenAI `/v1/chat/completions` schema (model, messages, max_tokens, temperature, stream), any developer who has existing code calling `api.openai.com` can point it at my server by changing *just the base URL*. No code changes. OpenAI SDK clients, LangChain, LlamaIndex — they all work out of the box.
>
> This was also why I chose vLLM — its built-in server already speaks this protocol, so my backend is essentially a thin authentication and billing proxy in front of vLLM. I didn't have to write a translation layer, which means fewer bugs and less maintenance.
>
> The customer insight here is: developers don't want to learn your API. They want to use the API they already know. My job is to provide the same interface with better economics and full infrastructure control.

---

### Q7 · Dive Deep — "What was the hardest infrastructure problem you had to debug, and how did you solve it?"

**LP Focus:** *Dive Deep*, *Ownership*

> **Model Answer:**
>
> The hardest problem was **vLLM pod startup reliability**. An 8B parameter model in FP16 is roughly 16GB. When the pod starts, it downloads the model weights from Hugging Face (on first run) and loads them into GPU memory. On an L4 (24GB VRAM), this is tight.
>
> The initial problem: Kubernetes was killing the pod before the model finished loading. The default liveness probe was firing too early, seeing no response on `:8000/health`, and restarting the container — which would start the download *again*, creating an infinite restart loop.
>
> **How I solved it:**
>
> I configured **three-tier health checks** in the deployment manifest:
>
> 1. **`startupProbe`**: `initialDelaySeconds: 120`, `periodSeconds: 15`, `failureThreshold: 12`. This gives the pod up to **3 minutes** of initial delay plus **3 more minutes** of retries — a total of 6 minutes to download and load model weights before Kubernetes considers it failed. This is the critical one.
>
> 2. **`livenessProbe`**: `initialDelaySeconds: 300`, `periodSeconds: 20`. Only kicks in *after* the startup probe succeeds. Checks if the container is still responsive.
>
> 3. **`readinessProbe`**: `initialDelaySeconds: 240`, `periodSeconds: 30`. Controls when the pod is added to the Service's endpoint list — so traffic only flows once inference is actually ready.
>
> I also mounted a **PersistentVolume** at `/root/.cache/huggingface` (35Gi on host path) so that model weights are cached across pod restarts. After the first download, subsequent startups are dramatically faster (loading from local disk vs. network).
>
> Additionally, I allocated a **4Gi shared memory volume** (`emptyDir` with `medium: Memory`) mounted at `/dev/shm`. vLLM uses shared memory for tensor parallel inference and IPC between processes — the default 64Mi `/dev/shm` in Docker would cause silent failures.
>
> This whole debugging cycle taught me that GPU workloads have fundamentally different lifecycle characteristics than traditional web services, and Kubernetes' defaults are designed for the latter.

---

## Quick Reference: LP Mapping

| # | Question Topic | Primary LP | Secondary LP |
|---|---------------|------------|-------------|
| 1 | PostgreSQL + Redis dual-store | Dive Deep | Deliver Results |
| 2 | vLLM vs. alternatives | Dive Deep | Customer Obsession |
| 3 | Bare-metal K8s vs. managed | Ownership | Dive Deep |
| 4 | Stripe webhook payment flow | Deliver Results | Dive Deep |
| 5 | WebSocket vs. HTTP trade-off | Ownership | Dive Deep |
| 6 | OpenAI API compatibility | Customer Obsession | Deliver Results |
| 7 | GPU pod startup debugging | Dive Deep | Ownership |

---

> [!TIP]
> **Interview Meta-Strategy**: For every answer, follow the **STAR format** (Situation, Task, Action, Result). The model answers above are already structured this way. When you practice, focus on being concise in the *Situation/Task* (1-2 sentences) and detailed in the *Action/Result* — that's where you demonstrate depth.

> [!IMPORTANT]
> **Numbers sell.** Wherever possible, inject concrete metrics: "16GB model in FP16", "sub-millisecond Redis lookup", "6-minute startup window", "35Gi persistent volume". Interviewers remember specifics, not generalities.
