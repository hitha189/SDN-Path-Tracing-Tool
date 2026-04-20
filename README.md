# SDN Path Tracing Tool
### Course: Computer Networks — UE24CS252B | PES University
### Name: Hithashree S
### SRN: PES1UG24CS189

---

## Problem Statement

Design and implement an **SDN-based Path Tracing Tool** using Mininet and the Ryu OpenFlow Controller that:
- Identifies and displays the path taken by packets across a network
- Tracks flow rules installed at each switch
- Identifies the forwarding path of packets in real-time
- Displays the complete route from source to destination
- Validates correctness using ping and iperf tests

---

## Introduction

In traditional networks, packet paths are determined by distributed routing protocols and are difficult to observe. In **Software Defined Networking (SDN)**, the control plane is centralized in a controller, making it possible to track and display exactly which switches a packet passes through.

This project uses:
- **Mininet** — to emulate a virtual network with hosts and switches
- **Ryu Controller** — to handle OpenFlow events and install flow rules
- **OpenFlow 1.3** — as the protocol between controller and switches

---

## Network Topology

```
h1 ---- s1 ---- s2 ---- s3 ---- h2
10.0.0.1                        10.0.0.2
```

| Component | Details |
|-----------|---------|
| Hosts | h1 (10.0.0.1), h2 (10.0.0.2) |
| Switches | s1, s2, s3 (OVS — Open vSwitch) |
| Controller | Ryu (Remote, port 6633) |
| Protocol | OpenFlow 1.3 |
| Link Type | TCLink (supports bandwidth/delay simulation) |

**Why this topology?**
A linear 3-switch topology is ideal for demonstrating path tracing because packets must pass through all 3 switches, making the traced path clearly visible and verifiable.

---

## Setup & Installation

### Prerequisites
- Ubuntu 20.04 / 22.04
- Python 3.10+
- VirtualBox / VMware

### Step 1 — Install Mininet
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install mininet -y
```

### Step 2 — Install Ryu Controller
```bash
pip install ryu
pip install eventlet==0.33.3
pip install dnspython==2.2.1
```

### Step 3 — Fix Ryu Compatibility (Python 3.10)
Edit the Ryu wsgi.py file:
```bash
nano ~/.pyenv/versions/3.10.13/lib/python3.10/site-packages/ryu/app/wsgi.py
```
Find this line:
```python
from eventlet.wsgi import ALREADY_HANDLED
```
Replace with:
```python
try:
    from eventlet.wsgi import ALREADY_HANDLED
except ImportError:
    ALREADY_HANDLED = object()
```

### Step 4 — Clone / Download Project Files
```bash
mkdir ~/sdn-path-tracer
cd ~/sdn-path-tracer
```
Place `topology.py` and `path_tracer.py` in this folder.

---

## Execution Steps

### Terminal 1 — Start Ryu Controller
```bash
cd ~/sdn-path-tracer
ryu-manager path_tracer.py
```
Wait until you see:
```
=== PATH TRACER CONTROLLER STARTED ===
```

### Terminal 2 — Start Mininet Topology
```bash
cd ~/sdn-path-tracer
sudo python3 topology.py
```
Wait until you see:
```
*** Network is ready!
mininet>
```

### In Mininet CLI — Run Tests
```bash
# Test 1: Ping connectivity
pingall

# Test 2: View flow tables
sh ovs-ofctl dump-flows s1
sh ovs-ofctl dump-flows s2
sh ovs-ofctl dump-flows s3

