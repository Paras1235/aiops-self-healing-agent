from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import os
import json
import subprocess
import datetime
import time
from google.genai import Client
from google.genai import types

app = FastAPI(title="AIOps Self-Healing Agent")
client = Client()
incident_history = []

def log_incident(alert_name: str, status: str, diagnosis: str = "", command: str = "", execution_log: str = ""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    incident_entry = {
        "id": len(incident_history) + 1,
        "timestamp": timestamp,
        "alert_name": alert_name,
        "status": status,
        "diagnosis": diagnosis,
        "command": command,
        "execution_log": execution_log
    }
    incident_history.insert(0, incident_entry)
    return incident_entry

def execute_remediation(command: str, alert_name: str, diagnosis: str):
    print(f"[AUTOMATION] Attempting to run healing command: {command}")
    allowed_prefixes = ["kubectl get", "kubectl describe", "kubectl rollout restart"]
    if any(command.strip().startswith(prefix) for prefix in allowed_prefixes):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout if result.stdout else result.stderr
            print("\n========== AUTOMATED EXECUTION OUTPUT ==========")
            print(output)
            print("================================================\n")
            log_incident(alert_name, "Resolved", diagnosis, command, output)
        except Exception as e:
            error_msg = f"Failed during automated process: {str(e)}"
            log_incident(alert_name, "Failed", diagnosis, command, error_msg)
    else:
        reject_msg = "Security validation failed. Only read-only diagnostics and rollout restarts are automated."
        log_incident(alert_name, "Rejected", diagnosis, command, reject_msg)

def handle_local_fallback(alert_name: str, summary: str, original_error: str):
    """Local AIOps engine that takes over if cloud API limits are exhausted."""
    print(f"[LOCAL-ENGINE] Activating deterministic recovery rules for {alert_name}...")
    
    # Deterministic local rule engine mapping alerts to clean cluster paths
    fallback_map = {
        "TargetDown": {
            "diagnosis": "Unreachable target application app container metrics. Triggering an automated pipeline rollout reset locally (API Quota Fallback).",
            "command": "kubectl rollout restart deployment/aiops-target-app -n aiops"
        },
        "KubePodCrashLooping": {
            "diagnosis": "Node exporter daemon set container crashed. Collecting running node context diagnostic logs locally (API Quota Fallback).",
            "command": "kubectl describe daemonset kube-prometheus-stack-prometheus-node-exporter -n monitoring"
        },
        "KubeDaemonSetRolloutStuck": {
            "diagnosis": "Node-exporter rollout pipeline degradation detected. Issuing immediate cluster daemon rollout restart locally (API Quota Fallback).",
            "command": "kubectl rollout restart daemonset/kube-prometheus-stack-prometheus-node-exporter -n monitoring"
        }
    }
    
    rule = fallback_map.get(alert_name, {
        "diagnosis": f"Cluster anomaly alert received. Local rule engine running diagnostics check. Original API error: {original_error[:100]}",
        "command": "kubectl get pods -A"
    })
    
    execute_remediation(rule["command"], alert_name, rule["diagnosis"])

def analyze_with_ai(alert_name: str, summary: str, full_alert: dict):
    print(f"\n[AI-ANALYSIS] Requesting structured remediation from Gemini for {alert_name}...")
    
    prompt = f"""
    You are an expert AIOps SRE. Review this Kubernetes alert:
    Alert Name: {alert_name}
    Summary: {summary}
    Details: {full_alert}
    
    CRITICAL CLUSTER NAMING RULES:
    - The Node Exporter DaemonSet name is exactly: kube-prometheus-stack-prometheus-node-exporter
    - The Alertmanager StatefulSet name is exactly: alertmanager-kube-prometheus-stack-alertmanager
    - The namespace for monitoring components is exactly: monitoring
    - The namespace for the target application is exactly: aiops
    
    Provide a JSON response matching this schema:
    {{
        "diagnosis": "Brief explanation of root cause",
        "healing_command": "A single safe kubectl command to run (e.g., a rollout restart or specific get/describe check)"
    }}
    """
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Stagger out requests to keep free tier requests spaced out cleanly
            time.sleep(3)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            
            data = json.loads(response.text)
            diagnosis = data.get('diagnosis', 'No diagnosis provided')
            healing_command = data.get('healing_command', '')
            
            print("\n================= GEMINI AI DIAGNOSIS =================")
            print(f"DIAGNOSIS: {diagnosis}")
            print(f"PROPOSED ACTION: {healing_command}")
            print("========================================================\n")
            
            if healing_command:
                execute_remediation(healing_command, alert_name, diagnosis)
            return
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"[RETRY-ENGINE] Quota spike detected on attempt {attempt + 1}. Staggering fallback engine loop...")
                time.sleep(5)
            else:
                handle_local_fallback(alert_name, summary, error_str)
                return

    # If retries are completely exhausted, seamlessly drop into your local deterministic recovery routine
    handle_local_fallback(alert_name, summary, "Max API cloud rate limit retries exceeded.")

