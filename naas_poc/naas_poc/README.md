---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install flask requests
```

### 2. Start the SDN Controller

```bash
python controller.py
# Runs on http://localhost:6633
```

### 3. Start the NaaS Portal

```bash
python portal.py
# Runs on http://localhost:5000
```

### 4. Run the full demo

```bash
python demo.py
```

Or simulate live node traffic:

```bash
python node_simulator.py 60   # runs for 60 seconds
```

---

## 🎬 Demo Walkthrough

The `demo.py` script runs a full 7-step NaaS scenario:

| Step | Action |
|---|---|
| 1 | Create tenants (University of Jijel, StartupCo DZ) |
| 2 | Provision SD-WAN links via API |
| 3 | Deploy Firewall-as-a-Service VNF with IP block rules |
| 4 | Deploy Load Balancer VNF with virtual IP |
| 5 | Simulate traffic — allowed, blocked, and redirected packets |
| 6 | View live monitoring dashboard |
| 7 | On-demand service teardown |

---

## 📡 API Reference

### SDN Controller (`:6633`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/nodes` | List registered nodes |
| POST | `/nodes/register` | Register a virtual node |
| GET | `/flows` | Get all flow rules |
| POST | `/flows` | Add a flow rule |
| DELETE | `/flows/<id>` | Delete a flow rule |
| POST | `/flows/simulate` | Simulate a packet |
| GET | `/vnfs` | List VNF instances |
| POST | `/vnfs/deploy` | Deploy a VNF |
| DELETE | `/vnfs/<id>` | Remove a VNF |
| GET | `/stats` | Live network statistics |

### NaaS Portal (`:5000`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/tenants` | Create a tenant |
| POST | `/api/services/provision` | Provision a network service |
| DELETE | `/api/services/<id>` | Deprovision a service |
| GET | `/api/monitor/stats` | Full platform monitoring |
| POST | `/api/simulate/traffic` | Trigger traffic simulation |

---

## 👤 Author

**Abdallah Bazia**
- GitHub: [@abdallah-bazia](https://github.com/abdallah-bazia)
- Portfolio: [portfolio-jet-three-82.vercel.app](https://portfolio-jet-three-82.vercel.app)