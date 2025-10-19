"""
Pipeline: Monitor Agent -> Diagnostic Agent -> Solution Agent
Monitor collects network metrics, Diagnostic analyzes them, Solution provides fixes
"""
import json
import sys
sys.path.insert(0, '/home/admin/Documents/crewai_starter/agents')

from monitor_agent import NetworkMonitor
from diagnostic_agent_working import WorkingDiagnosticAgent
from solution_agent import SolutionAgent
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

# Step 7: Generate AI solutions
print("\n🚀 STEP 7: Generating AI-powered solutions...")
solution_agent = SolutionAgent(llm)
solutions = solution_agent.generate_solutions(diagnosis)

# Step 8: Print solutions
solution_agent.print_solutions(solutions)

print("\n✅ Pipeline complete!")
print("="*70)
print("SUMMARY: Monitor → Diagnostic → Solution")
print(f"  • Network Status: {alert['status']}")
print(f"  • Root Cause: {diagnosis['root_cause'][:60]}...")
solutions_list = solutions.get('solutions', {}).get('solutions_list', [])
if solutions_list:
    print(f"  • Top Recommendation: {solutions_list[0][:60]}...")
else:
    print(f"  • Recommendations: See AI solutions above")
print("="*70)

