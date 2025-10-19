"""
Flask API Wrapper for Network Monitoring Agents
Exposes CrewAI agents as REST endpoints for React frontend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json

# Import your existing agents
from monitor_agent import NetworkMonitor
from diagnostic_agent_working import WorkingDiagnosticAgent

# Import CrewAI LLM
from crewai import LLM

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize LLM (using Ollama)
try:
    llm = LLM(model='ollama/qwen2.5:0.5b', base_url="http://localhost:11434")
    print("✅ LLM initialized")
except Exception as e:
    print(f"⚠️  LLM initialization failed: {e}")
    llm = None

# Initialize agents
monitor = NetworkMonitor(llm, interface="wlan0") if llm else None
diagnostic = WorkingDiagnosticAgent(interface="wlan0", llm=llm)

print("✅ Flask API initialized with CrewAI agents")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/monitor', methods=['GET'])
def get_monitor_status():
    """
    Endpoint 1: Get current network status
    Uses your Monitor Agent to check network health
    """
    try:
        if not monitor:
            # Fallback if LLM not available
            return jsonify({
                "timestamp": datetime.now().isoformat(),
                "status": "unknown",
                "error": "Monitor agent not initialized"
            }), 500
        
        # Use your existing monitor agent
        analysis = monitor.check_once()
        
        # Transform to frontend format
        response = {
            "timestamp": analysis['timestamp'],
            "status": analysis['status'],
            "metrics": {
                "ping": analysis['metrics']['ping'],
                "signal": analysis['metrics']['signal']
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in /api/monitor: {e}")
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/diagnose', methods=['POST'])
def run_full_pipeline():
    """
    Endpoint 2: Run FULL PIPELINE - Monitor → Diagnostic → Solution
    Just like run_pipeline.py but returns JSON
    """
    try:
        print("\n" + "="*70)
        print("🚀 RUNNING FULL DIAGNOSTIC PIPELINE VIA API")
        print("="*70)
        
        # STEP 1: Monitor - Get current network status
        print("\n📡 STEP 1: Monitor Agent - Collecting metrics...")
        if not monitor:
            return jsonify({"error": "Monitor agent not available"}), 500
        
        alert = monitor.check_once()
        print(f"   Status: {alert['status']}")
        
        # STEP 2: Diagnostic - Run all tools + AI scoring
        print("\n🔬 STEP 2: Diagnostic Agent - Running tools...")
        diagnosis = diagnostic.diagnose(alert)
        print(f"   Issue: {diagnosis.get('primary_issue')}")
        print(f"   Health Score: {diagnosis.get('network_health_score', 'N/A')}/100")
        
        # STEP 3: Solution - Generate recommendations
        print("\n💡 STEP 3: Solution Agent - Generating recommendations...")
        from solution_agent import SolutionAgent
        solution_agent = SolutionAgent(llm) if llm else None
        
        if solution_agent:
            solutions = solution_agent.generate_solutions(diagnosis)
            solution_list = solutions.get('solutions', {}).get('solutions_list', [])
        else:
            # Fallback to diagnostic recommendations
            solution_list = diagnosis.get('recommendations', [])
        
        print(f"   Generated {len(solution_list)} solutions")
        
        # Build comprehensive response
        response = {
            "timestamp": diagnosis['timestamp'],
            "pipeline_complete": True,
            
            # Monitor data
            "monitor": {
                "status": alert['status'],
                "metrics": alert['metrics']
            },
            
            # Diagnostic data  
            "diagnosis": {
                "primary_issue": diagnosis.get('primary_issue'),
                "root_cause": diagnosis.get('root_cause'),
                "confidence": diagnosis.get('confidence'),
                "evidence": diagnosis.get('evidence', []),
                "health_score": diagnosis.get('network_health_score'),
                "score_explanation": diagnosis.get('score_explanation'),
                "diagnostic_data": diagnosis.get('diagnostic_data', {})
            },
            
            # Solution data
            "solutions": {
                "recommendations": solution_list[:7],  # Top 7 unique solutions
                "total": len(solution_list)
            }
        }
        
        print("\n✅ Pipeline complete!")
        print("="*70)
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in pipeline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Pipeline failed",
            "message": str(e),
            "pipeline_complete": False
        }), 500


@app.route('/api/fix', methods=['POST'])
def get_solutions():
    """
    Endpoint 3: Get AI-powered solutions
    Uses diagnostic results to generate actionable recommendations
    """
    try:
        data = request.json
        diagnostic_result = data.get('diagnostic', {})
        
        print(f"\n💡 Generating solutions via API...")
        
        # Extract recommendations from diagnostic
        recommendations = diagnostic_result.get('recommendations', [])
        issue = diagnostic_result.get('primary_issue', 'unknown')
        root_cause = diagnostic_result.get('root_cause', 'Analysis complete')
        
        # Format response for frontend
        response = {
            "issue": issue,
            "root_cause": root_cause,
            "solutions": recommendations
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in /api/fix: {e}")
        return jsonify({
            "issue": "Solution Error",
            "root_cause": f"Failed to generate solutions: {str(e)}",
            "solutions": ["Check agent logs for details"]
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        "status": "running",
        "monitor_available": monitor is not None,
        "diagnostic_available": diagnostic is not None,
        "llm_available": llm is not None,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Starting Flask API Server")
    print("="*70)
    print(f"Monitor Agent: {'✅ Ready' if monitor else '❌ Not available'}")
    print(f"Diagnostic Agent: {'✅ Ready' if diagnostic else '❌ Not available'}")
    print(f"LLM: {'✅ Connected' if llm else '❌ Not available'}")
    print("\nEndpoints:")
    print("  GET  /api/monitor   - Get current network status (continuous)")
    print("  POST /api/diagnose  - Run FULL PIPELINE (Monitor→Diagnostic→Solution)")
    print("  POST /api/fix       - Get solutions only (legacy)")
    print("  GET  /api/health    - Check API health")
    print("="*70 + "\n")
    
    # Run on all interfaces so React can connect
    app.run(host='0.0.0.0', port=5000, debug=True)
