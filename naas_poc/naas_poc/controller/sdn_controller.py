"""
NaaS PoC - SDN Controller
Manages flow tables, VNFs, and network policies centrally.
Exposes an internal API consumed by the NaaS Portal.
"""

from flask import Flask, jsonify, request
from datetime import datetime
import threading
import time
import uuid

app = Flask(__name__)

# ─── Global State ─────────────────────────────────────────────────────────────

nodes = {}          # registered virtual nodes
flow_table = []     # SDN flow rules
vnf_instances = {}  # deployed VNFs (firewall, load balancer, etc.)
traffic_log = []    # simulated traffic events
stats = {
    "total_flows": 0,
    "packets_forwarded": 0,
    "packets_dropped": 0,
    "vnf_count": 0,
}
lock = threading.Lock()

# ─── Node Registration ─────────────────────────────────────────────────────────

@app.route("/nodes", methods=["GET"])
def get_nodes():
    return jsonify(list(nodes.values()))

@app.route("/nodes/register", methods=["POST"])
def register_node():
    data = request.json
    node_id = data.get("node_id")
    with lock:
        nodes[node_id] = {
            "node_id": node_id,
            "name": data.get("name"),
            "ip": data.get("ip"),
            "type": data.get("type", "host"),
            "status": "active",
            "registered_at": datetime.now().isoformat(),
        }
    return jsonify({"status": "registered", "node_id": node_id}), 201

@app.route("/nodes/<node_id>/status", methods=["PUT"])
def update_node_status(node_id):
    data = request.json
    with lock:
        if node_id in nodes:
            nodes[node_id]["status"] = data.get("status", "active")
    return jsonify({"status": "updated"})

# ─── Flow Table Management ─────────────────────────────────────────────────────

@app.route("/flows", methods=["GET"])
def get_flows():
    return jsonify(flow_table)

@app.route("/flows", methods=["POST"])
def add_flow():
    data = request.json
    with lock:
        flow = {
            "flow_id": str(uuid.uuid4())[:8],
            "src": data.get("src"),
            "dst": data.get("dst"),
            "action": data.get("action", "forward"),
            "priority": data.get("priority", 100),
            "bandwidth_limit": data.get("bandwidth_limit", None),
            "protocol": data.get("protocol", "any"),
            "created_at": datetime.now().isoformat(),
            "hit_count": 0,
        }
        flow_table.append(flow)
        stats["total_flows"] += 1
    return jsonify({"status": "flow_added", "flow": flow}), 201

@app.route("/flows/<flow_id>", methods=["DELETE"])
def delete_flow(flow_id):
    with lock:
        global flow_table
        before = len(flow_table)
        flow_table = [f for f in flow_table if f["flow_id"] != flow_id]
        removed = before - len(flow_table)
    return jsonify({"status": "deleted", "removed": removed})

@app.route("/flows/simulate", methods=["POST"])
def simulate_packet():
    """Simulate a packet traversing the flow table."""
    data = request.json
    src = data.get("src")
    dst = data.get("dst")
    protocol = data.get("protocol", "tcp")
    size_kb = data.get("size_kb", 1)

    matched_flow = None
    for flow in sorted(flow_table, key=lambda x: -x["priority"]):
        src_match = flow["src"] in (src, "*", "any")
        dst_match = flow["dst"] in (dst, "*", "any")
        proto_match = flow["protocol"] in (protocol, "any")
        if src_match and dst_match and proto_match:
            matched_flow = flow
            break

    with lock:
        if matched_flow:
            action = matched_flow["action"]
            matched_flow["hit_count"] += 1
            if action == "forward":
                stats["packets_forwarded"] += 1
                result = "forwarded"
            elif action == "drop":
                stats["packets_dropped"] += 1
                result = "dropped"
            elif action == "redirect":
                stats["packets_forwarded"] += 1
                result = f"redirected to {matched_flow.get('redirect_to', 'VNF')}"
            else:
                result = action
        else:
            stats["packets_dropped"] += 1
            result = "dropped (no matching flow)"

        event = {
            "time": datetime.now().isoformat(),
            "src": src,
            "dst": dst,
            "protocol": protocol,
            "size_kb": size_kb,
            "result": result,
            "flow_id": matched_flow["flow_id"] if matched_flow else None,
        }
        traffic_log.append(event)
        if len(traffic_log) > 100:
            traffic_log.pop(0)

    return jsonify({"result": result, "matched_flow": matched_flow, "event": event})

