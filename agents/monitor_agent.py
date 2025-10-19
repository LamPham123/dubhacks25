"""
Monitor Agent - Network Health Monitoring with CrewAI
Continuously monitors network health and triggers diagnostic agent when issues detected
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool

# Lightweight monitoring libraries
try:
    from icmplib import ping
    import psutil
    import dns.resolver
    import netifaces
    import subprocess
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install icmplib psutil dnspython netifaces crewai")
    exit(1)


# ============================================================================
# TOOLS - Lightweight network monitoring functions
# ============================================================================

@tool("ping_test")
def ping_test(host: str = "8.8.8.8") -> str:
    """
    Test network connectivity using ICMP ping.
    
    Args:
        host: Target host to ping (default: 8.8.8.8 - Google DNS)
    
    Returns:
        JSON string with ping results including success status, latency, and packet loss
    """
    try:
        result = ping(host, count=3, timeout=2, privileged=False)
        data = {
            'success': result.is_alive,
            'latency_ms': round(result.avg_rtt, 2) if result.avg_rtt else None,
            'packet_loss': result.packet_loss,
            'host': host
        }
        return json.dumps(data)
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e),
            'host': host
        })


@tool("dns_lookup")
def dns_lookup(domain: str = "google.com") -> str:
    """
    Test DNS resolution speed and availability.
    
    Args:
        domain: Domain name to resolve (default: google.com)
    
    Returns:
        JSON string with DNS lookup results including success status and resolution time
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 2
    
    try:
        start = time.time()
        answers = resolver.resolve(domain, 'A')
        latency_ms = (time.time() - start) * 1000
        
        return json.dumps({
            'success': True,
            'latency_ms': round(latency_ms, 2),
            'ip': str(answers[0]),
            'domain': domain
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e),
            'domain': domain
        })


@tool("check_wifi_signal")
def check_wifi_signal(interface: str = "wlan0") -> str:
    """
    Check WiFi signal strength in dBm (Linux only).
    
    Args:
        interface: Network interface name (default: wlan0)
    
    Returns:
        JSON string with signal strength in dBm and quality description
    """
    try:
        result = subprocess.run(
            ['iwconfig', interface],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        # Parse signal level from output
        for line in result.stdout.split('\n'):
            if 'Signal level' in line:
                signal_str = line.split('Signal level=')[1].split()[0]
                signal_dbm = int(signal_str.replace('dBm', ''))
                
                # Determine quality
                if signal_dbm >= -50:
                    quality = "excellent"
                elif signal_dbm >= -60:
                    quality = "good"
                elif signal_dbm >= -70:
                    quality = "fair"
                elif signal_dbm >= -80:
                    quality = "weak"
                else:
                    quality = "very weak"
                
                return json.dumps({
                    'success': True,
                    'signal_dbm': signal_dbm,
                    'quality': quality,
                    'interface': interface
                })
        
        return json.dumps({
            'success': False,
            'error': 'Signal level not found in iwconfig output',
            'interface': interface
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e),
            'interface': interface
        })


@tool("check_interface_status")
def check_interface_status(interface: str = "wlan0") -> str:
    """
    Get network interface statistics and status.
    
    Args:
        interface: Network interface name (default: wlan0)
    
    Returns:
        JSON string with interface status, bytes/packets sent/received, and error counts
    """
    try:
        # Check if interface exists
        addrs = netifaces.ifaddresses(interface)
        
        # Get I/O counters
        io_counters = psutil.net_io_counters(pernic=True)
        iface_stats = io_counters.get(interface)
        
        if not iface_stats:
            return json.dumps({'up': False, 'interface': interface})
        
        return json.dumps({
            'up': True,
            'interface': interface,
            'bytes_sent': iface_stats.bytes_sent,
            'bytes_recv': iface_stats.bytes_recv,
            'packets_sent': iface_stats.packets_sent,
            'packets_recv': iface_stats.packets_recv,
            'errors_in': iface_stats.errin,
            'errors_out': iface_stats.errout,
            'drops_in': iface_stats.dropin,
            'drops_out': iface_stats.dropout
        })
    except Exception as e:
        return json.dumps({
            'up': False,
            'error': str(e),
            'interface': interface
        })


@tool("get_network_gateway")
def get_network_gateway(interface: str = "wlan0") -> str:
    """
    Get the default gateway IP address for the interface.
    
    Args:
        interface: Network interface name (default: wlan0)
    
    Returns:
        JSON string with gateway IP address
    """
    try:
        gateways = netifaces.gateways()
        default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
        
        if default_gateway:
            gateway_ip, gateway_interface = default_gateway
            return json.dumps({
                'success': True,
                'gateway_ip': gateway_ip,
                'interface': gateway_interface
            })
        
        return json.dumps({
            'success': False,
            'error': 'No default gateway found'
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })


# ============================================================================
# MONITOR AGENT CLASS
# ============================================================================

