"""
Pipeline: Monitor Agent -> Diagnostic Agent
Monitor collects network metrics, Diagnostic analyzes them
"""
import json
import sys
sys.path.insert(0, '/home/admin/Documents/crewai_starter/agents')

from monitor_agent import NetworkMonitor
from diagnostic_agent_working import WorkingDiagnosticAgent
from crewai import LLM

print("="*70)
print("NETWORK MONITORING & DIAGNOSTIC PIPELINE")
print("="*70)

# Step 1: Initialize Monitor Agent
print("\n📡 STEP 1: Initializing Monitor Agent...")
llm = LLM(model='ollama/qwen2.5:0.5b', base_url='http://localhost:11434')
monitor = NetworkMonitor(llm, interface='wlan0')

# Step 2: Collect network metrics
print("\n📊 STEP 2: Collecting network metrics from Monitor Agent...")
alert = monitor.check_once()
monitor.print_status(alert)

# Print the full monitor response
print("\n" + "="*70)
print("📋 MONITOR AGENT RESPONSE (Full Alert Object)")
print("="*70)
print(json.dumps(alert, indent=2))
print("="*70)

# Step 3: Pass to Diagnostic Agent
print("\n🔬 STEP 3: Passing alert to Diagnostic Agent...")
diagnostic = WorkingDiagnosticAgent(interface='wlan0')

# Step 4: Run diagnosis
diagnosis = diagnostic.diagnose(alert)

# Step 5: Print diagnostic tool results
print("\n" + "="*70)
print("🔧 DIAGNOSTIC TOOLS RESPONSES (Raw Data)")
print("="*70)
if 'diagnostic_data' in diagnosis:
    for tool_name, tool_result in diagnosis['diagnostic_data'].items():
        print(f"\n📦 {tool_name.upper()}:")
        print(json.dumps(tool_result, indent=2))
print("="*70)

# Step 6: Print final diagnosis
diagnostic.print_diagnosis(diagnosis)

print("\n✅ Pipeline complete!")