# ─── VNF Management ───────────────────────────────────────────────────────────

@app.route("/vnfs", methods=["GET"])
def get_vnfs():
    return jsonify(list(vnf_instances.values()))

@app.route("/vnfs/deploy", methods=["POST"])
def deploy_vnf():
    data = request.json
    vnf_type = data.get("type")  # firewall, load_balancer, nat, ids
    vnf_id = f"vnf-{vnf_type}-{str(uuid.uuid4())[:6]}"

    config = data.get("config", {})

    with lock:
        vnf = {
            "vnf_id": vnf_id,
            "type": vnf_type,
            "status": "deploying",
            "node_id": data.get("node_id"),
            "config": config,
            "deployed_at": datetime.now().isoformat(),
        }
        vnf_instances[vnf_id] = vnf
        stats["vnf_count"] += 1

    # simulate deployment delay
    def activate():
        time.sleep(1.5)
        with lock:
            if vnf_id in vnf_instances:
                vnf_instances[vnf_id]["status"] = "active"
                # auto-create flow rules based on VNF type
                if vnf_type == "firewall":
                    for blocked in config.get("block_ips", []):
                        flow_table.append({
                            "flow_id": str(uuid.uuid4())[:8],
                            "src": blocked,
                            "dst": "*",
                            "action": "drop",
                            "priority": 200,
                            "bandwidth_limit": None,
                            "protocol": "any",
                            "created_at": datetime.now().isoformat(),
                            "hit_count": 0,
                            "vnf_id": vnf_id,
                        })
                        stats["total_flows"] += 1
                elif vnf_type == "load_balancer":
                    flow_table.append({
                        "flow_id": str(uuid.uuid4())[:8],
                        "src": "*",
                        "dst": config.get("vip", "10.0.0.100"),
                        "action": "redirect",
                        "redirect_to": str(config.get("backends", [])),
                        "priority": 150,
                        "bandwidth_limit": None,
                        "protocol": "tcp",
                        "created_at": datetime.now().isoformat(),
                        "hit_count": 0,
                        "vnf_id": vnf_id,
                    })
                    stats["total_flows"] += 1

    threading.Thread(target=activate, daemon=True).start()
    return jsonify({"status": "deploying", "vnf_id": vnf_id, "vnf": vnf}), 201

@app.route("/vnfs/<vnf_id>", methods=["DELETE"])
def remove_vnf(vnf_id):
    with lock:
        removed = vnf_instances.pop(vnf_id, None)
        if removed:
            global flow_table
            flow_table = [f for f in flow_table if f.get("vnf_id") != vnf_id]
            stats["vnf_count"] = max(0, stats["vnf_count"] - 1)
    return jsonify({"status": "removed" if removed else "not_found"})

# ─── Stats & Traffic ──────────────────────────────────────────────────────────

@app.route("/stats", methods=["GET"])
def get_stats():
    with lock:
        return jsonify({
            **stats,
            "active_nodes": sum(1 for n in nodes.values() if n["status"] == "active"),
            "active_vnfs": sum(1 for v in vnf_instances.values() if v["status"] == "active"),
            "flow_count": len(flow_table),
        })

@app.route("/traffic", methods=["GET"])
def get_traffic():
    return jsonify(traffic_log[-50:])

@app.route("/reset", methods=["POST"])
def reset():
    with lock:
        nodes.clear()
        flow_table.clear()
        vnf_instances.clear()
        traffic_log.clear()
        for k in stats:
            stats[k] = 0
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    print("Starting SDN Controller on port 6633...")
    app.run(port=6633, debug=False)