# Test 3: Bandwidth test
h1 iperf -s &
h2 iperf -c 10.0.0.1 -t 5
```

---

## Project Structure

```
sdn-path-tracer/
├── topology.py       # Custom Mininet linear topology
├── path_tracer.py    # Ryu controller with path tracing logic
└── README.md         # Project documentation
```

---

## SDN Logic & Flow Rule Design

### How Path Tracing Works

```
1. h1 sends a packet to h2
2. s1 receives it → no flow rule exists → sends packet_in to Ryu
3. Ryu logs: "packet passed through s1"
4. Ryu installs flow rule in s1 → forwards packet to s2
5. Same process repeats at s2 and s3
6. Ryu prints complete path: 10.0.0.1 → s1 → s2 → s3 → 10.0.0.2
```

### Flow Rule Design

| Priority | Match | Action | Purpose |
|----------|-------|--------|---------|
| 0 | Any packet | Send to Controller | Table-miss fallback |
| 1 | in_port + dst_mac | Output to port | Learned forwarding |

### packet_in Event Handling
- When a switch receives a packet with no matching flow rule, it sends a `packet_in` event to Ryu
- Ryu inspects the packet, logs which switch it passed through, installs a flow rule, and forwards the packet
- This continues at each switch until the full path is traced

---

## Test Scenario 1 — Ping Test (Connectivity Validation)

### Command
```bash
mininet> pingall
```

### Expected Output
```
*** Ping: testing ping reachability
h1 -> h2
h2 -> h1
*** Results: 0% dropped (2/2 received)
```

### Screenshot
<!-- Add your pingall screenshot here -->
![Ping Test](screenshots/pingall.png)

### What this proves
- All hosts can communicate through the switch path
- 0% packet loss confirms correct flow rule installation
- Path tracing was triggered successfully

---

## Test Scenario 2 — Flow Table Verification

### Command
```bash
mininet> sh ovs-ofctl dump-flows s1
mininet> sh ovs-ofctl dump-flows s2
mininet> sh ovs-ofctl dump-flows s3
```

### Screenshot
<!-- Add your flow table screenshot here -->
![Flow Tables](screenshots/flow_tables.png)

### Flow Table Analysis

Each switch contains 3 rules after `pingall`:

| Rule | Priority | Match | Action | Meaning |
|------|----------|-------|--------|---------|
| 1 | 1 | in_port=eth2, dst_mac=h1_mac | output:eth1 | Forward toward h1 |
| 2 | 1 | in_port=eth1, dst_mac=h2_mac | output:eth2 | Forward toward h2 |
| 3 | 0 | (any) | CONTROLLER:65535 | Table-miss fallback |

Key observations:
- `n_packets=3` confirms packets actually traversed each switch
- `n_bytes=238` confirms data was transferred
- Rules are symmetric — traffic flows in both directions

---

## Test Scenario 3 — iperf Bandwidth Test

### Command
```bash
mininet> h1 iperf -s &
mininet> h2 iperf -c 10.0.0.1 -t 5
```

### Expected Output
```
Client connecting to 10.0.0.1, TCP port 5001
[1] local 10.0.0.2 port 34162 connected with 10.0.0.1 port 5001
[ID] Interval        Transfer    Bandwidth
[1]  0.0000-5.0017 sec  27.4 GBytes  47.1 Gbits/sec
```

### Screenshot
<!-- Add your iperf screenshot here -->
![iperf Test](screenshots/iperf.png)

### Performance Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Duration | 5 seconds | Test ran successfully |
| Transfer | 27.4 GBytes | Large data transferred |
| Bandwidth | 47.1 Gbits/sec | High throughput (virtual network) |
| Packet Loss | 0% | Perfect delivery |

The high bandwidth is expected in a virtual network environment (no physical hardware limits).

---

## Path Tracing Output

### Screenshot
<!-- Add your Ryu terminal path tracing screenshot here -->
![Path Tracing](screenshots/path_tracing.png)

### Output Explanation

```
Switch s1 connected to controller   ← s1 registered with Ryu
Switch s2 connected to controller   ← s2 registered with Ryu  
Switch s3 connected to controller   ← s3 registered with Ryu

[PATH] Packet 10.0.0.1 → 10.0.0.2 passed through Switch s1  ← packet_in at s1
[PATH] Packet 10.0.0.1 → 10.0.0.2 passed through Switch s2  ← packet_in at s2
[PATH] Packet 10.0.0.1 → 10.0.0.2 passed through Switch s3  ← packet_in at s3

==================================================
  TRACED PATH:
  10.0.0.1 → s1 → s2 → s3 → 10.0.0.2          ← Full path displayed!
==================================================
```

---

## Performance Observation & Analysis

| Metric | Tool Used | Result |
|--------|-----------|--------|
| Latency | ping (pingall) | 0% packet loss |
| Throughput | iperf | 47.1 Gbits/sec |
| Flow table changes | ovs-ofctl dump-flows | 3 rules per switch |
| Packet counts | n_packets in flow table | 3 packets per switch |
| Path tracing | Ryu logs | h1→s1→s2→s3→h2 |

---

## SDN Concepts Demonstrated

| Concept | How it's shown in this project |
|---------|-------------------------------|
| Controller-Switch interaction | Ryu receives packet_in from all 3 switches |
| Flow rule installation | Priority-1 rules installed after MAC learning |
| Table-miss rule | Priority-0 rule sends unknown packets to controller |
| MAC learning | mac_to_port table built dynamically |
| Path tracing | Switch IDs logged per flow, full path printed |
| OpenFlow 1.3 | OFP_VERSION set in controller |

---

## Cleanup

To stop and clean up after the experiment:
```bash
# In Mininet CLI
exit

# Clean residual state
sudo mn -c
```

---

## References

1. Mininet Overview — https://mininet.org/overview/
2. Mininet Walkthrough — https://mininet.org/walkthrough/
3. Ryu Controller Documentation — https://ryu.readthedocs.io/en/latest/
4. OpenFlow 1.3 Specification — https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf
5. Mininet GitHub — https://github.com/mininet/mininet
6. Open vSwitch Documentation — https://docs.openvswitch.org/
