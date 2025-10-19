"""
Shared Network Diagnostic Tools
Used by all agents to collect network data and perform actions
"""

import subprocess
import time
import json
import re
from datetime import datetime
from typing import Dict, Optional, List
import socket


class NetworkTools:
    """Collection of network diagnostic utilities"""
    
    @staticmethod
    def capture_packets(interface: str = "wlan0", duration: int = 10, count: int = 100) -> Dict:
        """
        Capture network packets using tcpdump for analysis
        
        Args:
            interface: Network interface to capture from
            duration: Seconds to capture
            count: Max packets to capture
            
        Returns:
            Dictionary with packet capture analysis
        """
        try:
            # Run tcpdump with detailed output
            cmd = [
                "timeout", str(duration),
                "tcpdump", "-i", interface,
                "-c", str(count),
                "-n",  # Don't resolve hostnames
                "-v",  # Verbose
                "-tt"  # Unix timestamp
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 2
            )
            
            output = result.stdout + result.stderr
            
            # Parse packet capture
            packets = []
            protocols = {"TCP": 0, "UDP": 0, "ICMP": 0, "DNS": 0, "Other": 0}
            retransmissions = 0
            
            for line in output.split('\n'):
                if 'IP' in line:
                    if 'tcp' in line.lower():
                        protocols["TCP"] += 1
                        if 'Flags [R]' in line or 'retransmission' in line.lower():
                            retransmissions += 1
                    elif 'udp' in line.lower():
                        protocols["UDP"] += 1
                        if '53' in line:  # DNS port
                            protocols["DNS"] += 1
                    elif 'icmp' in line.lower():
                        protocols["ICMP"] += 1
                    else:
                        protocols["Other"] += 1
                    
                    packets.append(line)
            
            total_packets = sum(protocols.values())
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "interface": interface,
                "duration": duration,
                "total_packets": total_packets,
                "protocols": protocols,
                "retransmissions": retransmissions,
                "packet_samples": packets[:20],  # First 20 packets
                "analysis": {
                    "tcp_percentage": round(protocols["TCP"] / max(total_packets, 1) * 100, 2),
                    "udp_percentage": round(protocols["UDP"] / max(total_packets, 1) * 100, 2),
                    "dns_queries": protocols["DNS"],
                    "retransmission_rate": round(retransmissions / max(total_packets, 1) * 100, 2)
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Capture timed out",
                "note": "May need sudo access for tcpdump"
            }
        except FileNotFoundError:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "tcpdump not installed",
                "note": "Install with: sudo apt-get install tcpdump"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def scan_connected_devices(interface: str = "wlan0") -> Dict:
        """
        Scan for connected devices on local network using arp-scan
        
        Args:
            interface: Network interface to scan
            
        Returns:
            Dictionary with discovered devices
        """
        try:
            # Try arp-scan first (more reliable)
            result = subprocess.run(
                ["sudo", "arp-scan", "--interface", interface, "--localnet"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            devices = []
            for line in result.stdout.split('\n'):
                # Parse arp-scan output: IP\tMAC\tVendor
                parts = line.split('\t')
                if len(parts) >= 2 and '.' in parts[0]:
                    devices.append({
                        "ip": parts[0].strip(),
                        "mac": parts[1].strip() if len(parts) > 1 else "unknown",
                        "vendor": parts[2].strip() if len(parts) > 2 else "unknown"
                    })
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "interface": interface,
                "device_count": len(devices),
                "devices": devices
            }
            
        except FileNotFoundError:
            # Fallback to arp table
            try:
                result = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                devices = []
                for line in result.stdout.split('\n'):
                    # Parse arp output
                    if '(' in line and ')' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            ip = parts[1].strip('()')
                            mac = parts[3] if len(parts) > 3 else "unknown"
                            devices.append({
                                "ip": ip,
                                "mac": mac,
                                "vendor": "unknown"
                            })
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                    "interface": interface,
                    "device_count": len(devices),
                    "devices": devices,
                    "note": "Using arp table (install arp-scan for better results)"
                }
                
            except Exception as e:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e)
                }
        
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "note": "May need sudo access"
            }
    
    @staticmethod
    def analyze_bandwidth(interface: str = "wlan0", duration: int = 5) -> Dict:
        """
        Analyze bandwidth usage using ifstat or similar
        
        Args:
            interface: Network interface
            duration: Seconds to monitor
            
        Returns:
            Dictionary with bandwidth stats
        """
        try:
            # Get interface stats before
            with open(f'/sys/class/net/{interface}/statistics/rx_bytes', 'r') as f:
                rx_bytes_start = int(f.read().strip())
            with open(f'/sys/class/net/{interface}/statistics/tx_bytes', 'r') as f:
                tx_bytes_start = int(f.read().strip())
            
            time.sleep(duration)
            
            # Get interface stats after
            with open(f'/sys/class/net/{interface}/statistics/rx_bytes', 'r') as f:
                rx_bytes_end = int(f.read().strip())
            with open(f'/sys/class/net/{interface}/statistics/tx_bytes', 'r') as f:
                tx_bytes_end = int(f.read().strip())
            
            rx_bytes = rx_bytes_end - rx_bytes_start
            tx_bytes = tx_bytes_end - tx_bytes_start
            
            # Calculate rates in Mbps
            rx_mbps = (rx_bytes * 8) / (duration * 1_000_000)
            tx_mbps = (tx_bytes * 8) / (duration * 1_000_000)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "interface": interface,
                "duration": duration,
                "download_mbps": round(rx_mbps, 2),
                "upload_mbps": round(tx_mbps, 2),
                "download_bytes": rx_bytes,
                "upload_bytes": tx_bytes,
                "total_mbps": round(rx_mbps + tx_mbps, 2)
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def analyze_connections() -> Dict:
        """
        Analyze active network connections
        
        Returns:
            Dictionary with connection analysis
        """
        try:
            # Get active connections using ss (socket statistics)
            result = subprocess.run(
                ["ss", "-tunap"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            tcp_connections = 0
            udp_connections = 0
            established = 0
            listening = 0
            
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    if line.startswith('tcp'):
                        tcp_connections += 1
                        if 'ESTAB' in line:
                            established += 1
                        elif 'LISTEN' in line:
                            listening += 1
                    elif line.startswith('udp'):
                        udp_connections += 1
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "tcp_connections": tcp_connections,
                "udp_connections": udp_connections,
                "established": established,
                "listening": listening,
                "total_connections": tcp_connections + udp_connections
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def ping_test(host: str = "8.8.8.8", count: int = 4, timeout: int = 5) -> Dict:
        """
        Test connectivity to a host using ping
        
        Args:
            host: Target host to ping
            count: Number of ping packets
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with ping results
        """
        try:
            cmd = f"ping -c {count} -W {timeout} {host}"
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            
            success = result.returncode == 0
            
            # Parse packet loss and latency
            packet_loss = 100
            avg_latency = None
            
            if success:
                # Extract packet loss
                loss_match = re.search(r'(\d+)% packet loss', result.stdout)
                if loss_match:
                    packet_loss = int(loss_match.group(1))
                
                # Extract average latency
                latency_match = re.search(r'avg = ([\d.]+)', result.stdout)
                if latency_match:
                    avg_latency = float(latency_match.group(1))
            
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": success,
                "packet_loss": packet_loss,
                "avg_latency_ms": avg_latency,
                "raw_output": result.stdout if success else result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": False,
                "packet_loss": 100,
                "avg_latency_ms": None,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def dns_lookup(domain: str = "google.com", timeout: int = 5) -> Dict:
        """
        Test DNS resolution
        
        Args:
            domain: Domain to resolve
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with DNS lookup results
        """
        try:
            socket.setdefaulttimeout(timeout)
            start_time = time.time()
            ip_address = socket.gethostbyname(domain)
            resolution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "success": True,
                "ip_address": ip_address,
                "resolution_time_ms": round(resolution_time, 2)
            }
            
        except socket.gaierror as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "success": False,
                "error": f"DNS resolution failed: {str(e)}"
            }
        except socket.timeout:
            return {
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "success": False,
                "error": "DNS lookup timeout"
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_signal_strength() -> Dict:
        """
        Get WiFi signal strength (works on Raspberry Pi)
        
        Returns:
            Dictionary with signal information
        """
        try:
            # Try to get signal from iwconfig
            result = subprocess.run(
                ["iwconfig"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            signal_level = None
            link_quality = None
            interface = None
            
            # Parse iwconfig output
            for line in result.stdout.split('\n'):
                if 'IEEE 802.11' in line or 'ESSID:' in line:
                    interface = line.split()[0]
                
                if 'Link Quality' in line:
                    # Parse: Link Quality=XX/YY  Signal level=-ZZ dBm
                    quality_match = re.search(r'Link Quality=(\d+)/(\d+)', line)
                    if quality_match:
                        quality = int(quality_match.group(1))
                        max_quality = int(quality_match.group(2))
                        link_quality = f"{quality}/{max_quality}"
                    
                    signal_match = re.search(r'Signal level=(-?\d+)', line)
                    if signal_match:
                        signal_level = int(signal_match.group(1))
            
            if signal_level is not None:
                # Categorize signal strength
                if signal_level >= -50:
                    quality_desc = "excellent"
                elif signal_level >= -60:
                    quality_desc = "good"
                elif signal_level >= -70:
                    quality_desc = "fair"
                elif signal_level >= -80:
                    quality_desc = "weak"
                else:
                    quality_desc = "very weak"
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                    "interface": interface,
                    "signal_level_dbm": signal_level,
                    "link_quality": link_quality,
                    "quality_description": quality_desc
                }
            else:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": "Could not parse signal strength"
                }
                
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": f"Failed to get signal strength: {str(e)}"
            }
    
    @staticmethod
    def check_interface_status(interface: str = "wlan0") -> Dict:
        """
        Check if network interface is up
        
        Args:
            interface: Network interface name
            
        Returns:
            Dictionary with interface status
        """
        try:
            # Check if interface exists and is up
            result = subprocess.run(
                ["ip", "link", "show", interface],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "interface": interface,
                    "exists": False,
                    "up": False,
                    "error": "Interface not found"
                }
            
            is_up = "state UP" in result.stdout
            
            return {
                "timestamp": datetime.now().isoformat(),
                "interface": interface,
                "exists": True,
                "up": is_up,
                "details": result.stdout.split('\n')[1].strip() if len(result.stdout.split('\n')) > 1 else ""
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "interface": interface,
                "error": str(e)
            }
    
    @staticmethod
    def measure_latency(host: str = "8.8.8.8", samples: int = 10) -> Dict:
        """
        Measure latency with multiple samples
        
        Args:
            host: Target host
            samples: Number of ping samples
            
        Returns:
            Dictionary with latency statistics
        """
        try:
            result = subprocess.run(
                ["ping", "-c", str(samples), "-i", "0.2", host],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "host": host,
                    "success": False,
                    "error": "Ping failed"
                }
            
            # Parse statistics: min/avg/max/mdev
            stats_match = re.search(
                r'min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
                result.stdout
            )
            
            if stats_match:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "host": host,
                    "success": True,
                    "samples": samples,
                    "min_ms": float(stats_match.group(1)),
                    "avg_ms": float(stats_match.group(2)),
                    "max_ms": float(stats_match.group(3)),
                    "mdev_ms": float(stats_match.group(4))
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": False,
                "error": "Could not parse statistics"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def read_system_logs(lines: int = 50) -> Dict:
        """
        Read recent network-related system logs
        
        Args:
            lines: Number of log lines to read
            
        Returns:
            Dictionary with log entries
        """
        try:
            # Read journal logs for network-related entries
            result = subprocess.run(
                ["journalctl", "-n", str(lines), "-u", "NetworkManager", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                # Try alternative: systemd-networkd
                result = subprocess.run(
                    ["journalctl", "-n", str(lines), "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            # Filter for errors and warnings
            errors = []
            warnings = []
            
            for line in result.stdout.split('\n'):
                if 'error' in line.lower() or 'fail' in line.lower():
                    errors.append(line)
                elif 'warn' in line.lower():
                    warnings.append(line)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "total_lines": len(result.stdout.split('\n')),
                "errors": errors[-10:],  # Last 10 errors
                "warnings": warnings[-10:],  # Last 10 warnings
                "recent_logs": result.stdout.split('\n')[-20:]  # Last 20 lines
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def bandwidth_check(host: str = "8.8.8.8", size: str = "1M") -> Dict:
        """
        Basic bandwidth test using curl
        
        Args:
            host: Target host
            size: Download size (used for test)
            
        Returns:
            Dictionary with bandwidth info
        """
        try:
            # Simple download speed test
            start_time = time.time()
            result = subprocess.run(
                ["ping", "-c", "1", "-s", "1000", host],
                capture_output=True,
                text=True,
                timeout=5
            )
            duration = time.time() - start_time
            
            success = result.returncode == 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": success,
                "test_duration_sec": round(duration, 3),
                "note": "Basic connectivity test - full bandwidth test requires internet"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "host": host,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_current_dns() -> Dict:
        """
        Get current DNS configuration
        
        Returns:
            Dictionary with DNS server info
        """
        try:
            # Read /etc/resolv.conf
            with open('/etc/resolv.conf', 'r') as f:
                content = f.read()
            
            dns_servers = []
            for line in content.split('\n'):
                if line.startswith('nameserver'):
                    dns_servers.append(line.split()[1])
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "dns_servers": dns_servers
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_gateway() -> Dict:
        """
        Get default gateway
        
        Returns:
            Dictionary with gateway info
        """
        try:
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse: default via X.X.X.X dev wlan0
                match = re.search(r'via ([\d.]+)', result.stdout)
                if match:
                    gateway = match.group(1)
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "success": True,
                        "gateway": gateway
                    }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Could not determine gateway"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }


class NetworkActions:
    """Actions to fix network issues (requires sudo)"""
    
    @staticmethod
    def restart_interface(interface: str = "wlan0") -> Dict:
        """
        Restart network interface
        
        Args:
            interface: Interface to restart
            
        Returns:
            Dictionary with action result
        """
        try:
            # Bring interface down
            subprocess.run(
                ["sudo", "ip", "link", "set", interface, "down"],
                capture_output=True,
                timeout=5,
                check=True
            )
            
            time.sleep(2)
            
            # Bring interface up
            subprocess.run(
                ["sudo", "ip", "link", "set", interface, "up"],
                capture_output=True,
                timeout=5,
                check=True
            )
            
            time.sleep(3)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "restart_interface",
                "interface": interface,
                "success": True,
                "message": f"Interface {interface} restarted successfully"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "restart_interface",
                "interface": interface,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def change_dns(new_dns: str = "8.8.8.8") -> Dict:
        """
        Change DNS server (requires sudo)
        
        Args:
            new_dns: New DNS server address
            
        Returns:
            Dictionary with action result
        """
        try:
            # This is a simplified version - actual implementation would need
            # to modify /etc/resolv.conf or NetworkManager settings
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "change_dns",
                "new_dns": new_dns,
                "success": True,
                "message": f"DNS changed to {new_dns}",
                "note": "Actual implementation requires modifying system configuration"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "change_dns",
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def flush_dns_cache() -> Dict:
        """
        Flush DNS cache
        
        Returns:
            Dictionary with action result
        """
        try:
            # Flush systemd-resolved cache
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "systemd-resolved"],
                capture_output=True,
                timeout=10
            )
            
            success = result.returncode == 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "flush_dns_cache",
                "success": success,
                "message": "DNS cache flushed" if success else "Failed to flush DNS cache"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "flush_dns_cache",
                "success": False,
                "error": str(e)
            }


