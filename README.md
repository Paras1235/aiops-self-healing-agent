# 🤖 Autonomous AIOps Self-Healing Infrastructure Pipeline

An event-driven automation framework that leverages Large Language Models (LLMs) to dynamically analyze real-time cluster telemetry and orchestrate safe, automated remediations for full-stack deployments on Kubernetes.

---

## 📊 Performance Impact

* Ingestion Delay: Manual SRE Intervention takes 1 to 5 Minutes (Email/Slack check) vs Custom Automated AIOps Engine which is Immediate (~0.1 Seconds).
* Diagnosis Time: Manual SRE Intervention takes 5 to 15 Minutes (Log Inspection) vs Custom Automated AIOps Engine which takes ~1.5 Seconds (Gemini Engine).
* Execution Speed: Manual SRE Intervention takes 1 to 2 Minutes (Manual Shell Input) vs Custom Automated AIOps Engine which takes ~0.4 Seconds (Subprocess Engine).
* Total Target MTTR: Manual SRE Intervention takes ~15 Minutes vs Custom Automated AIOps Engine which takes ~2.0 Seconds.

---

## 🏗️ System Architecture & Data Flow

The self-healing pipeline operates in a closed-loop design across four logical operational layers:

Layer 1: ORCHESTRATION & TELEMETRY LAYER

* Local Kubernetes Cluster (Docker Desktop) monitors infrastructure.
* Metrics are scraped via Node and sent to the Prometheus Monitoring Stack.

Layer 2: ROUTING & INGESTION LAYER

* State Tracking sends a Firing Alert to Prometheus Alertmanager.
* Alertmanager dispatches an HTTP POST JSON Webhook to the Custom AIOps FastAPI Agent Engine running on Port 8080.

Layer 3: COGNITION & DECISION ENGINE

* If Cloud Quota is Available: Sent to 3A. PRIMARY COGNITION via the Gemini 2.5 Flash Cloud API to generate structured JSON.
* If 429 Rate Throttled: Automatically routes to 3B. HYBRID FALLBACK via the Local Rule Engine Fallback using a deterministic matrix mapping.

Layer 4: AUTOMATED EXECUTION & VISIBILITY LAYER

* The engine validates the command using a strict prefix whitelist.
* The Host Machine Secure Subprocess Runner executes the script (e.g., kubectl rollout restart).
* An In-Memory Database Sync populates the Live Tailwind Web Operations UI Dashboard at http://localhost:8080/dashboard.

---

## 🛡️ Production-Grade Core Implementations

1. Structured Triage Parsing
The AI engine utilizes the Google GenAI SDK running gemini-2.5-flash with a strictly configured schema parameter (response_mime_type="application/json"). This enforces strict compliance, forcing the LLM to output a clean, parsable JSON structure containing a detailed diagnosis description and a targeted remediation execution script with zero conversational filler.
2. Idempotent Security Guardrails
To prevent arbitrary command injection or destructive actions (such as rm -rf or cluster-wide deletions), the host subprocess runner filters all incoming commands against an explicit security prefix whitelist containing only "kubectl get", "kubectl describe", and "kubectl rollout restart". Any command violating these bounds is blocked, logged securely to the dashboard database, and flagged as "Rejected" to preserve system safety.
3. Dual-Engine Resilience (Hybrid Fallback)
To absorb cloud quota constraints or API network timeouts (429 Resource Exhausted) during intense cluster alert storms, the system features a local fallback matrix. If the cloud-connected gateway becomes unavailable, the agent seamlessly drops to a local deterministic rule table to restore target apps without downtime.

---

## 🛠️ Tech Stack Specs

* Orchestration: Docker Desktop, local Kubernetes (k8s)
* Observability: Prometheus, Alertmanager
* Backend Server: FastAPI, Uvicorn, Python 3.11+
* Intelligence: Gemini 2.5 Flash API
* User Interface: HTML5, CSS3 (Tailwind CSS CDN), Vanilla JavaScript EventSource

---

## 🚀 Quick Start Guide

Setup & Prerequisites:

* An active Google Gemini API Key.
* PowerShell or a Unix terminal with kubectl configured to talk to your local cluster.