def analyze_and_heal(alert_payload: dict):
    alerts = alert_payload.get('alerts', [])
    status = alert_payload.get('status', 'unknown')
    for alert in alerts:
        alert_name = alert.get('labels', {}).get('alertname', 'Unknown')
        summary = alert.get('annotations', {}).get('summary', 'No summary')
        if status == "firing":
            analyze_with_ai(alert_name, summary, alert)

@app.post("/webhook")
async def receive_alert(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        background_tasks.add_task(analyze_and_heal, payload)
        return {"status": "success", "message": "Alert routed to engine."}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400

@app.get("/api/incidents")
async def get_incidents():
    return JSONResponse(content=incident_history)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AIOps Remediation Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');
            body { font-family: 'Inter', sans-serif; }
            pre, code { font-family: 'Fira Code', monospace; }
        </style>
    </head>
    <body class="bg-gray-950 text-gray-100 min-h-screen">
        <header class="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-50 px-6 py-4">
            <div class="max-w-7xl mx-auto flex justify-between items-center">
                <div class="flex items-center space-x-3">
                    <span class="text-2xl">🤖</span>
                    <div>
                        <h1 class="text-xl font-bold tracking-tight bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
                            AIOps Remediation Dashboard
                        </h1>
                        <p class="text-xs text-gray-400">Autonomous Self-Healing Agent Engine</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
                    <span class="text-xs text-gray-400 font-medium">Agent Active & Listening</span>
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto px-6 py-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div class="bg-gray-900 border border-gray-800 p-6 rounded-xl shadow-lg">
                    <h3 class="text-sm text-gray-400 font-medium uppercase tracking-wider mb-1">Total Webhooks Handled</h3>
                    <p id="total-count" class="text-3xl font-extrabold text-teal-400">0</p>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-6 rounded-xl shadow-lg">
                    <h3 class="text-sm text-gray-400 font-medium uppercase tracking-wider mb-1">Success Rate</h3>
                    <p id="success-rate" class="text-3xl font-extrabold text-emerald-400">100%</p>
                </div>
                <div class="bg-gray-900 border border-gray-800 p-6 rounded-xl shadow-lg">
                    <h3 class="text-sm text-gray-400 font-medium uppercase tracking-wider mb-1">Current Active Incident</h3>
                    <p id="active-status" class="text-3xl font-extrabold text-gray-400">None</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div class="lg:col-span-5 flex flex-col space-y-4">
                    <h2 class="text-lg font-bold text-gray-300 flex items-center space-x-2">
                        <span>📋</span> <span>Incident Remediation History</span>
                    </h2>
                    <div id="incident-list" class="space-y-3 overflow-y-auto max-h-[600px] pr-2">
                        <div class="text-center py-12 text-gray-500 border border-dashed border-gray-800 rounded-xl bg-gray-900/20">
                            Waiting for webhook activity... Trigger an alert to start.
                        </div>
                    </div>
                </div>

                <div class="lg:col-span-7">
                    <div class="sticky top-24 bg-gray-900 border border-gray-800 rounded-xl shadow-lg overflow-hidden h-[645px] flex flex-col">
                        <div class="border-b border-gray-800 bg-gray-950/50 px-6 py-4 flex justify-between items-center">
                            <h2 class="text-md font-bold text-gray-300">🔍 Live Diagnosis Details</h2>
                            <span id="detail-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase bg-gray-800 text-gray-400">Idle</span>
                        </div>
                        <div id="detail-body" class="p-6 overflow-y-auto flex-1 space-y-6">
                            <div class="flex flex-col items-center justify-center h-full text-gray-500">
                                <span class="text-4xl mb-3">💻</span>
                                <p>Select an incident from the history timeline to inspect its real-time remediation details.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>

        <script>
            let currentSelectedId = null;
            let loadedIncidents = [];

            async function fetchIncidents() {
                try {
                    const response = await fetch('/api/incidents');
                    const data = await response.json();
                    loadedIncidents = data;
                    renderDashboard();
                } catch (e) {
                    console.error("Dashboard failed to retrieve history feed:", e);
                }
            }

            function renderDashboard() {
                document.getElementById('total-count').innerText = loadedIncidents.length;
                const activeInc = loadedIncidents.find(i => i.status === 'Resolved');
                if (activeInc) {
                    document.getElementById('active-status').innerText = "CLEARED";
                    document.getElementById('active-status').className = "text-3xl font-extrabold text-emerald-400";
                }

                const listContainer = document.getElementById('incident-list');
                if (loadedIncidents.length === 0) return;

                listContainer.innerHTML = '';
                loadedIncidents.forEach(inc => {
                    const isActive = inc.id === currentSelectedId;
                    const card = document.createElement('div');
                    card.className = `p-4 rounded-xl border cursor-pointer transition-all duration-150 ${
                        isActive ? 'bg-gray-800 border-teal-500 shadow-md shadow-teal-500/10' : 'bg-gray-900 border-gray-800 hover:border-gray-700 hover:bg-gray-900/80'
                    }`;
                    card.onclick = () => selectIncident(inc.id);

                    const badgeColor = inc.status === 'Resolved' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400';

                    card.innerHTML = `
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-bold text-sm text-gray-200">${inc.alert_name}</h4>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}">${inc.status}</span>
                        </div>
                        <p class="text-xs text-gray-400 line-clamp-1 mb-2">${inc.diagnosis || 'Awaiting analysis...'}</p>
                        <div class="flex justify-between items-center text-[10px] text-gray-500">
                            <span>⏱️ ${inc.timestamp}</span>
                            <span class="font-mono text-teal-400">${inc.command ? 'Remediated' : 'Unresolved'}</span>
                        </div>
                    `;
                    listContainer.appendChild(card);
                });

                if (currentSelectedId !== null) {
                    updateDetails();
                } else if (loadedIncidents.length > 0) {
                    selectIncident(loadedIncidents[0].id);
                }
            }

            function selectIncident(id) {
                currentSelectedId = id;
                updateDetails();
            }

            function updateDetails() {
                const inc = loadedIncidents.find(i => i.id === currentSelectedId);
                const detailBody = document.getElementById('detail-body');
                const badge = document.getElementById('detail-badge');

                if (!inc) return;

                badge.innerText = inc.status;
                badge.className = `px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                    inc.status === 'Resolved' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                }`;

                detailBody.innerHTML = `
                    <div>
                        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Target Alert Name</h3>
                        <p class="text-lg font-bold text-gray-100 flex items-center space-x-2">
                            <span class="text-red-400">🚨</span>
                            <span>${inc.alert_name}</span>
                        </p>
                    </div>

                    <div>
                        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">🧠 AI Root Cause Diagnosis</h3>
                        <div class="bg-gray-950 p-4 rounded-lg border border-gray-800 text-sm text-gray-300 leading-relaxed">
                            ${inc.diagnosis}
                        </div>
                    </div>

                    <div>
                        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">⚙️ Executed Command</h3>
                        <div class="bg-gray-950 px-4 py-3 rounded-lg border border-gray-800 flex justify-between items-center">
                            <code class="text-teal-400 text-xs">${inc.command || 'None'}</code>
                            <span class="text-[10px] bg-teal-500/10 text-teal-400 px-2 py-0.5 rounded font-mono font-bold">Auto-Executed</span>
                        </div>
                    </div>

                    <div class="flex-1 flex flex-col">
                        <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">🖥️ Cluster Execution Terminal Output</h3>
                        <pre class="bg-gray-950 p-4 rounded-lg border border-gray-800 text-xs text-gray-300 overflow-x-auto flex-1 h-44 whitespace-pre-wrap leading-relaxed select-text">${inc.execution_log || 'No output captured.'}</pre>
                    </div>
                `;
            }

            fetchIncidents();
            setInterval(fetchIncidents, 2000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    uvicorn.run("agent:app", host="0.0.0.0", port=8080, reload=True)