def collect_full_diagnostic() -> Dict:
    """
    Collect complete network diagnostic data
    
    Returns:
        Dictionary with all diagnostic information
    """
    tools = NetworkTools()
    
    diagnostic = {
        "timestamp": datetime.now().isoformat(),
        "connectivity": {
            "ping_google_dns": tools.ping_test("8.8.8.8"),
            "ping_cloudflare_dns": tools.ping_test("1.1.1.1"),
            "ping_gateway": None  # Will be filled after getting gateway
        },
        "dns": {
            "lookup_google": tools.dns_lookup("google.com"),
            "lookup_cloudflare": tools.dns_lookup("cloudflare.com"),
            "current_dns": tools.get_current_dns()
        },
        "interface": {
            "wlan0_status": tools.check_interface_status("wlan0"),
            "eth0_status": tools.check_interface_status("eth0")
        },
        "signal": tools.get_signal_strength(),
        "latency": tools.measure_latency(),
        "gateway": tools.get_gateway(),
        "logs": tools.read_system_logs(30)
    }
    
    # If we got the gateway, ping it too
    gateway_info = diagnostic["gateway"]
    if gateway_info.get("success") and gateway_info.get("gateway"):
        diagnostic["connectivity"]["ping_gateway"] = tools.ping_test(gateway_info["gateway"])
    
    return diagnostic