class NetworkMonitor:
    """
    CrewAI-based Network Monitor Agent
    Continuously monitors network health and triggers diagnostic when issues detected
    """
    
    def __init__(self, llm: LLM, check_interval: int = 30, interface: str = "wlan0"):
        """
        Initialize Monitor Agent
        
        Args:
            llm: Language model for the agent
            check_interval: Seconds between health checks
            interface: Network interface to monitor (wlan0 for WiFi, eth0 for ethernet)
        """
        self.llm = llm
        self.check_interval = check_interval
        self.interface = interface
        self.metrics_history = []
        self.max_history = 100
        
        # Define thresholds
        self.thresholds = {
            'max_latency_ms': 200,
            'max_packet_loss': 20,
            'min_signal_dbm': -80,
            'dns_timeout_ms': 5000
        }
        
        # Create the CrewAI agent
        self.agent = Agent(
            role='Network Health Monitor',
            goal='Continuously monitor network connectivity, latency, DNS, and signal strength to detect issues immediately',
            backstory="""You are a vigilant network monitoring specialist running on a Raspberry Pi.
            You watch network metrics 24/7 and can detect subtle changes that indicate problems.
            You use lightweight tools like ping, DNS lookups, and WiFi signal checks.
            When you detect anomalies, you alert the diagnostic team with detailed context.""",
            tools=[
                ping_test,
                dns_lookup,
                check_wifi_signal,
                check_interface_status,
                get_network_gateway
            ],
            verbose=True,
            llm=llm
        )
        
        print(f"✅ Monitor Agent initialized - interface: {interface}, interval: {check_interval}s")
    
    def collect_metrics(self) -> Dict:
        """
        Collect current network metrics using tools
        
        Returns:
            Dictionary with all current metrics
        """
        print(f"\n🔍 Collecting metrics at {datetime.now().strftime('%H:%M:%S')}")
        
        # Use the tools directly (not through agent for speed)
        ping_result = json.loads(ping_test.func())
        dns_result = json.loads(dns_lookup.func())
        signal_result = json.loads(check_wifi_signal.func(self.interface))
        interface_result = json.loads(check_interface_status.func(self.interface))
        gateway_result = json.loads(get_network_gateway.func(self.interface))
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'ping': ping_result,
            'dns': dns_result,
            'signal': signal_result,
            'interface': interface_result,
            'gateway': gateway_result
        }
        
        # Add to history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
        
        return metrics
    
    def analyze_metrics(self, metrics: Dict) -> Dict:
        """
        Analyze metrics to detect issues
        
        Args:
            metrics: Current metrics
            
        Returns:
            Analysis with status and detected issues
        """
        issues = []
        warnings = []
        
        # Check ping
        ping = metrics['ping']
        if not ping.get('success'):
            issues.append({
                'type': 'connectivity',
                'severity': 'critical',
                'message': 'Cannot reach external hosts - ping failed',
                'details': ping
            })
        else:
            latency = ping.get('latency_ms')
            packet_loss = ping.get('packet_loss', 0)
            
            if latency and latency > self.thresholds['max_latency_ms']:
                warnings.append({
                    'type': 'latency',
                    'severity': 'warning',
                    'message': f'High latency: {latency}ms (threshold: {self.thresholds["max_latency_ms"]}ms)',
                    'value': latency
                })
            
            if packet_loss > self.thresholds['max_packet_loss']:
                warnings.append({
                    'type': 'packet_loss',
                    'severity': 'warning',
                    'message': f'High packet loss: {packet_loss}%',
                    'value': packet_loss
                })
        
        # Check DNS
        dns = metrics['dns']
        if not dns.get('success'):
            issues.append({
                'type': 'dns',
                'severity': 'critical',
                'message': 'DNS resolution failed',
                'details': dns
            })
        
        # Check signal
        signal = metrics['signal']
        if signal.get('success'):
            signal_dbm = signal.get('signal_dbm')
            if signal_dbm and signal_dbm < self.thresholds['min_signal_dbm']:
                warnings.append({
                    'type': 'signal',
                    'severity': 'warning',
                    'message': f'Weak WiFi signal: {signal_dbm}dBm ({signal.get("quality")})',
                    'value': signal_dbm
                })
        
        # Check interface
        interface = metrics['interface']
        if not interface.get('up'):
            issues.append({
                'type': 'interface',
                'severity': 'critical',
                'message': f'Network interface {self.interface} is down',
                'details': interface
            })
        
        # Determine status
        if issues:
            status = 'unhealthy'
        elif warnings:
            status = 'degraded'
        else:
            status = 'healthy'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'issues': issues,
            'warnings': warnings,
            'metrics': metrics
        }
    
    def create_analysis_task(self, metrics: Dict) -> Task:
        """
        Create a CrewAI task for the agent to analyze metrics
        
        Args:
            metrics: Current metrics to analyze
            
        Returns:
            CrewAI Task
        """
        return Task(
            description=f"""Analyze the following network metrics and provide a health assessment:

Metrics collected at {metrics['timestamp']}:
- Ping: {json.dumps(metrics['ping'], indent=2)}
- DNS: {json.dumps(metrics['dns'], indent=2)}
- WiFi Signal: {json.dumps(metrics['signal'], indent=2)}
- Interface: {json.dumps(metrics['interface'], indent=2)}
- Gateway: {json.dumps(metrics['gateway'], indent=2)}

Provide:
1. Overall health status (healthy/degraded/unhealthy)
2. Any critical connectivity issues
3. Any performance degradation warnings
4. Root cause hypothesis if issues detected
5. Recommended next steps

Be concise and actionable.""",
            agent=self.agent,
            expected_output="A structured health assessment with status and recommendations"
        )
    
    def print_status(self, analysis: Dict):
        """Print current status to console"""
        status = analysis['status']
        
        status_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '🔴'
        }
        
        time_str = datetime.now().strftime('%H:%M:%S')
        
        if status == 'healthy':
            metrics = analysis['metrics']
            ping = metrics['ping']
            dns = metrics['dns']
            signal = metrics['signal']
            
            print(f"{status_emoji[status]} [{time_str}] Network healthy - "
                  f"Ping: {ping.get('latency_ms')}ms, "
                  f"DNS: {dns.get('latency_ms')}ms, "
                  f"Signal: {signal.get('signal_dbm')}dBm ({signal.get('quality')})")
        else:
            print(f"\n{status_emoji[status]} [{time_str}] Network {status.upper()}")
            
            if analysis['issues']:
                print(f"🔴 Critical Issues ({len(analysis['issues'])}):")
                for issue in analysis['issues']:
                    print(f"  - {issue['message']}")
            
            if analysis['warnings']:
                print(f"⚠️  Warnings ({len(analysis['warnings'])}):")
                for warning in analysis['warnings']:
                    print(f"  - {warning['message']}")
    
    def run_monitoring(self, on_issue_callback=None):
        """
        Run continuous monitoring loop
        
        Args:
            on_issue_callback: Function to call when issues detected (receives analysis dict)
        """
        print(f"\n🚀 Starting network monitoring (interval: {self.check_interval}s)")
        print("Press Ctrl+C to stop\n")
        
        last_status = 'healthy'
        
        try:
            while True:
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Analyze
                analysis = self.analyze_metrics(metrics)
                
                # Print status
                self.print_status(analysis)
                
                # Trigger callback if status changed to unhealthy/degraded
                if analysis['status'] != 'healthy' and last_status == 'healthy':
                    print(f"\n🚨 ALERT: Network status changed from {last_status} to {analysis['status']}")
                    
                    if on_issue_callback:
                        on_issue_callback(analysis)
                
                # Update last status
                last_status = analysis['status']
                
                # Wait
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            import traceback
            traceback.print_exc()
    
    def check_once(self) -> Dict:
        """
        Perform a single health check (non-blocking)
        Useful for agentic workflows where you want the agent to check on-demand
        
        Returns:
            Analysis dictionary with status and any issues/warnings
        """
        metrics = self.collect_metrics()
        analysis = self.analyze_metrics(metrics)
        return analysis
    
    def get_recent_history(self, num_checks: int = 10) -> List[Dict]:
        """
        Get recent metrics history
        Useful for diagnostic agents to see trends
        
        Args:
            num_checks: Number of recent checks to return
            
        Returns:
            List of recent metrics
        """
        return self.metrics_history[-num_checks:] if self.metrics_history else []


