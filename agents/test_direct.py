#!/usr/bin/env python3
"""
Simple test to verify direct diagnostic functions work
"""

import subprocess
import json

def test_arp():
    """Test ARP table check"""
    try:
        result = subprocess.run(['arp', '-n'], capture_output=True, text=True, timeout=5)
        print("ARP Table:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"ARP test failed: {e}")
        return False

def test_ping():
    """Test ping"""
    try:
        result = subprocess.run(['ping', '-c', '3', '8.8.8.8'], capture_output=True, text=True, timeout=10)
        print("Ping to 8.8.8.8:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Ping test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing direct diagnostic functions...")
    
    print("\n1. Testing ARP table...")
    arp_ok = test_arp()
    
    print("\n2. Testing ping...")
    ping_ok = test_ping()
    
    print(f"\n✅ Results: ARP={arp_ok}, Ping={ping_ok}")
