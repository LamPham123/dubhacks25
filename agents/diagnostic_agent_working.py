"""
Diagnostic Agent - Rule-Based (ACTUALLY WORKS!)
Forces tool execution, uses Python logic for analysis
"""

import json
import time
from datetime import datetime
from typing import Dict

# Import the tools directly
import sys
sys.path.insert(0, '/home/admin/Documents/crewai_starter/agents')

try:
    from diagnostic_agent import (
        run_traceroute,
        ping_multiple_targets,
        scan_wifi_channels,
        check_dns_servers,
        check_network_congestion,
        check_arp_table
    )
except ImportError:
    print("Error importing tools from diagnostic_agent.py")
    exit(1)


class WorkingDiagnosticAgent:
    """
    Diagnostic agent that ACTUALLY runs tools and analyzes results
    No LLM flakiness - pure Python logic
    """
    
    def __init__(self, interface: str = "wlan0"):
        self.interface = interface
        print(f"✅ Working Diagnostic Agent initialized - interface: {interface}")
    
    def diagnose(self, alert: Dict) -> Dict:
        """
        Run diagnostics on network issue
        
        Args:
            alert: Alert from monitor agent with status, warnings, metrics
            
        Returns:
            Comprehensive diagnosis with root cause
        """
        print(f"\n🔬 Starting REAL diagnostic investigation...")
        print(f"📊 Alert status: {alert['status']}\n")
        
        # Step 1: ALWAYS run diagnostic tools (no LLM needed)
        print("="*70)
        print("STEP 1: Running diagnostic tools...")
        print("="*70)
        
        results = {}
        
        # Tool 1: Ping multiple targets
        print("\n🔧 Tool 1: ping_multiple_targets")
        try:
            ping_result = ping_multiple_targets("router,8.8.8.8,1.1.1.1")
            results['ping_multiple'] = json.loads(ping_result)
            print(f"   ✅ Completed - tested {len(results['ping_multiple']['results'])} targets")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['ping_multiple'] = {'success': False, 'error': str(e)}
        
        # Tool 2: Traceroute
        print("\n🔧 Tool 2: run_traceroute")
        try:
            trace_result = run_traceroute("8.8.8.8")
            results['traceroute'] = json.loads(trace_result)
            if results['traceroute'].get('success'):
                print(f"   ✅ Completed - traced {results['traceroute']['total_hops']} hops")
            else:
                print(f"   ⚠️  {results['traceroute'].get('error')}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['traceroute'] = {'success': False, 'error': str(e)}
        
        # Tool 3: WiFi scan
        print("\n🔧 Tool 3: scan_wifi_channels")
        try:
            wifi_result = scan_wifi_channels(self.interface)
            results['wifi_scan'] = json.loads(wifi_result)
            if results['wifi_scan'].get('success'):
                print(f"   ✅ Completed - found {results['wifi_scan']['networks_found']} networks")
            else:
                print(f"   ⚠️  {results['wifi_scan'].get('error')}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['wifi_scan'] = {'success': False, 'error': str(e)}
        
        # Tool 4: DNS check
        print("\n🔧 Tool 4: check_dns_servers")
        try:
            dns_result = check_dns_servers()
            results['dns_check'] = json.loads(dns_result)
            if results['dns_check'].get('success'):
                print(f"   ✅ Completed - tested {len(results['dns_check']['dns_servers'])} DNS servers")
            else:
                print(f"   ⚠️  Failed")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['dns_check'] = {'success': False, 'error': str(e)}
        
        # Tool 5: ARP table
        print("\n🔧 Tool 5: check_arp_table")
        try:
            arp_result = check_arp_table()
            results['arp_table'] = json.loads(arp_result)
            if results['arp_table'].get('success'):
                print(f"   ✅ Completed - found {results['arp_table']['total_devices']} devices")
            else:
                print(f"   ⚠️  Failed")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results['arp_table'] = {'success': False, 'error': str(e)}
        
        # Step 2: Analyze with PYTHON RULES (not LLM)
        print("\n" + "="*70)
        print("STEP 2: Analyzing results with rule-based logic...")
        print("="*70)
        
        diagnosis = self.analyze_with_rules(alert, results)
        
        return diagnosis
    
    def analyze_with_rules(self, alert: Dict, results: Dict) -> Dict:
        """
        Use rule-based logic to diagnose the issue
        Much more reliable than small LLM!
        """
        metrics = alert.get('metrics', {})
        warnings = alert.get('warnings', [])
        
        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'alert_status': alert['status'],
            'primary_issue': None,
            'root_cause': None,
            'confidence': 'medium',
            'evidence': [],
            'recommendations': [],
            'diagnostic_data': results
        }
        
        # Extract key metrics
        ping_latency = metrics.get('ping', {}).get('latency_ms', 0)
        signal_dbm = metrics.get('signal', {}).get('signal_dbm', 0)
        dns_latency = metrics.get('dns', {}).get('latency_ms', 0)
        
        # Rule 1: Check ping multiple targets results
        if results.get('ping_multiple', {}).get('success'):
            ping_results = results['ping_multiple']['results']
            
            router_latency = None
            internet_latency = []
            
            for result in ping_results:
                if 'router' in result.get('target', '').lower() or result['target'].startswith('192.168'):
                    router_latency = result.get('latency_ms')
                else:
                    internet_latency.append(result.get('latency_ms', 0))
            
            avg_internet_latency = sum(internet_latency) / len(internet_latency) if internet_latency else 0
            
            print(f"\n📊 Latency Analysis:")
            print(f"   Router: {router_latency}ms" if router_latency else "   Router: not tested")
            print(f"   Internet: {avg_internet_latency:.1f}ms avg")
            print(f"   Monitor reported: {ping_latency}ms")
            
            # RULE: High router latency = local network issue
            if router_latency and router_latency > 100:
                diagnosis['primary_issue'] = 'high_local_network_latency'
                diagnosis['root_cause'] = f'Router latency is high ({router_latency}ms), indicating local network congestion or WiFi issues'
                diagnosis['confidence'] = 'high'
                diagnosis['evidence'].append(f'Router latency: {router_latency}ms (threshold: 50ms)')
                
                # Check WiFi as secondary cause
                if signal_dbm and signal_dbm < -70:
                    diagnosis['evidence'].append(f'WiFi signal is weak: {signal_dbm}dBm')
                    diagnosis['recommendations'].extend([
                        'Move closer to WiFi router',
                        'Switch to 5GHz band if available',
                        'Check for WiFi interference'
                    ])
                else:
                    diagnosis['recommendations'].extend([
                        'Check router CPU/memory usage',
                        'Restart router',
                        'Reduce number of connected devices'
                    ])
            
            # RULE: Router fast but internet slow = ISP/routing issue
            elif router_latency and router_latency < 50 and avg_internet_latency > 200:
                diagnosis['primary_issue'] = 'high_external_latency'
                diagnosis['root_cause'] = f'Router is responsive ({router_latency}ms) but external hosts are slow ({avg_internet_latency:.0f}ms avg), indicating ISP or internet routing issues'
                diagnosis['confidence'] = 'high'
                diagnosis['evidence'].append(f'Router: {router_latency}ms (fast)')
                diagnosis['evidence'].append(f'Internet: {avg_internet_latency:.0f}ms (slow)')
                diagnosis['recommendations'].extend([
                    'Contact ISP about latency issues',
                    'Check if other users on network experiencing same issue',
                    'Try wired connection to rule out WiFi'
                ])
            
            # RULE: Everything moderately slow = WiFi quality
            elif router_latency and 50 < router_latency < 150:
                diagnosis['primary_issue'] = 'moderate_network_degradation'
                diagnosis['root_cause'] = 'Moderate latency across local and external hosts, likely WiFi signal quality or interference'
                diagnosis['confidence'] = 'medium'
                diagnosis['evidence'].append(f'Router: {router_latency}ms (moderate)')
                diagnosis['evidence'].append(f'Signal: {signal_dbm}dBm')
                
                # Check WiFi congestion
                if results.get('wifi_scan', {}).get('success'):
                    networks = results['wifi_scan'].get('networks_found', 0)
                    if networks > 20:
                        diagnosis['evidence'].append(f'{networks} WiFi networks detected (congested environment)')
                        diagnosis['recommendations'].append('Switch to less congested WiFi channel')
                
                diagnosis['recommendations'].extend([
                    'Improve WiFi signal strength',
                    'Switch to 5GHz band',
                    'Move closer to router'
                ])
        
        # Rule 2: Check DNS performance
        if dns_latency > 1000:
            diagnosis['evidence'].append(f'DNS resolution is slow: {dns_latency}ms')
            diagnosis['recommendations'].append('Change DNS servers to 8.8.8.8 or 1.1.1.1')
        
        # Rule 3: Check WiFi signal if available
        if signal_dbm:
            if signal_dbm >= -50:
                quality = "excellent"
            elif signal_dbm >= -60:
                quality = "good"
            elif signal_dbm >= -70:
                quality = "fair"
            else:
                quality = "weak"
            
            diagnosis['evidence'].append(f'WiFi signal: {signal_dbm}dBm ({quality})')
            
            if signal_dbm < -70:
                diagnosis['recommendations'].insert(0, 'PRIORITY: Improve WiFi signal (move closer to router)')
        
        # Fallback if no specific diagnosis
        if not diagnosis['root_cause']:
            diagnosis['primary_issue'] = 'network_degradation'
            diagnosis['root_cause'] = 'Network performance is degraded, but specific cause unclear from available data'
            diagnosis['confidence'] = 'low'
            diagnosis['recommendations'].append('Run additional diagnostics')
        
        return diagnosis
    
    def print_diagnosis(self, diagnosis: Dict):
        """Print diagnosis in readable format"""
        print("\n" + "="*70)
        print("🔬 DIAGNOSTIC REPORT (RULE-BASED)")
        print("="*70)
        
        print(f"\n📊 Primary Issue: {diagnosis['primary_issue']}")
        print(f"🎯 Root Cause: {diagnosis['root_cause']}")
        print(f"📈 Confidence: {diagnosis['confidence'].upper()}")
        
        if diagnosis['evidence']:
            print(f"\n🔍 Evidence:")
            for evidence in diagnosis['evidence']:
                print(f"  • {evidence}")
        
        if diagnosis['recommendations']:
            print(f"\n✅ Recommendations:")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Working Network Diagnostic Agent (Rule-Based)')
    parser.add_argument('--mode', choices=['test', 'file'], default='test',
                        help='Mode: test (simulate alert), file (load from JSON)')
    parser.add_argument('--alert-file', type=str,
                        help='Path to alert JSON file (for file mode)')
    parser.add_argument('--interface', default='wlan0',
                        help='Network interface to diagnose (wlan0, eth0, etc.)')
    
    args = parser.parse_args()
    
    # Initialize diagnostic agent
    diagnostic = WorkingDiagnosticAgent(interface=args.interface)
    
    if args.mode == 'test':
        # Simulate a high latency alert
        print("\n🧪 Test mode: Simulating high latency alert\n")
        
        test_alert = {
            'timestamp': datetime.now().isoformat(),
            'status': 'degraded',
            'warnings': [{
                'type': 'latency',
                'severity': 'warning',
                'message': 'High latency: 526.94ms (threshold: 200ms)',
                'value': 526.94
            }],
            'issues': [],
            'metrics': {
                'ping': {
                    'success': True,
                    'latency_ms': 526.94,
                    'packet_loss': 0,
                    'host': '8.8.8.8'
                },
                'dns': {
                    'success': True,
                    'latency_ms': 44.02,
                    'ip': '142.250.185.46',
                    'domain': 'google.com'
                },
                'signal': {
                    'success': True,
                    'signal_dbm': -64,
                    'quality': 'fair',
                    'interface': 'wlan0'
                }
            }
        }
        
        diagnosis = diagnostic.diagnose(test_alert)
        diagnostic.print_diagnosis(diagnosis)
        
        # Save to file
        output_file = '/tmp/diagnostic_result_working.json'
        with open(output_file, 'w') as f:
            json.dump(diagnosis, f, indent=2)
        print(f"\n💾 Diagnosis saved to: {output_file}")
    
    elif args.mode == 'file':
        if not args.alert_file:
            print("❌ Error: --alert-file required for file mode")
            exit(1)
        
        print(f"\n📁 Loading alert from: {args.alert_file}\n")
        with open(args.alert_file, 'r') as f:
            alert = json.load(f)
        
        diagnosis = diagnostic.diagnose(alert)
        diagnostic.print_diagnosis(diagnosis)
        
        # Save to file
        output_file = '/tmp/diagnostic_result_working.json'
        with open(output_file, 'w') as f:
            json.dump(diagnosis, f, indent=2)
        print(f"\n💾 Diagnosis saved to: {output_file}")
