Autonomous AIOps Self-Healing Infrastructure PipelineAn event-driven automation framework that leverages Large Language Models (LLMs) to dynamically analyze real-time cluster telemetry and orchestrate safe, automated remediations for full-stack applications.📊 Performance ImpactManual SRE Intervention MTTR: ~15 MinutesAutonomous AIOps Agent MTTR: ~2.0 Seconds🏗️ System ArchitectureThe pipeline operates in an event-driven loop across four distinct operational layers:+---------------------------------------------------------+
|        1. ORCHESTRATION & TELEMETRY LAYER               |
|                                                         |
|   [ Local Kubernetes Cluster (Docker Desktop) ]         |
|                         │                               |
|                         ▼ (Metrics Scraped via Node)    |
|             [ Prometheus Monitoring Stack ]             |
+-------------------------┬-------------------------------+
                          │
                          │ (State Tracking: Firing Alert)
                          ▼
+---------------------------------------------------------+
|        2. ROUTING & INGESTION LAYER                     |
|                                                         |
|             [ Prometheus Alertmanager ]                 |
|                         │                               |
|                         ▼ (HTTP POST JSON Webhook)      |
|       [ Custom AIOps FastAPI Agent Engine ]             |
|                  (Port: 8080)                           |
+-------------------------┬-------------------------------+
                          │
                          ├────────────────────────┐
     (If Quota Available) │                        │ (If 429 Rate Throttled)
                          ▼                        ▼
+-----------------------------------+    +----------------------------------+
|      3A. PRIMARY COGNITION        |    |       3B. HYBRID FALLBACK        |
|                                   |    |                                  |
|   [ Gemini 2.5 Flash Cloud API ]  |    |   [ Local Rule Engine Fallback ] |
|    (Structured JSON Generation)   |    |  (Deterministic Matrix Mapping)  |
+-------------------------┬---------+    +----------------─┬────────────────+
                          │                                │
                          └────────────────────────┬───────┘
                                                   │
                                                   ▼ (Validates Prefix Whitelist)
+--------------------------------------------------┴----------------+
|        4. AUTOMATED EXECUTION & VISIBILITY LAYER                  |
|                                                                   |
|             [ Host Machine Secure Subprocess Runner ]             |
|                         │                                         |
|                         ├─► (Executes: kubectl rollout restart)   |
|                         │                                         |
|                         ▼ (In-Memory Database Sync)               |
|             [ Live Tailwind Web Operations UI Dashboard ]         |
|                         (http://localhost:8080/dashboard)         |
+-------------------------------------------------------------------+
🛠️ Key Technical Implementations1. Structured AI ResponsesConfigured execution parameters with strict schema enforcement (response_mime_type="application/json"). This forces the LLM to reply exclusively with machine-readable, deterministic triage objects containing clear diagnosis keys and specific shell remediation fields.2. Idempotent Security Guardrail LayerTo protect the target server host environment from unverified or destructive behaviors, an isolation validator intercepts generated scripts. Execution is strictly restricted to pre-authorized prefixes:kubectl getkubectl describekubectl rollout restartAny unauthorized operations (e.g., resource deletion attempts) are intercepted, safely blocked, and flagged as Rejected for tracking.3. High-Availability Fallback ModuleDesigned to absorb API cloud rate throttling bottlenecks (429 Resource Exhausted) gracefully during high-density alert storms. If the cloud gateway fails or hits quota limits, the agent immediately routes tasks through a deterministic local lookup matrix to guarantee continuous system availability.🚀 Quick Start GuidePrerequisitesPython 3.10+Local Kubernetes Cluster (Docker Desktop)Active Google Gemini API KeyInstallation & Local SetupClone the repository:git clone https://github.com/Paras1235/aiops-self-healing-agent.git
cd aiops-self-healing-agent/aiops-agent
Install dependencies:pip install -r requirements.txt
Configure the environment and boot the agent:$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
python agent.py
Access the Operations Center UI:Open your browser and navigate to http://localhost:8080/dashboard🧪 Triggering a Simulation TestTo simulate an incident and view the automated remediation cycle, fire a mock TargetDown payload to the webhook gateway endpoint using PowerShell:$payload = @{
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
