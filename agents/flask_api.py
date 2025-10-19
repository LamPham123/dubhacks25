"""
Flask API Wrapper for Network Monitoring Agents
Exposes CrewAI agents as REST endpoints for React frontend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import os

# Disable CrewAI telemetry for better performance
os.environ['OTEL_SDK_DISABLED'] = 'true'

# Import your existing agents
from monitor_agent import NetworkMonitor
from diagnostic_agent_working import WorkingDiagnosticAgent

# Import CrewAI LLM
from crewai import LLM

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize LLM (using Ollama) with speed optimizations
try:
    llm = LLM(
        model='ollama/qwen2.5:0.5b',
        base_url="http://localhost:11434",
        temperature=0.3,  # Lower = faster, more focused responses
        # max_tokens=100    # Limit response length for speed
    )
    print("✅ LLM initialized (optimized for speed)")
except Exception as e:
    print(f"⚠️  LLM initialization failed: {e}")
    llm = None

# Initialize agents with robust error handling
monitor = None
diagnostic = None

try:
    if llm:
        monitor = NetworkMonitor(llm, interface="wlan0")
        print("✅ Monitor Agent initialized")
    else:
        print("⚠️  Monitor Agent skipped (LLM not available)")
except Exception as e:
    print(f"⚠️  Monitor Agent initialization failed: {e}")
    monitor = None

# DON'T create diagnostic agent at startup - create fresh for each request
# This matches run_pipeline.py behavior and avoids threading issues
diagnostic = None

print("✅ Flask API initialized with CrewAI agents")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/monitor', methods=['GET'])
def get_monitor_status():
    """
    Endpoint 1: Get current network status
    Uses your Monitor Agent to check network health
    Works even when network is down!
    """
    try:
        if not monitor:
            # Fallback if LLM not available - still return valid data
            return jsonify({
                "timestamp": datetime.now().isoformat(),
                "status": "offline",
                "metrics": {
                    "ping": {"success": False, "latency_ms": 0, "packet_loss": 100},
                    "signal": {"success": False, "signal_dbm": 0, "quality": "offline"}
                }
            })
        
        # Use your existing monitor agent
        try:
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
            
        except Exception as monitor_error:
            # Monitor failed (likely network is down) - return offline status
            print(f"⚠️  Monitor check failed (network might be down): {monitor_error}")
            return jsonify({
                "timestamp": datetime.now().isoformat(),
                "status": "offline",
                "metrics": {
                    "ping": {"success": False, "latency_ms": 0, "packet_loss": 100, "error": str(monitor_error)},
                    "signal": {"success": False, "signal_dbm": 0, "quality": "offline"}
                }
            })
        
    except Exception as e:
        print(f"❌ Critical error in /api/monitor: {e}")
        # Even on critical error, return valid JSON (not 500)
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "metrics": {
                "ping": {"success": False, "latency_ms": 0, "packet_loss": 100, "error": "API error"},
                "signal": {"success": False, "signal_dbm": 0, "quality": "error"}
            }
        })


@app.route('/api/diagnose', methods=['POST'])
def run_full_pipeline():
    """
    Endpoint 2: Run FULL PIPELINE - Monitor → Diagnostic → Solution
    Just like run_pipeline.py but returns JSON
    """
    try:
        import time
        pipeline_start = time.time()
        
        print("\n" + "="*70)
        print("🚀 RUNNING FULL DIAGNOSTIC PIPELINE VIA API")
        print("="*70)
        
        # STEP 1: Monitor - Get current network status
        print("\n📡 STEP 1: Monitor Agent - Collecting metrics...")
        if not monitor:
            # Create a minimal alert for offline mode
            alert = {
                'timestamp': datetime.now().isoformat(),
                'status': 'offline',
                'warnings': [{'type': 'connectivity', 'message': 'Network appears to be down'}],
                'issues': [],
                'metrics': {
                    'ping': {'success': False, 'latency_ms': 0, 'packet_loss': 100},
                    'dns': {'success': False},
                    'signal': {'success': False, 'signal_dbm': 0},
                    'interface': {'up': False},
                    'gateway': {'success': False}
                }
            }
        else:
            try:
                alert = monitor.check_once()
            except Exception as e:
                print(f"   ⚠️  Monitor failed (network might be down): {e}")
                # Create offline alert
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'offline',
                    'warnings': [{'type': 'connectivity', 'message': f'Monitor failed: {str(e)}'}],
                    'issues': [],
                    'metrics': {
                        'ping': {'success': False, 'latency_ms': 0, 'packet_loss': 100},
                        'dns': {'success': False},
                        'signal': {'success': False, 'signal_dbm': 0},
                        'interface': {'up': False},
                        'gateway': {'success': False}
                    }
                }
        
        print(f"   Status: {alert['status']}")
        
        # STEP 2: Diagnostic - Create FRESH agent and run tools + AI scoring
        print("\n🔬 STEP 2: Diagnostic Agent - Running tools...")
        print("   ⏳ This will take 10-20 seconds...")
        start_time = time.time()
        
        try:
            # Create fresh diagnostic agent for this request (like run_pipeline.py)
            fresh_diagnostic = WorkingDiagnosticAgent(interface="wlan0", llm=llm)
            diagnosis = fresh_diagnostic.diagnose(alert)
            elapsed = time.time() - start_time
            print(f"   ✅ Diagnostic complete in {elapsed:.1f}s")
            print(f"   Issue: {diagnosis.get('primary_issue')}")
            print(f"   Health Score: {diagnosis.get('network_health_score', 'N/A')}/100")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ⚠️  Diagnostic failed after {elapsed:.1f}s: {e}")
            # Create minimal diagnosis for offline mode
            diagnosis = {
                'timestamp': datetime.now().isoformat(),
                'alert_status': alert['status'],
                'primary_issue': 'network_offline',
                'root_cause': f'Network appears to be down or unreachable. Diagnostic tools cannot run without connectivity.',
                'confidence': 'high',
                'evidence': ['All network operations failed', 'No connectivity detected'],
                'recommendations': [
                    'Check if WiFi is enabled on your device',
                    'Verify WiFi adapter is working',
                    'Check if router is powered on',
                    'Try restarting your network adapter'
                ],
                'network_health_score': 0,
                'score_explanation': 'Network is completely offline',
                'diagnostic_data': {}
            }
        
        # STEP 3: Solution - Generate recommendations
        print("\n💡 STEP 3: Solution Agent - Generating recommendations...")
        print("   ⏳ AI is thinking (5-10 seconds)...")
        start_time = time.time()
        
        try:
            from solution_agent import SolutionAgent
            solution_agent = SolutionAgent(llm) if llm else None
            
            if solution_agent and diagnosis.get('primary_issue') != 'network_offline':
                solutions = solution_agent.generate_solutions(diagnosis)
                solution_list = solutions.get('solutions', {}).get('solutions_list', [])
            else:
                # Fallback to diagnostic recommendations
                solution_list = diagnosis.get('recommendations', [])
            
            elapsed = time.time() - start_time
            print(f"   ✅ Solutions generated in {elapsed:.1f}s")
            print(f"   Generated {len(solution_list)} solutions")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ⚠️  Solution generation failed after {elapsed:.1f}s: {e}")
            # Use diagnostic recommendations as fallback
            solution_list = diagnosis.get('recommendations', ['Check network connectivity'])
        
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
        
        # Calculate total time
        total_time = time.time() - pipeline_start
        
        print("\n✅ Pipeline complete!")
        print(f"⏱️  Total pipeline time: {total_time:.1f} seconds")
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
        "diagnostic_available": llm is not None,  # Diagnostic created per request
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
    print(f"Diagnostic Agent: ✅ Created per request (fresh)")
    print(f"LLM: {'✅ Connected' if llm else '❌ Not available'}")
    print("\nEndpoints:")
    print("  GET  /api/monitor   - Get current network status (continuous)")
    print("  POST /api/diagnose  - Run FULL PIPELINE (Monitor→Diagnostic→Solution)")
    print("  POST /api/fix       - Get solutions only (legacy)")
    print("  GET  /api/health    - Check API health")
    print("="*70 + "\n")
    
    # Run on all interfaces so React can connect
    # debug=False for better performance with AI agents
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
