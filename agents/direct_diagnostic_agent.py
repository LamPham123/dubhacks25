"""
Direct Diagnostic Agent - Bypasses CrewAI to actually execute tools
This version directly calls diagnostic functions instead of relying on CrewAI
"""

import time
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

# Diagnostic libraries
try:
    import netifaces
    from icmplib import ping as icmp_ping
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install netifaces icmplib")
    exit(1)


# ============================================================================
# DIAGNOSTIC FUNCTIONS - Direct execution
# ============================================================================

def run_traceroute(target: str = "8.8.8.8", max_hops: int = 15) -> Dict:
    """
    Run traceroute to identify where network delays occur.
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
            parts = line.strip().split()
            if len(parts) >= 3:
                hop_num = parts[0]
                if hop_num.isdigit():
                    hop_data = {
                        'hop': int(hop_num),
                        'host': parts[1] if parts[1] != '*' else 'timeout',
                        'latency_ms': None
                    }
                    
                    # Extract latency
                    for part in parts[2:]:
                        try:
                            if 'ms' in part:
                                latency = float(part.replace('ms', ''))
                                hop_data['latency_ms'] = round(latency, 2)
                                break
                        except ValueError:
                            continue
                    
                    hops.append(hop_data)
        
        return {
            'success': True,
            'target': target,
            'hops': hops,
            'total_hops': len(hops)
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Traceroute timed out',
            'target': target
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'target': target
        }


def ping_multiple_targets(targets: str = "router,8.8.8.8,1.1.1.1") -> Dict:
    """
    Ping multiple targets to isolate where the problem is.
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
        
        return {
            'success': True,
            'results': results,
            'total_targets': len(results)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def check_arp_table() -> Dict:
    """
    Check ARP table to see devices on local network.
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
        
        return {
            'success': True,
            'entries': entries,
            'total_devices': len(entries)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# DIRECT DIAGNOSTIC AGENT CLASS
# ============================================================================

class DirectDiagnosticAgent:
    """
    Direct Diagnostic Agent that actually executes tools
    No CrewAI dependency - just direct function calls
    """
    
    def __init__(self, interface: str = "wlan0"):
        """
        Initialize Direct Diagnostic Agent
        
        Args:
            interface: Network interface to diagnose
        """
        self.interface = interface
        self.diagnostic_history = []
        
        print(f"✅ Direct Diagnostic Agent initialized - interface: {interface}")
    
    def diagnose(self, alert: Dict) -> Dict:
        """
        Perform direct diagnostics by actually calling tools
        
        Args:
            alert: Alert dictionary from Monitor Agent
            
        Returns:
            Comprehensive diagnosis with actual tool results
        """
        print(f"\n🔬 Starting DIRECT diagnostic investigation...")
        print(f"📊 Alert status: {alert['status']}")
        
        # Execute tools directly
        results = {}
        
        print("\n🔧 STEP 1: Checking ARP table...")
        arp_result = check_arp_table()
        results['arp'] = arp_result
        print(f"   ARP devices found: {arp_result.get('total_devices', 0)}")
        
        print("\n🔧 STEP 2: Testing connectivity scope...")
        ping_result = ping_multiple_targets("router,8.8.8.8,1.1.1.1")
        results['ping'] = ping_result
        print(f"   Ping targets tested: {len(ping_result.get('results', []))}")
        
        print("\n🔧 STEP 3: Running traceroute...")
        traceroute_result = run_traceroute("8.8.8.8")
        results['traceroute'] = traceroute_result
        print(f"   Traceroute hops: {traceroute_result.get('total_hops', 0)}")
        
        # Analyze results
        diagnosis = self.analyze_results(results, alert)
        
        # Add to history
        self.diagnostic_history.append({
            'timestamp': datetime.now().isoformat(),
            'alert': alert,
            'diagnosis': diagnosis,
            'tool_results': results
        })
        
        return diagnosis
    
    def analyze_results(self, results: Dict, alert: Dict) -> Dict:
        """
        Analyze the actual tool results to determine root cause
        
        Args:
            results: Dictionary with actual tool results
            alert: Original alert
            
        Returns:
            Structured diagnosis
        """
        # Analyze ARP results
        arp_devices = results['arp'].get('total_devices', 0)
        local_network_ok = arp_devices > 0
        
        # Analyze ping results
        ping_results = results['ping'].get('results', [])
        router_ok = False
        internet_ok = False
        
        for ping in ping_results:
            if ping['target'].startswith('192.168') or ping['target'].startswith('10.'):
                router_ok = ping['success']
            elif ping['target'] in ['8.8.8.8', '1.1.1.1']:
                internet_ok = ping['success']
        
        # Analyze traceroute results
        traceroute_hops = results['traceroute'].get('hops', [])
        isp_delay = False
        if traceroute_hops:
            # Check if there are significant delays in early hops
            for hop in traceroute_hops[:5]:  # First 5 hops
                if hop.get('latency_ms', 0) > 100:
                    isp_delay = True
                    break
        
        # Determine root cause
        if not local_network_ok:
            root_cause = "Local network issue - router not responding"
            confidence = "HIGH"
        elif not router_ok:
            root_cause = "Router connectivity issue"
            confidence = "HIGH"
        elif not internet_ok:
            root_cause = "ISP/Internet connectivity issue"
            confidence = "HIGH"
        elif isp_delay:
            root_cause = "ISP network delays detected"
            confidence = "MEDIUM"
        else:
            root_cause = "Network appears healthy - may be intermittent issue"
            confidence = "LOW"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'primary_issue': alert.get('status', 'unknown'),
            'root_cause': root_cause,
            'confidence': confidence,
            'tool_results': results,
            'analysis': {
                'local_network_devices': arp_devices,
                'router_responding': router_ok,
                'internet_accessible': internet_ok,
                'isp_delays_detected': isp_delay,
                'traceroute_hops': len(traceroute_hops)
            },
            'recommendations': self.generate_recommendations(root_cause, results)
        }
    
    def generate_recommendations(self, root_cause: str, results: Dict) -> List[str]:
        """
        Generate specific recommendations based on root cause
        """
        recommendations = []
        
        if "local network" in root_cause.lower():
            recommendations.append("Check router power and connections")
            recommendations.append("Restart router if possible")
            recommendations.append("Check ethernet/WiFi cable connections")
        
        elif "router" in root_cause.lower():
            recommendations.append("Ping router directly to confirm connectivity")
            recommendations.append("Check router configuration")
            recommendations.append("Consider router restart")
        
        elif "ISP" in root_cause.lower():
            recommendations.append("Contact ISP for service status")
            recommendations.append("Check ISP service status page")
            recommendations.append("Try different DNS servers (8.8.8.8, 1.1.1.1)")
        
        elif "delay" in root_cause.lower():
            recommendations.append("Monitor network during peak hours")
            recommendations.append("Consider upgrading internet plan")
            recommendations.append("Check for background downloads/uploads")
        
        else:
            recommendations.append("Monitor network for recurring issues")
            recommendations.append("Check for scheduled maintenance")
        
        return recommendations
    
    def print_diagnosis_report(self, diagnosis: Dict):
        """Print a formatted diagnosis report with actual results"""
        print("\n" + "="*70)
        print("🔬 DIRECT DIAGNOSTIC REPORT")
        print("="*70)
        
        print(f"\n📊 Primary Issue: {diagnosis['primary_issue']}")
        print(f"🎯 Root Cause: {diagnosis['root_cause']}")
        print(f"📈 Confidence: {diagnosis['confidence']}")
        
        # Show actual tool results
        print(f"\n🔧 ACTUAL TOOL RESULTS:")
        
        # ARP results
        arp = diagnosis['tool_results']['arp']
        print(f"\n📋 ARP Table:")
        print(f"   Devices found: {arp.get('total_devices', 0)}")
        if arp.get('entries'):
            for entry in arp['entries'][:5]:  # Show first 5
                print(f"   - {entry['ip']} -> {entry['mac'] or 'incomplete'}")
        
        # Ping results
        ping = diagnosis['tool_results']['ping']
        print(f"\n🏓 Ping Results:")
        for result in ping.get('results', []):
            if result['success']:
                print(f"   ✅ {result['target']}: {result['latency_ms']}ms (loss: {result['packet_loss']}%)")
            else:
                print(f"   ❌ {result['target']}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Traceroute results
        traceroute = diagnosis['tool_results']['traceroute']
        print(f"\n🛤️  Traceroute to {traceroute.get('target', 'unknown')}:")
        print(f"   Total hops: {traceroute.get('total_hops', 0)}")
        if traceroute.get('hops'):
            for hop in traceroute['hops'][:8]:  # Show first 8 hops
                latency = hop.get('latency_ms', 'timeout')
                print(f"   Hop {hop['hop']}: {hop['host']} ({latency}ms)")
        
        # Recommendations
        if diagnosis.get('recommendations'):
            print(f"\n✅ Recommendations:")
            for rec in diagnosis['recommendations']:
                print(f"   • {rec}")
        
        print("\n" + "="*70)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Direct Network Diagnostic Agent')
    parser.add_argument('--mode', choices=['test', 'file'], default='test',
                        help='Mode: test (simulate alert), file (load from JSON)')
    parser.add_argument('--alert-file', type=str,
                        help='Path to alert JSON file (for file mode)')
    parser.add_argument('--interface', default='wlan0',
                        help='Network interface to diagnose (wlan0, eth0, etc.)')
    
    args = parser.parse_args()
    
    # Initialize Direct Diagnostic Agent
    agent = DirectDiagnosticAgent(args.interface)
    
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
