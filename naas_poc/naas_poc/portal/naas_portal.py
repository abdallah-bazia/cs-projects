"""
NaaS PoC - Service Portal API + Web UI
"""

from flask import Flask, jsonify, request, render_template
from datetime import datetime
import requests
import uuid

# 👇 IMPORTANT: tells Flask where HTML is
app = Flask(__name__, template_folder="templates")

CONTROLLER_URL = "http://localhost:6633"

tenants = {}
services = {}

# ─── UI ROUTE ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ctrl(method, path, **kwargs):
    try:
        resp = getattr(requests, method)(
            f"{CONTROLLER_URL}{path}", **kwargs, timeout=5
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ─── Tenant Management ───────────────────────────────────────────────────────

@app.route("/api/tenants", methods=["GET"])
def list_tenants():
    return jsonify(list(tenants.values()))


@app.route("/api/tenants", methods=["POST"])
def create_tenant():
    data = request.json

    tenant_id = f"tenant-{str(uuid.uuid4())[:8]}"
    plan = data.get("plan", "basic")

    tenant = {
        "tenant_id": tenant_id,
        "name": data.get("name"),
        "plan": plan,
        "bandwidth_quota_mbps": {
            "basic": 100,
            "business": 500,
            "enterprise": 10000
        }.get(plan, 100),
        "created_at": datetime.now().isoformat(),
        "services": [],
    }

    tenants[tenant_id] = tenant
    return jsonify({"status": "created", "tenant": tenant}), 201


@app.route("/api/tenants/<tenant_id>", methods=["GET"])
def get_tenant(tenant_id):
    t = tenants.get(tenant_id)
    if not t:
        return jsonify({"error": "not found"}), 404
    return jsonify(t)


# ─── Network Service Provisioning ────────────────────────────────────────────

@app.route("/api/services", methods=["GET"])
def list_services():
    return jsonify(list(services.values()))


@app.route("/api/services/provision", methods=["POST"])
def provision_service():
    data = request.json
    tenant_id = data.get("tenant_id")
    service_type = data.get("service_type")

    if tenant_id not in tenants:
        return jsonify({"error": "tenant not found"}), 404

    service_id = f"svc-{str(uuid.uuid4())[:8]}"

    service = {
        "service_id": service_id,
        "tenant_id": tenant_id,
        "type": service_type,
        "status": "provisioning",
        "config": data.get("config", {}),
        "created_at": datetime.now().isoformat(),
        "vnf_id": None,
        "flow_ids": [],
    }

    # ─── SD-WAN ─────────────────────────────────
    if service_type == "sdwan":
        cfg = data.get("config", {})
        result = ctrl("post", "/flows", json={
            "src": cfg.get("src_node"),
            "dst": cfg.get("dst_node"),
            "action": "forward",
            "priority": 100,
            "bandwidth_limit": cfg.get("bandwidth_mbps", 100),
            "protocol": "any",
        })

        if "flow" in result:
            service["flow_ids"].append(result["flow"]["flow_id"])
            service["status"] = "active"
        else:
            service["status"] = "failed"

    # ─── FIREWALL ───────────────────────────────
    elif service_type == "firewall":
        result = ctrl("post", "/vnfs/deploy", json={
            "type": "firewall",
            "node_id": data["config"].get("node_id"),
            "config": data["config"],
        })

        if "vnf_id" in result:
            service["vnf_id"] = result["vnf_id"]
            service["status"] = "deploying"
        else:
            service["status"] = "failed"

    # ─── LOAD BALANCER ──────────────────────────
    elif service_type == "loadbalancer":
        result = ctrl("post", "/vnfs/deploy", json={
            "type": "load_balancer",
            "node_id": data["config"].get("node_id"),
            "config": data["config"],
        })

        if "vnf_id" in result:
            service["vnf_id"] = result["vnf_id"]
            service["status"] = "deploying"
        else:
            service["status"] = "failed"

    # ─── NAT ────────────────────────────────────
    elif service_type == "nat":
        result = ctrl("post", "/flows", json={
            "src": data["config"].get("private_subnet", "192.168.0.0/24"),
            "dst": "*",
            "action": "forward",
            "priority": 120,
            "protocol": "any",
        })

        if "flow" in result:
            service["flow_ids"].append(result["flow"]["flow_id"])
            service["status"] = "active"
        else:
            service["status"] = "failed"

    services[service_id] = service
    tenants[tenant_id]["services"].append(service_id)

    return jsonify({"status": service["status"], "service": service}), 201


@app.route("/api/services/<service_id>", methods=["GET"])
def get_service(service_id):
    svc = services.get(service_id)
    if not svc:
        return jsonify({"error": "not found"}), 404

    if svc.get("vnf_id"):
        vnfs = ctrl("get", "/vnfs")
        for v in vnfs if isinstance(vnfs, list) else []:
            if v["vnf_id"] == svc["vnf_id"]:
                svc["status"] = v["status"]

    return jsonify(svc)


@app.route("/api/services/<service_id>", methods=["DELETE"])
def delete_service(service_id):
    svc = services.pop(service_id, None)
    if not svc:
        return jsonify({"error": "not found"}), 404

    if svc.get("vnf_id"):
        ctrl("delete", f"/vnfs/{svc['vnf_id']}")

    for fid in svc.get("flow_ids", []):
        ctrl("delete", f"/flows/{fid}")

    t = tenants.get(svc["tenant_id"])
    if t and service_id in t["services"]:
        t["services"].remove(service_id)

    return jsonify({"status": "deleted"})


# ─── Simulation ──────────────────────────────────────────────────────────────

@app.route("/api/flows/add", methods=["POST"])
def add_flow():
    data = request.json
    return jsonify(ctrl("post", "/flows", json=data))

@app.route("/api/flows/<flow_id>", methods=["DELETE"])
def delete_flow(flow_id):
    return jsonify(ctrl("delete", f"/flows/{flow_id}"))

@app.route("/api/simulate/traffic", methods=["POST"])
def simulate():
    data = request.json
    return jsonify(ctrl("post", "/flows/simulate", json=data))


# ─── Monitoring ──────────────────────────────────────────────────────────────

@app.route("/api/monitor/stats", methods=["GET"])
def monitor_stats():
    ctrl_stats = ctrl("get", "/stats")
    return jsonify({
        "controller": ctrl_stats,
        "portal": {
            "total_tenants": len(tenants),
            "total_services": len(services),
            "active_services": sum(
                1 for s in services.values() if s["status"] == "active"
            ),
        }
    })


@app.route("/api/monitor/traffic", methods=["GET"])
def monitor_traffic():
    return jsonify(ctrl("get", "/traffic"))


@app.route("/api/monitor/nodes", methods=["GET"])
def monitor_nodes():
    return jsonify(ctrl("get", "/nodes"))


@app.route("/api/monitor/flows", methods=["GET"])
def monitor_flows():
    return jsonify(ctrl("get", "/flows"))


@app.route("/api/monitor/vnfs", methods=["GET"])
def monitor_vnfs():
    return jsonify(ctrl("get", "/vnfs"))


# ─── RUN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting NaaS Portal on http://localhost:5000")
    app.run(port=5000, debug=True)