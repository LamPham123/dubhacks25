#!/usr/bin/env python3
"""
Simplified Diagnostic Agent - Lightweight version for Raspberry Pi
Quick diagnostic without heavy LLM processing
"""

import time
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

# Lightweight diagnostic tools
try:
    from icmplib import ping
    import psutil
    import netifaces
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install icmplib psutil netifaces")
    exit(1)


def quick_ping_test(targets: List[str]) -> Dict:
    """Quick ping test to multiple targets"""
    results = []
    
    for target in targets:
        try:
            result = ping(target, count=3, timeout=2, privileged=False)
            results.append({
                'target': target,
                'success': result.is_alive,
                'latency_ms': round(result.avg_rtt, 2) if result.avg_rtt else None,
                'packet_loss': result.packet_loss
            })
        except Exception as e:
            results.append({
                'target': target,
                'success': False,
                'error': str(e)
            })
    
    return {'results': results}


def quick_traceroute(target: str = "8.8.8.8") -> Dict:
    """Quick traceroute with timeout"""
    try:
        result = subprocess.run(
            ['traceroute', '-m', '10', '-w', '1', '-q', '1', target],
            capture_output=True,
            text=True,
            timeout=15  # Shorter timeout
        )
        
        hops = []
        lines = result.stdout.strip().split('\n')[1:]
        
        for line in lines[:10]:  # Limit to first 10 hops
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].isdigit():
                hops.append({
                    'hop': int(parts[0]),
                    'host': parts[1] if parts[1] != '*' else 'timeout',
                    'latency_ms': None
                })
        
        return {
            'success': True,
            'target': target,
            'hops': hops
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'target': target
        }


def check_wifi_interference() -> Dict:
    """Quick WiFi scan for interference"""
    try:
        result = subprocess.run(
            ['sudo', 'iwlist', 'wlan0', 'scan'],
            capture_output=True,
            text=True,
            timeout=5  # Shorter timeout
        )
        
        networks = []
        for line in result.stdout.split('\n'):
            if 'Cell' in line and 'ESSID:' in line:
                # Extract SSID and signal
                try:
                    essid = line.split('ESSID:')[1].strip().strip('"')
                    networks.append({'ssid': essid})
                except:
                    pass
        
        return {
            'success': True,
            'networks_found': len(networks),
            'sample_networks': networks[:5]  # Just first 5
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def analyze_network_issue(alert: Dict) -> Dict:
    """
    Quick analysis without heavy LLM processing
    Uses simple rules and diagnostic tools
    """
    print(f"\n🔬 Quick Diagnostic Analysis")
    print(f"📊 Alert status: {alert['status']}")
    
    # Extract metrics
    metrics = alert.get('metrics', {})
    ping_data = metrics.get('ping', {})
    dns_data = metrics.get('dns', {})
    signal_data = metrics.get('signal', {})
    
    # Quick diagnostic tests
    print("🔍 Running quick tests...")
    
    # Test 1: Multi-target ping
    print("  - Testing multiple targets...")
    ping_results = quick_ping_test(['router', '8.8.8.8', '1.1.1.1'])
    
    # Test 2: Traceroute
    print("  - Running traceroute...")
    trace_results = quick_traceroute()
    
    # Test 3: WiFi scan (if WiFi issue suspected)
    wifi_results = None
    if signal_data.get('signal_dbm', 0) < -70:
        print("  - Checking WiFi interference...")
        wifi_results = check_wifi_interference()
    
    # Simple rule-based analysis
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'primary_issue': alert['status'],
        'confidence': 'medium',
        'evidence': [],
        'diagnostic_data': {
            'ping_results': ping_results,
            'traceroute': trace_results,
            'wifi_scan': wifi_results
        },
        'recommendations': []
    }
    
    # Analyze ping results
    ping_success_count = sum(1 for r in ping_results['results'] if r['success'])
    if ping_success_count == 0:
        analysis['root_cause'] = 'Complete network failure - check router and ISP'
        analysis['confidence'] = 'high'
        analysis['recommendations'].append('Check router power and connections')
        analysis['recommendations'].append('Contact ISP if router is working')
    elif ping_success_count == 1:
        analysis['root_cause'] = 'Local network issue - router or WiFi problem'
        analysis['confidence'] = 'high'
        analysis['recommendations'].append('Restart router')
        analysis['recommendations'].append('Check WiFi signal strength')
    else:
        analysis['root_cause'] = 'Internet connectivity issue - ISP or routing problem'
        analysis['confidence'] = 'medium'
        analysis['recommendations'].append('Check ISP status')
        analysis['recommendations'].append('Try different DNS servers')
    
    # Add evidence
    analysis['evidence'].append(f"Ping success rate: {ping_success_count}/3")
    if trace_results['success']:
        analysis['evidence'].append(f"Traceroute completed to {trace_results['target']}")
    if wifi_results and wifi_results['success']:
        analysis['evidence'].append(f"Found {wifi_results['networks_found']} WiFi networks")
    
    return analysis


def print_diagnosis(diagnosis: Dict):
    """Print diagnosis in readable format"""
    print("\n" + "="*60)
    print("🔬 QUICK DIAGNOSTIC REPORT")
    print("="*60)
    
    print(f"\n📊 Primary Issue: {diagnosis.get('primary_issue', 'Unknown')}")
    print(f"🎯 Root Cause: {diagnosis.get('root_cause', 'Unknown')}")
    print(f"📈 Confidence: {diagnosis.get('confidence', 'Unknown').upper()}")
    
    if 'evidence' in diagnosis and diagnosis['evidence']:
        print(f"\n🔍 Evidence:")
        for evidence in diagnosis['evidence']:
            print(f"  • {evidence}")
    
    if 'recommendations' in diagnosis and diagnosis['recommendations']:
        print(f"\n✅ Recommendations:")
        for rec in diagnosis['recommendations']:
            print(f"  • {rec}")
    
    print("\n" + "="*60)


def main():
    """Main function for testing"""
    print("🧪 Quick Diagnostic Agent Test")
    print("="*40)
    
    # Simulate a high latency alert
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
    
    # Run quick diagnosis
    diagnosis = analyze_network_issue(test_alert)
    print_diagnosis(diagnosis)
    
    # Save result
    output_file = '/tmp/quick_diagnostic_result.json'
    with open(output_file, 'w') as f:
        json.dump(diagnosis, f, indent=2)
    print(f"\n💾 Diagnosis saved to: {output_file}")


if __name__ == "__main__":
    main()