# ============================================================================
# MAIN - Run as standalone or import as module
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Network Monitor Agent')
    parser.add_argument('--mode', choices=['test', 'monitor', 'check'], default='test',
                        help='Mode: test (single check), monitor (continuous), check (JSON output)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Check interval in seconds (for monitor mode)')
    parser.add_argument('--interface', default='wlan0',
                        help='Network interface to monitor (wlan0, eth0, etc.)')
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
    
    # Initialize monitor
    monitor = NetworkMonitor(llm, check_interval=args.interval, interface=args.interface)
    
    if args.mode == 'test':
        # Single check with pretty output
        print("\n🧪 Running single health check...\n")
        analysis = monitor.check_once()
        monitor.print_status(analysis)
        print()
        sys.exit(0 if analysis['status'] == 'healthy' else 1)
    
    elif args.mode == 'check':
        # Single check with JSON output (for scripting/automation)
        analysis = monitor.check_once()
        print(json.dumps(analysis, indent=2))
        sys.exit(0 if analysis['status'] == 'healthy' else 1)
    
    elif args.mode == 'monitor':
        # Continuous monitoring
        def trigger_diagnostic_crew(analysis):
            """This is where you'd trigger your diagnostic agent crew"""
            print("\n" + "="*70)
            print("🤖 TRIGGERING DIAGNOSTIC AGENT CREW")
            print("="*70)
            print("This is where you would:")
            print("  1. Initialize Diagnostic Agent")
            print("  2. Create Crew with Monitor + Diagnostic agents")
            print("  3. Pass analysis context to crew")
            print("  4. Let agents collaborate to investigate")
            print("="*70 + "\n")
            
            # TODO: Implement diagnostic crew trigger
            # from diagnostic_agent import DiagnosticAgent
            # diagnostic = DiagnosticAgent(llm)
            # crew = Crew(agents=[monitor.agent, diagnostic.agent], ...)
            # crew.kickoff()
        
        monitor.run_monitoring(on_issue_callback=trigger_diagnostic_crew)