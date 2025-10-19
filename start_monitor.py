#!/usr/bin/env python3
"""
Network Monitor Startup Script
Simple way to start your network monitoring system
"""

import sys
import os
import json
from datetime import datetime

# Add the agents directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'agents'))

def main():
    """Main startup function"""
    print("🌐 Network Monitor Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('agents/shared_tools.py'):
        print("❌ Error: Please run this from the crewai_starter directory")
        print("   cd /home/admin/Documents/crewai_starter")
        print("   python start_monitor.py")
        return
    
    print("✅ Found network monitoring tools")
    
    # Import the tools
    try:
        from shared_tools import NetworkTools, collect_full_diagnostic
        print("✅ Network tools imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're in the right directory and have installed dependencies")
        return
    
    # Create tools instance
    tools = NetworkTools()
    
    print("\n🔍 Running Network Diagnostic...")
    print("-" * 30)
    
    # Run basic tests
    print("1. Testing connectivity...")
    ping_result = tools.ping_test("8.8.8.8", count=3)
    if ping_result.get('success'):
        print(f"   ✅ Ping OK - {ping_result.get('avg_latency_ms', 'N/A')}ms")
    else:
        print(f"   ❌ Ping failed - {ping_result.get('error', 'Unknown error')}")
    
    print("2. Testing DNS...")
    dns_result = tools.dns_lookup("google.com")
    if dns_result.get('success'):
        print(f"   ✅ DNS OK - {dns_result.get('resolution_time_ms', 'N/A')}ms")
    else:
        print(f"   ❌ DNS failed - {dns_result.get('error', 'Unknown error')}")
    
    print("3. Checking WiFi signal...")
    signal_result = tools.get_signal_strength()
    if signal_result.get('success'):
        signal_level = signal_result.get('signal_level_dbm', 'N/A')
        quality = signal_result.get('quality_description', 'unknown')
        print(f"   ✅ Signal: {signal_level}dBm ({quality})")
    else:
        print(f"   ❌ Signal check failed - {signal_result.get('error', 'Unknown error')}")
    
    print("4. Checking network interface...")
    interface_result = tools.check_interface_status("wlan0")
    if interface_result.get('up'):
        print(f"   ✅ Interface wlan0 is UP")
    else:
        print(f"   ❌ Interface wlan0 is DOWN")
    
    print("\n📊 Network Status Summary:")
    print("-" * 30)
    
    # Determine overall status
    if ping_result.get('success') and dns_result.get('success') and interface_result.get('up'):
        status = "🟢 HEALTHY"
    elif ping_result.get('success') or dns_result.get('success'):
        status = "🟡 DEGRADED"
    else:
        status = "🔴 CRITICAL"
    
    print(f"Overall Status: {status}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show options
    print("\n🚀 What would you like to do next?")
    print("1. Run full diagnostic")
    print("2. Start continuous monitoring")
    print("3. Test packet capture (if tcpdump works)")
    print("4. Scan connected devices")
    print("5. Exit")
    
    try:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            print("\n🔬 Running full diagnostic...")
            diagnostic = collect_full_diagnostic()
            print(json.dumps(diagnostic, indent=2))
            
        elif choice == "2":
            print("\n🔄 Starting continuous monitoring...")
            print("Press Ctrl+C to stop")
            start_continuous_monitoring(tools)
            
        elif choice == "3":
            print("\n📦 Testing packet capture...")
            pcap_result = tools.capture_packets("wlan0", duration=5, count=20)
            if pcap_result.get('success'):
                print(f"   ✅ Captured {pcap_result.get('total_packets', 0)} packets")
                print(f"   Protocols: {pcap_result.get('protocols', {})}")
            else:
                print(f"   ❌ Packet capture failed: {pcap_result.get('error', 'Unknown error')}")
                
        elif choice == "4":
            print("\n🔍 Scanning connected devices...")
            devices_result = tools.scan_connected_devices("wlan0")
            if devices_result.get('success'):
                devices = devices_result.get('devices', [])
                print(f"   ✅ Found {len(devices)} devices")
                for device in devices[:5]:  # Show first 5
                    print(f"   - {device.get('ip', 'N/A')} ({device.get('mac', 'N/A')})")
            else:
                print(f"   ❌ Device scan failed: {devices_result.get('error', 'Unknown error')}")
                
        elif choice == "5":
            print("👋 Goodbye!")
            
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

def start_continuous_monitoring(tools):
    """Start continuous monitoring loop"""
    import time
    
    try:
        while True:
            # Collect metrics
            ping_result = tools.ping_test("8.8.8.8", count=2)
            dns_result = tools.dns_lookup("google.com")
            
            # Determine status
            if ping_result.get('success') and dns_result.get('success'):
                status = "✅ HEALTHY"
            elif ping_result.get('success') or dns_result.get('success'):
                status = "⚠️  DEGRADED"
            else:
                status = "🔴 CRITICAL"
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {status}")
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

if __name__ == "__main__":
    main()