1. Installation
Clone the repository and install the backend server dependencies:
git clone [https://github.com/Paras1235/aiops-self-healing-agent.git](https://github.com/Paras1235/aiops-self-healing-agent.git)
cd aiops-self-healing-agent/aiops-agent
pip install -r requirements.txt
2. Launch the Application Server
Run the following PowerShell commands to declare your AI API Key and start up the self-healing background workers:
$env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
python agent.py
(Note: Make sure your terminal displays "Application startup complete" on port 8080.)
3. Open the Operations Room
Access the dashboard by opening your browser of choice and pointing to http://localhost:8080/dashboard.

---

## 🧪 Simulating an Incident Test Run

To test the self-healing loop under clean conditions, open a separate terminal tab and simulate an Alertmanager TargetDown webhook call using this payload:

$payload = @{
status = "firing"
alerts = @(
@{
labels = @{
alertname = "TargetDown"
severity = "warning"
namespace = "aiops"
}
annotations = @{
summary = "The endpoint for aiops-target-app is unreachable on port 8000."
}
}
)
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://localhost:8080/webhook" -Method POST -Body $payload -ContentType "application/json" -UseBasicParsing

Verify that the dashboard instantly increments the handled webhooks count and displays a live "Resolved" card indicating that the cluster pods have been automatically restarted!

## 🛡️ Production-Grade Core Implementations

### 1. Structured Triage Parsing

The AI engine utilizes the Google GenAI SDK running `gemini-2.5-flash` with a strictly configured schema parameter (`response_mime_type="application/json"`). This enforces strict compliance, forcing the LLM to output a clean, parsable JSON format with zero conversational filler:

```json
{
  "diagnosis": "Detailed root-cause analysis description",
  "healing_command": "Targeted remediation execution script"
}

```

### 2. Idempotent Security Guardrails

To prevent arbitrary command injection or destructive actions (such as `rm -rf` or cluster-wide deletions), the host subprocess runner filters all incoming commands against an explicit security prefix whitelist:

* `kubectl get`
* `kubectl describe`
* `kubectl rollout restart`

Any command violating these bounds is blocked, logged securely to the dashboard database, and flagged as `Rejected` to preserve system safety.

### 3. Dual-Engine Resilience (Hybrid Fallback)

To absorb cloud quota constraints or API network timeouts (`429 Resource Exhausted`) during intense cluster alert storms, the system features a local fallback matrix. If the cloud-connected gateway becomes unavailable, the agent seamlessly drops to a local deterministic rule table to restore target apps without downtime.

---

## 🛠️ Tech Stack Specs

* **Orchestration:** Docker Desktop, local Kubernetes (k8s)
* **Observability:** Prometheus, Alertmanager
* **Backend Server:** FastAPI, Uvicorn, Python 3.11+
* **Intelligence:** Gemini 2.5 Flash API
* **User Interface:** HTML5, CSS3 (Tailwind CSS CDN), Vanilla JavaScript EventSource

---

## 🚀 Quick Start Guide

### Setup & Prerequisites

* An active Google Gemini API Key.
* PowerShell or a Unix terminal with `kubectl` configured to talk to your local cluster.

### 1. Installation

Clone the repository and install the backend server dependencies:

```bash
git clone [https://github.com/Paras1235/aiops-self-healing-agent.git](https://github.com/Paras1235/aiops-self-healing-agent.git)
cd aiops-self-healing-agent/aiops-agent
pip install -r requirements.txt

```

### 2. Launch the Application Server

Run the following PowerShell commands to declare your AI API Key and start up the self-healing background workers:

```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY_HERE"
python agent.py

```

*Note: Make sure your terminal displays `Application startup complete` on port 8080.*

### 3. Open the Operations Room

Access the dashboard by opening your browser of choice and pointing to:
👉 **`http://localhost:8080/dashboard`**

---

## 🧪 Simulating an Incident Test Run

To test the self-healing loop under clean conditions, open a separate terminal tab and simulate an Alertmanager `TargetDown` webhook call using this payload:

```powershell
$payload = @{
    status = "firing"
    alerts = @(
        @{
            labels = @{
                alertname = "TargetDown"
                severity = "warning"
                namespace = "aiops"
            }
            annotations = @{
                summary = "The endpoint for aiops-target-app is unreachable on port 8000."
            }
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://localhost:8080/webhook" -Method POST -Body $payload -ContentType "application/json" -UseBasicParsing

```

