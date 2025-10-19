"""
Diagnostic Agent - Simplified Network Diagnostics with CrewAI
Investigates network issues detected by Monitor Agent using focused diagnostic tools
"""

import time
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# Diagnostic libraries
try:
    import netifaces
    from icmplib import ping as icmp_ping
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install netifaces icmplib crewai")
    exit(1)


# ============================================================================
# SIMPLIFIED DIAGNOSTIC TOOLS - Focused network investigation
# ============================================================================

@tool("run_traceroute")
def run_traceroute(target: str = "8.8.8.8", max_hops: int = 15) -> str:
    """
    Run traceroute to identify where network delays occur.
    Shows each hop from your device to the target and latency at each hop.
    
    Args:
        target: Target host to trace route to (default: 8.8.8.8)
        max_hops: Maximum number of hops to trace (default: 15)
    
    Returns:
        JSON string with hop-by-hop latency data
    """
    try:
        result = subprocess.run(
            ['traceroute', '-m', str(max_hops), '-w', '2', '-q', '1', target],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        hops = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            # Parse traceroute output: "3  192.168.1.1  1.234 ms"
            parts = line.strip().split()
            if len(parts) >= 3:
                hop_num = parts[0]
                if hop_num.isdigit():
                    hop_data = {
                        'hop': int(hop_num),
                        'host': parts[1] if parts[1] != '*' else 'timeout',
                        'latency_ms': None
                    }
                    
                    # Extract latency (look for numbers followed by 'ms')
                    for part in parts[2:]:
                        try:
                            if 'ms' in part:
                                latency = float(part.replace('ms', ''))
                                hop_data['latency_ms'] = round(latency, 2)
                                break
                        except ValueError:
                            continue
                    
                    hops.append(hop_data)
        
        return json.dumps({
            'success': True,
            'target': target,
            'hops': hops,
            'total_hops': len(hops)
        })
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            'success': False,
            'error': 'Traceroute timed out',
            'target': target
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e),
            'target': target
        })


@tool("ping_multiple_targets")
def ping_multiple_targets(targets: str = "router,8.8.8.8,1.1.1.1") -> str:
    """
    Ping multiple targets to isolate where the problem is.
    Helps determine if issue is local network, ISP, or internet-wide.
    
    Args:
        targets: Comma-separated list of targets. Use 'router' for gateway.
                 Example: "router,8.8.8.8,1.1.1.1"
    
    Returns:
        JSON string with ping results for each target
    """
    try:
        target_list = targets.split(',')
        results = []
        
        for target in target_list:
            target = target.strip()
            
            # Special handling for 'router' - get gateway IP
            if target.lower() == 'router':
                gateways = netifaces.gateways()
                default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
                if default_gateway:
                    target = default_gateway[0]
                else:
                    results.append({
                        'target': 'router',
                        'success': False,
                        'error': 'No default gateway found'
                    })
                    continue
            
            # Ping the target
            try:
                result = icmp_ping(target, count=5, timeout=2, privileged=False)
                results.append({
                    'target': target,
                    'success': result.is_alive,
                    'latency_ms': round(result.avg_rtt * 1000, 2) if result.is_alive else None,
                    'packet_loss': round(result.packet_loss, 1),
                    'min_rtt': round(result.min_rtt * 1000, 2) if result.is_alive else None,
                    'max_rtt': round(result.max_rtt * 1000, 2) if result.is_alive else None
                })
            except Exception as e:
                results.append({
                    'target': target,
                    'success': False,
                    'error': str(e)
                })
        
        return json.dumps({
            'success': True,
            'results': results,
            'total_targets': len(results)
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })


