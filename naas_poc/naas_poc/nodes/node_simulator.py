"""
NaaS PoC - Virtual Node Simulator
Simulates network hosts/nodes that register with the SDN controller
and generate traffic to demonstrate NaaS in action.
"""

import requests
import time
import random
import threading
import sys

CONTROLLER_URL = "http://localhost:6633"
PORTAL_URL = "http://localhost:5000"

NODES = [
    {"node_id": "node-h1", "name": "Host-1 (Branch Office A)", "ip": "10.0.0.1", "type": "host"},
    {"node_id": "node-h2", "name": "Host-2 (Branch Office B)", "ip": "10.0.0.2", "type": "host"},
    {"node_id": "node-h3", "name": "Host-3 (Data Center)",     "ip": "10.0.0.3", "type": "server"},
    {"node_id": "node-h4", "name": "Host-4 (IoT Gateway)",     "ip": "10.0.1.1", "type": "iot"},
    {"node_id": "node-gw", "name": "Gateway (Internet Edge)",  "ip": "10.0.0.254","type": "gateway"},
]

TRAFFIC_PATTERNS = [
    {"src": "10.0.0.1", "dst": "10.0.0.2", "protocol": "tcp",  "size_kb": 50,   "label": "Branch A → Branch B"},
    {"src": "10.0.0.1", "dst": "10.0.0.3", "protocol": "tcp",  "size_kb": 200,  "label": "Branch A → Data Center"},
    {"src": "10.0.0.2", "dst": "10.0.0.3", "protocol": "tcp",  "size_kb": 150,  "label": "Branch B → Data Center"},
    {"src": "10.0.1.1", "dst": "10.0.0.3", "protocol": "udp",  "size_kb": 10,   "label": "IoT → Data Center"},
    {"src": "192.168.5.99", "dst": "10.0.0.3", "protocol": "tcp", "size_kb": 5, "label": "ATTACK → Data Center"},
    {"src": "10.0.0.1", "dst": "10.0.0.100","protocol": "tcp",  "size_kb": 80,   "label": "Branch A → VIP (LB)"},
]

def register_nodes():
    print("\n[*] Registering virtual nodes with SDN Controller...")
    for node in NODES:
        try:
            r = requests.post(f"{CONTROLLER_URL}/nodes/register", json=node, timeout=3)
            print(f"    ✓ Registered: {node['name']} ({node['ip']})")
        except Exception as e:
            print(f"    ✗ Failed to register {node['name']}: {e}")
    print()

def simulate_traffic(duration=60, interval=2):
    print(f"[*] Starting traffic simulation for {duration}s (interval: {interval}s)\n")
    end_time = time.time() + duration
    count = 0

    while time.time() < end_time:
        pattern = random.choice(TRAFFIC_PATTERNS)
        try:
            r = requests.post(f"{PORTAL_URL}/api/simulate/traffic", json={
                "src": pattern["src"],
                "dst": pattern["dst"],
                "protocol": pattern["protocol"],
                "size_kb": pattern["size_kb"],
            }, timeout=3)
            data = r.json()
            result = data.get("result", "unknown")
            emoji = "✓" if "forward" in result or "redirect" in result else "✗"
            print(f"    {emoji} [{pattern['label']}] → {result}")
            count += 1
        except Exception as e:
            print(f"    ! Traffic sim error: {e}")
        time.sleep(interval)

    print(f"\n[*] Traffic simulation done. {count} packets sent.")

def print_stats():
    print("\n[*] Final Network Stats:")
    try:
        r = requests.get(f"{PORTAL_URL}/api/monitor/stats", timeout=3)
        stats = r.json()
        ctrl = stats.get("controller", {})
        portal = stats.get("portal", {})
        print(f"    Nodes active      : {ctrl.get('active_nodes', 0)}")
        print(f"    Flow rules        : {ctrl.get('flow_count', 0)}")
        print(f"    VNFs active       : {ctrl.get('active_vnfs', 0)}")
        print(f"    Packets forwarded : {ctrl.get('packets_forwarded', 0)}")
        print(f"    Packets dropped   : {ctrl.get('packets_dropped', 0)}")
        print(f"    Tenants           : {portal.get('total_tenants', 0)}")
        print(f"    Active services   : {portal.get('active_services', 0)}")
    except Exception as e:
        print(f"    Error fetching stats: {e}")

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    register_nodes()
    simulate_traffic(duration=duration, interval=2)
    print_stats()
