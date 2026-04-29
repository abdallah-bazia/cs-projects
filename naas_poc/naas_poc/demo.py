"""
NaaS PoC - Full Demo Script
Runs the complete NaaS scenario:
  1. Create tenants
  2. Provision SD-WAN links
  3. Deploy Firewall-as-a-Service
  4. Deploy Load Balancer
  5. Simulate traffic (blocked & allowed)
  6. Show live monitoring
  7. Teardown services (on-demand deprovisioning)
"""

import requests
import time
import json

PORTAL = "http://localhost:5000/api"

def pretty(data):
    print(json.dumps(data, indent=2))

def step(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def post(path, data):
    r = requests.post(f"{PORTAL}{path}", json=data, timeout=5)
    return r.json()

def get(path):
    r = requests.get(f"{PORTAL}{path}", timeout=5)
    return r.json()

def delete(path):
    r = requests.delete(f"{PORTAL}{path}", timeout=5)
    return r.json()

# ── Step 1: Create Tenants ────────────────────────────────────────────────────
step("STEP 1 — Create NaaS Tenants")

t1 = post("/tenants", {"name": "University of Jijel", "plan": "enterprise"})
t2 = post("/tenants", {"name": "StartupCo DZ", "plan": "business"})
tenant1_id = t1["tenant"]["tenant_id"]
tenant2_id = t2["tenant"]["tenant_id"]

print(f"\n  ✓ Tenant 1: {t1['tenant']['name']} ({tenant1_id}) — {t1['tenant']['plan']} plan")
print(f"  ✓ Tenant 2: {t2['tenant']['name']} ({tenant2_id}) — {t2['tenant']['plan']} plan")
time.sleep(1)

# ── Step 2: Provision SD-WAN ──────────────────────────────────────────────────
step("STEP 2 — Provision SD-WAN Links (NaaS API)")

sdwan1 = post("/services/provision", {
    "tenant_id": tenant1_id,
    "service_type": "sdwan",
    "config": {
        "src_node": "10.0.0.1",
        "dst_node": "10.0.0.3",
        "bandwidth_mbps": 500,
    }
})
sdwan2 = post("/services/provision", {
    "tenant_id": tenant2_id,
    "service_type": "sdwan",
    "config": {
        "src_node": "10.0.0.2",
        "dst_node": "10.0.0.3",
        "bandwidth_mbps": 200,
    }
})
sdwan1_id = sdwan1["service"]["service_id"]
sdwan2_id = sdwan2["service"]["service_id"]

print(f"\n  ✓ SD-WAN for {t1['tenant']['name']}: {sdwan1['status']} ({sdwan1_id})")
print(f"  ✓ SD-WAN for {t2['tenant']['name']}: {sdwan2['status']} ({sdwan2_id})")
time.sleep(1)

# ── Step 3: Deploy Firewall-as-a-Service ──────────────────────────────────────
step("STEP 3 — Deploy Firewall-as-a-Service (VNF)")

fw = post("/services/provision", {
    "tenant_id": tenant1_id,
    "service_type": "firewall",
    "config": {
        "node_id": "node-gw",
        "block_ips": ["192.168.5.99", "10.99.0.0"],
        "policy": "deny_unknown",
    }
})
fw_id = fw["service"]["service_id"]
print(f"\n  ✓ Firewall deployed: {fw['status']} ({fw_id})")
print(f"  ✓ Blocked IPs: 192.168.5.99, 10.99.0.0")
print("  ⏳ Waiting for VNF to activate (1.5s)...")
time.sleep(2.5)

# ── Step 4: Deploy Load Balancer ──────────────────────────────────────────────
step("STEP 4 — Deploy Load Balancer VNF")

lb = post("/services/provision", {
    "tenant_id": tenant1_id,
    "service_type": "loadbalancer",
    "config": {
        "node_id": "node-h3",
        "vip": "10.0.0.100",
        "backends": ["10.0.0.3", "10.0.0.4", "10.0.0.5"],
        "algorithm": "round_robin",
    }
})
lb_id = lb["service"]["service_id"]
print(f"\n  ✓ Load Balancer deployed: {lb['status']} ({lb_id})")
print(f"  ✓ VIP: 10.0.0.100 → backends [10.0.0.3, 10.0.0.4, 10.0.0.5]")
time.sleep(2.5)

# ── Step 5: Simulate Traffic ──────────────────────────────────────────────────
step("STEP 5 — Simulate Traffic Through NaaS (SDN Flow Table)")

scenarios = [
    {"src": "10.0.0.1",    "dst": "10.0.0.3",   "protocol": "tcp", "size_kb": 100, "desc": "Branch A → Data Center (SD-WAN)"},
    {"src": "10.0.0.2",    "dst": "10.0.0.3",   "protocol": "tcp", "size_kb": 80,  "desc": "Branch B → Data Center (SD-WAN)"},
    {"src": "192.168.5.99","dst": "10.0.0.3",   "protocol": "tcp", "size_kb": 5,   "desc": "ATTACKER → Data Center (Firewall)"},
    {"src": "10.99.0.0",   "dst": "10.0.0.1",   "protocol": "tcp", "size_kb": 5,   "desc": "BLOCKED IP → Branch A (Firewall)"},
    {"src": "10.0.0.1",    "dst": "10.0.0.100", "protocol": "tcp", "size_kb": 60,  "desc": "Branch A → VIP (Load Balancer)"},
    {"src": "10.0.1.1",    "dst": "10.0.0.3",   "protocol": "udp", "size_kb": 10,  "desc": "IoT Sensor → Data Center"},
]

print()
for s in scenarios:
    r = post("/simulate/traffic", {
        "src": s["src"], "dst": s["dst"],
        "protocol": s["protocol"], "size_kb": s["size_kb"],
    })
    result = r.get("result", "unknown")
    icon = "✓" if "forward" in result or "redirect" in result else "✗"
    print(f"  {icon} {s['desc']}")
    print(f"      Result: {result}")
    time.sleep(0.5)

# ── Step 6: Live Monitoring ───────────────────────────────────────────────────
step("STEP 6 — Live Monitoring Dashboard (NaaS Observability)")

stats = get("/monitor/stats")
ctrl = stats["controller"]
portal = stats["portal"]

print(f"""
  ┌─────────────────────────────────────────┐
  │        NaaS Platform — Live Stats       │
  ├─────────────────────────────────────────┤
  │  Active Nodes       : {ctrl.get('active_nodes',0):<5}               │
  │  Flow Rules         : {ctrl.get('flow_count',0):<5}               │
  │  Active VNFs        : {ctrl.get('active_vnfs',0):<5}               │
  │  Packets Forwarded  : {ctrl.get('packets_forwarded',0):<5}               │
  │  Packets Dropped    : {ctrl.get('packets_dropped',0):<5}               │
  ├─────────────────────────────────────────┤
  │  Tenants            : {portal.get('total_tenants',0):<5}               │
  │  Total Services     : {portal.get('total_services',0):<5}               │
  │  Active Services    : {portal.get('active_services',0):<5}               │
  └─────────────────────────────────────────┘
""")

flows = get("/monitor/flows")
print(f"  Flow Table ({len(flows)} rules):")
for f in flows:
    print(f"    [{f['priority']:3}] {f['src']:<18} → {f['dst']:<18} | {f['action']:<10} | hits: {f['hit_count']}")

# ── Step 7: Teardown (on-demand deprovisioning) ───────────────────────────────
step("STEP 7 — On-Demand Service Teardown (NaaS Elasticity)")

print("\n  Deprovisioning SD-WAN for StartupCo DZ...")
r = delete(f"/services/{sdwan2_id}")
print(f"  ✓ {r['status']}")

print("  Removing Load Balancer VNF...")
r = delete(f"/services/{lb_id}")
print(f"  ✓ {r['status']}")

time.sleep(1)
stats2 = get("/monitor/stats")
print(f"\n  Services after teardown: {stats2['portal']['total_services']}")
print(f"  Active services        : {stats2['portal']['active_services']}")

step("DEMO COMPLETE")
print("""
  This PoC demonstrated:
  ✓ Multi-tenant NaaS platform with REST API provisioning
  ✓ SDN centralized flow table management
  ✓ SD-WAN link provisioning via API (no hardware)
  ✓ Firewall-as-a-Service VNF deployment with auto flow rules
  ✓ Load Balancer VNF with virtual IP and backend pool
  ✓ Real-time traffic simulation through NaaS policies
  ✓ Live monitoring and observability
  ✓ On-demand service teardown (NaaS elasticity)
""")