@tool("check_arp_table")
def check_arp_table() -> str:
    """
    Check ARP table to see devices on local network.
    Useful for identifying if router is responding and network is active.
    
    Returns:
        JSON string with ARP table entries
    """
    try:
        result = subprocess.run(
            ['arp', '-n'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        entries = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                entries.append({
                    'ip': parts[0],
                    'mac': parts[2] if parts[2] != '(incomplete)' else None,
                    'interface': parts[-1] if len(parts) > 4 else None
                })
        
        return json.dumps({
            'success': True,
            'entries': entries,
            'total_devices': len(entries)
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })


# ============================================================================
# DIAGNOSTIC AGENT CLASS
# ============================================================================

class DiagnosticAgent:
    """
    Simplified CrewAI-based Network Diagnostic Agent
    Performs focused investigation of network issues using 3 key tools
    """
    
    def __init__(self, llm: LLM, interface: str = "wlan0"):
        """
        Initialize Diagnostic Agent
        
        Args:
            llm: Language model for the agent
            interface: Network interface to diagnose (wlan0 for WiFi, eth0 for ethernet)
        """
        self.llm = llm
        self.interface = interface
        self.diagnostic_history = []
        
        # Create the CrewAI agent with simplified diagnostic tools
        self.agent = Agent(
            role='Network Diagnostic Specialist',
            goal='Execute diagnostic tools and analyze their actual results',
            backstory="""You are a network diagnostician who ALWAYS uses the provided tools.
            
            You MUST call these tools in order:
            1. check_arp_table - Shows local network devices
            2. ping_multiple_targets - Tests connectivity to different targets  
            3. run_traceroute - Shows network path and delays
            
            You NEVER just describe what you would do - you ALWAYS call the tools
            and analyze their actual output to diagnose network issues.""",
            tools=[
                check_arp_table,
                ping_multiple_targets,
                run_traceroute
            ],
            verbose=True,
            llm=llm
        )
        
        print(f"✅ Diagnostic Agent initialized - interface: {interface}")
    
    def diagnose(self, alert: Dict) -> Dict:
        """
        Perform focused diagnostics on a network issue reported by Monitor Agent
        
        Args:
            alert: Alert dictionary from Monitor Agent containing status, warnings, metrics
            
        Returns:
            Focused diagnosis with root cause analysis and recommendations
        """
        print(f"\n🔬 Starting diagnostic investigation...")
        print(f"📊 Alert status: {alert['status']}")
        
        # Create diagnostic task
        task = self.create_diagnostic_task(alert)
        
        # Execute with CrewAI
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Parse and structure the result
        diagnosis = self.parse_diagnosis_result(result, alert)
        
        # Add to history
        self.diagnostic_history.append({
            'timestamp': datetime.now().isoformat(),
            'alert': alert,
            'diagnosis': diagnosis
        })
        
        return diagnosis
    
    def create_diagnostic_task(self, alert: Dict) -> Task:
        """
        Create a CrewAI task for focused diagnostic investigation
        
        Args:
            alert: Alert from Monitor Agent
            
        Returns:
            CrewAI Task
        """
        # Extract key information from alert
        status = alert.get('status', 'unknown')
        warnings = alert.get('warnings', [])
        issues = alert.get('issues', [])
        metrics = alert.get('metrics', {})
        
        # Build simplified context string
        context_parts = []
        
        if issues:
            context_parts.append("CRITICAL ISSUES:")
            for issue in issues:
                context_parts.append(f"  - {issue['type']}: {issue['message']}")
        
        if warnings:
            context_parts.append("\nWARNINGS:")
            for warning in warnings:
                context_parts.append(f"  - {warning['type']}: {warning['message']}")
        
        context_parts.append(f"\nMETRICS:")
        context_parts.append(f"  Ping: {json.dumps(metrics.get('ping', {}), indent=4)}")
        context_parts.append(f"  DNS: {json.dumps(metrics.get('dns', {}), indent=4)}")
        context_parts.append(f"  Signal: {json.dumps(metrics.get('signal', {}), indent=4)}")
        
        context = "\n".join(context_parts)
        
        return Task(
            description=f"""Network Status: {status}

YOU MUST USE THE TOOLS PROVIDED. DO NOT JUST DESCRIBE WHAT YOU WOULD DO.

Execute these diagnostic tools in this exact order:

1. FIRST: Use the check_arp_table tool to get the ARP table
2. SECOND: Use the ping_multiple_targets tool with "router,8.8.8.8,1.1.1.1"  
3. THIRD: Use the run_traceroute tool with "8.8.8.8"

After running each tool, analyze the results and provide:
- What the tool results show
- What this means for the network issue
- Your conclusion about the root cause

CRITICAL: You must actually call these tools and show their output.""",
            agent=self.agent,
            expected_output="""A diagnostic report that includes:
1. The actual output/results from each tool you used
2. Analysis of what each tool result means
3. Your final diagnosis of the root cause
4. Confidence level in your diagnosis"""
        )
    
    def parse_diagnosis_result(self, result, alert: Dict) -> Dict:
        """
        Parse and structure the diagnosis result from CrewAI
        
        Args:
            result: Result from CrewAI crew execution
            alert: Original alert
            
        Returns:
            Structured diagnosis dictionary
        """
        # Try to extract JSON from result if present
        result_str = str(result)
        
        # Create structured diagnosis
        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'primary_issue': alert.get('status', 'unknown'),
            'root_cause': 'See analysis',
            'confidence': 'MEDIUM',
            'full_analysis': result_str,
            'alert_data': alert,
            'tools_used': [],
            'recommendations': []
        }
        
        # Try to extract tool usage from result
        if 'check_arp_table' in result_str:
            diagnosis['tools_used'].append('check_arp_table')
        if 'ping_multiple_targets' in result_str:
            diagnosis['tools_used'].append('ping_multiple_targets')
        if 'run_traceroute' in result_str:
            diagnosis['tools_used'].append('run_traceroute')
        
        return diagnosis
    
    def print_diagnosis_report(self, diagnosis: Dict):
        """Print a formatted diagnosis report"""
        print("\n" + "="*70)
        print("🔬 DIAGNOSTIC REPORT")
        print("="*70)
        
        print(f"\n📊 Primary Issue: {diagnosis['primary_issue']}")
        print(f"🎯 Root Cause: {diagnosis['root_cause']}")
        print(f"📈 Confidence: {diagnosis['confidence']}")
        
        if diagnosis['tools_used']:
            print(f"\n🔧 Tools Used: {', '.join(diagnosis['tools_used'])}")
        
        print(f"\n📝 Full Analysis:")
        print(diagnosis['full_analysis'])
        
        print("\n" + "="*70)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Simplified Network Diagnostic Agent')
    parser.add_argument('--mode', choices=['test', 'file', 'integrated'], default='test',
                        help='Mode: test (simulate alert), file (load from JSON), integrated (wait for monitor)')
    parser.add_argument('--alert-file', type=str,
                        help='Path to alert JSON file (for file mode)')
    parser.add_argument('--interface', default='wlan0',
                        help='Network interface to diagnose (wlan0, eth0, etc.)')
    parser.add_argument('--model', default='ollama/qwen2.5:0.5b',
                        help='LLM model to use')
    
    args = parser.parse_args()
    
    # Initialize LLM
    try:
        llm = LLM(model=args.model, base_url="http://localhost:11434")
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    
    # Initialize Diagnostic Agent
    agent = DiagnosticAgent(llm, args.interface)
    
    if args.mode == 'test':
        # Test mode - simulate an alert
        test_alert = {
            'status': 'degraded',
            'timestamp': datetime.now().isoformat(),
            'warnings': [
                {'type': 'high_latency', 'message': 'Ping latency > 100ms'},
                {'type': 'packet_loss', 'message': 'Packet loss detected'}
            ],
            'issues': [],
            'metrics': {
                'ping': {'success': True, 'latency_ms': 150.5, 'packet_loss': 5.0},
                'dns': {'success': True, 'latency_ms': 200.0},
                'signal': {'success': True, 'signal_dbm': -70, 'quality': 'poor'}
            }
        }
        
        print("🧪 Running in TEST mode with simulated alert...")
        diagnosis = agent.diagnose(test_alert)
        agent.print_diagnosis_report(diagnosis)
        
    elif args.mode == 'file':
        # File mode - load alert from JSON file
        if not args.alert_file:
            print("❌ --alert-file required for file mode")
            sys.exit(1)
        
        try:
            print(f"\n📁 Loading alert from: {args.alert_file}")
            with open(args.alert_file, 'r') as f:
                alert = json.load(f)
            
            diagnosis = agent.diagnose(alert)
            agent.print_diagnosis_report(diagnosis)
            
        except FileNotFoundError:
            print(f"❌ Alert file not found: {args.alert_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in alert file: {e}")
            sys.exit(1)
    
    elif args.mode == 'integrated':
        # Integrated mode - wait for monitor agent input
        print("🔄 Running in INTEGRATED mode - waiting for monitor input...")
        print("This mode would typically receive alerts from Monitor Agent")
        print("For now, use file mode with --alert-file")
        sys.exit(1)
