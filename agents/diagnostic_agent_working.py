"""
Diagnostic Agent - Rule-Based (ACTUALLY WORKS!)
Forces tool execution, uses Python logic for analysis
"""

import json
import re
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

# Import CrewAI for AI scoring
try:
    from crewai import Agent, Task, Crew
except ImportError:
    print("Warning: CrewAI not available, AI scoring will be disabled")
    Agent = Task = Crew = None


class WorkingDiagnosticAgent:
    """
    Diagnostic agent that ACTUALLY runs tools and analyzes results
    No LLM flakiness - pure Python logic
    Uses CrewAI only for AI health scoring
    """
    
    def __init__(self, interface: str = "wlan0", llm=None):
        self.interface = interface
        self.llm = llm
        self.enable_ai_scoring = llm is not None and Agent is not None
        
        # Create AI scoring agent if available
        if self.enable_ai_scoring:
            self.scoring_agent = Agent(
                role='Network Health Analyst',
                goal='Analyze network metrics and provide a health score from 0-100',
                backstory="""You are an expert network analyst who evaluates network performance.
                You look at latency, signal strength, packet loss, and other metrics to determine
                overall network health. You provide clear, concise health assessments.""",
                tools=[],  # No tools needed for scoring
                verbose=False,  # Keep it quiet
                llm=llm
            )
            print(f"✅ Working Diagnostic Agent initialized - interface: {interface} (AI scoring enabled)")
        else:
            self.scoring_agent = None
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
        
        # Check if network is actually healthy (no problems found)
        if not diagnosis['root_cause']:
            # Get router/internet latency to determine if healthy
            router_latency = None
            internet_latencies = []
            
            if results.get('ping_multiple', {}).get('success'):
                for result in results['ping_multiple']['results']:
                    if 'router' in result.get('target', '').lower() or result['target'].startswith('192.168'):
                        router_latency = result.get('latency_ms', 0)
                    else:
                        internet_latencies.append(result.get('latency_ms', 0))
            
            avg_internet = sum(internet_latencies) / len(internet_latencies) if internet_latencies else 0
            
            # If metrics are good, network is healthy!
            if router_latency and router_latency < 50 and avg_internet < 100 and signal_dbm > -70:
                diagnosis['primary_issue'] = 'network_healthy'
                diagnosis['root_cause'] = f'Network is performing well - router {router_latency:.1f}ms, internet {avg_internet:.0f}ms, signal {signal_dbm}dBm'
                diagnosis['confidence'] = 'high'
                diagnosis['recommendations'] = ['No action needed - network is healthy']
            else:
                # Unclear situation - metrics are borderline
                diagnosis['primary_issue'] = 'network_status_unclear'
                diagnosis['root_cause'] = 'Network metrics are borderline or insufficient data to make determination'
                diagnosis['confidence'] = 'low'
                diagnosis['recommendations'].append('Monitor network performance over time')
        
        # Generate AI health score if LLM available
        if self.enable_ai_scoring:
            try:
                score, explanation = self._generate_ai_health_score(diagnosis, results, metrics)
                diagnosis['network_health_score'] = score
                diagnosis['score_explanation'] = explanation
                print(f"\n🤖 AI Health Score: {score}/100 - {explanation}")
            except Exception as e:
                print(f"\n⚠️  AI scoring failed: {e}")
                # Don't break - diagnosis still works without score
        
        return diagnosis
    
    def _generate_ai_health_score(self, diagnosis: Dict, results: Dict, metrics: Dict) -> tuple:
        """
        Generate AI health score (0-100) using CrewAI framework
        
        Returns:
            (score, explanation) tuple
        """
        if not self.scoring_agent:
            return 50, "AI scoring not available"
        
        # Extract key metrics
        ping = metrics.get('ping', {})
        dns = metrics.get('dns', {})
        signal = metrics.get('signal', {})
        
        ping_latency = ping.get('latency_ms', 0)
        packet_loss = ping.get('packet_loss', 0)
        dns_latency = dns.get('latency_ms', 0)
        signal_dbm = signal.get('signal_dbm', 0)
        
        # Get router/internet latency from results
        router_latency = 0
        internet_latency = 0
        if results.get('ping_multiple', {}).get('success'):
            for result in results['ping_multiple']['results']:
                if 'router' in result.get('target', '').lower() or result['target'].startswith('192.168'):
                    router_latency = result.get('latency_ms', 0)
                elif result.get('success'):
                    internet_latency = result.get('latency_ms', 0)
                    break
        
        # Create CrewAI task for scoring
        scoring_task = Task(
            description=f"""Score this network from 0-100.

DATA: Router {router_latency:.1f}ms, Internet {internet_latency:.1f}ms, WiFi {signal_dbm}dBm

RULES:
- 90-100: All metrics excellent
- 70-89: Good performance
- 40-69: Fair, has issues
- 0-39: Poor performance

CRITICAL: Reply ONLY with this exact format: NUMBER|short explanation

Example: 95|Router 4ms excellent, internet fast, WiFi strong

Your answer:""",
            agent=self.scoring_agent,
            expected_output="Score from 0-100 with pipe-separated explanation"
        )
        
        try:
            # Create and run crew
            crew = Crew(
                agents=[self.scoring_agent],
                tasks=[scoring_task],
                verbose=False
            )
            
            result = crew.kickoff()
            response = str(result).strip()
            
            # Parse response - try multiple formats
            score = None
            explanation = ""
            
            print(f"\n   [DEBUG] AI raw response ({len(response)} chars):")
            print(f"   {response[:300]}...")
            
            # Method 1: Look for SCORE|explanation format (preferred)
            if '|' in response:
                parts = response.split('|', 1)
                score_str = ''.join(filter(str.isdigit, parts[0]))
                if score_str:
                    score = int(score_str)
                    explanation = parts[1].strip()[:150]
                    print(f"   [DEBUG] Parsed via Method 1 (pipe): score={score}")
            
            # Method 2: Extract numbers from response
            if score is None:
                # Look for patterns like "95", "Score: 95", "**95**", etc.
                numbers = re.findall(r'\b(\d{1,3})\b', response)
                print(f"   [DEBUG] Found numbers: {numbers[:5]}")
                
                if numbers:
                    # Take first number that's 0-100
                    for num in numbers:
                        potential_score = int(num)
                        if 0 <= potential_score <= 100:
                            score = potential_score
                            # Get text after the number
                            score_pos = response.find(num)
                            explanation = response[score_pos + len(num):].strip()
                            # Clean up markdown and formatting
                            explanation = explanation.replace('*', '').replace('#', '').strip()
                            explanation = explanation.split('\n')[0][:150]  # First line only
                            print(f"   [DEBUG] Parsed via Method 2 (regex): score={score}")
                            break
            
            # Method 3: Rule-based fallback if AI completely failed
            if score is None:
                print(f"   [DEBUG] Both methods failed, using rule-based fallback")
                score, explanation = self._fallback_health_score(router_latency, internet_latency, signal_dbm, packet_loss)
                explanation = f"Rule-based: {explanation}"
            
            # Clamp score to 0-100
            score = max(0, min(100, score))
            
            return score, explanation
            
        except Exception as e:
            # Fallback to rule-based scoring
            print(f"   AI scoring failed, using rule-based: {e}")
            return self._fallback_health_score(router_latency, internet_latency, signal_dbm, packet_loss)
    
    def _fallback_health_score(self, router_latency, internet_latency, signal_dbm, packet_loss) -> tuple:
        """Rule-based fallback scoring if LLM fails"""
        score = 100
        issues = []
        
        # Router latency penalty
        if router_latency > 100:
            score -= 30
            issues.append("high router latency")
        elif router_latency > 50:
            score -= 15
            issues.append("moderate router latency")
        
        # Internet latency penalty
        if internet_latency > 200:
            score -= 20
            issues.append("high internet latency")
        elif internet_latency > 100:
            score -= 10
        
        # Signal strength penalty
        if signal_dbm < -80:
            score -= 25
            issues.append("weak WiFi signal")
        elif signal_dbm < -70:
            score -= 10
        
        # Packet loss penalty
        if packet_loss > 5:
            score -= 20
            issues.append("packet loss")
        
        score = max(0, score)
        explanation = ", ".join(issues) if issues else "Network performing well"
        
        return score, explanation
    
    def print_diagnosis(self, diagnosis: Dict):
        """Print diagnosis in readable format"""
        print("\n" + "="*70)
        print("🔬 DIAGNOSTIC REPORT (RULE-BASED)")
        print("="*70)
        
        print(f"\n📊 Primary Issue: {diagnosis['primary_issue']}")
        print(f"🎯 Root Cause: {diagnosis['root_cause']}")
        print(f"📈 Confidence: {diagnosis['confidence'].upper()}")
        
        # Display AI health score if available
        if 'network_health_score' in diagnosis:
            score = diagnosis['network_health_score']
            explanation = diagnosis.get('score_explanation', '')
            
            # Choose emoji based on score
            if score >= 90:
                emoji = "🟢"
                rating = "EXCELLENT"
            elif score >= 70:
                emoji = "🟡"
                rating = "GOOD"
            elif score >= 40:
                emoji = "🟠"
                rating = "FAIR"
            else:
                emoji = "🔴"
                rating = "POOR"
            
            # Create visual bar
            filled = int(score / 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            print(f"\n{emoji} AI Health Score: {score}/100 ({rating})")
            print(f"   [{bar}] {explanation}")
        
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
