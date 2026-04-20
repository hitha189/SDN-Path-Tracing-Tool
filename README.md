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

## Source Code

### topology.py
```python
#!/usr/bin/env python3
# topology.py — Custom Linear Topology for Path Tracing

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_topology():
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink
    )

    info("*** Adding Controller\n")
    net.addController('c0', controller=RemoteController,
                       ip='127.0.0.1', port=6633)

    info("*** Adding Hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')

    info("*** Adding Switches\n")
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    info("*** Adding Links\n")
    net.addLink(h1, s1)
    net.addLink(s1, s2)
    net.addLink(s2, s3)
    net.addLink(s3, h2)

    info("*** Starting Network\n")
    net.start()

    info("*** Network is ready!\n")
    info("*** Hosts: h1=10.0.0.1, h2=10.0.0.2\n")
    info("*** Opening Mininet CLI — type 'pingall' to test\n")

    CLI(net)

    info("*** Stopping Network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
```

### path_tracer.py
```python
#!/usr/bin/env python3
# path_tracer.py — Ryu Controller with Path Tracing Logic

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, icmp
from ryu.lib import mac
import time

class PathTracer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PathTracer, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.flow_paths = {}
        self.logger.info("=== PATH TRACER CONTROLLER STARTED ===")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(
            ofproto.OFPP_CONTROLLER,
            ofproto.OFPCML_NO_BUFFER
        )]
        self.install_flow(datapath, priority=0, match=match, actions=actions)
        self.logger.info(f"Switch s{datapath.id} connected to controller")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return

        dst_mac = eth.dst
        src_mac = eth.src
        switch_id = datapath.id

        self.mac_to_port.setdefault(switch_id, {})
        self.mac_to_port[switch_id][src_mac] = in_port

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            src_ip = ip_pkt.src
            dst_ip = ip_pkt.dst
            key = (src_ip, dst_ip)

            if key not in self.flow_paths:
                self.flow_paths[key] = []

            if switch_id not in self.flow_paths[key]:
                self.flow_paths[key].append(switch_id)
                self.logger.info(
                    f"  [PATH] Packet {src_ip} → {dst_ip} "
                    f"passed through Switch s{switch_id}"
                )

            if len(self.flow_paths[key]) >= 3:
                self.print_path(src_ip, dst_ip)

        if dst_mac in self.mac_to_port.get(switch_id, {}):
            out_port = self.mac_to_port[switch_id][dst_mac]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self.install_flow(datapath, priority=1, match=match, actions=actions)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        )
        datapath.send_msg(out)

    def install_flow(self, datapath, priority, match, actions,
                     idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
            ofproto.OFPIT_APPLY_ACTIONS, actions
        )]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout
        )
        datapath.send_msg(mod)

    def print_path(self, src_ip, dst_ip):
        key = (src_ip, dst_ip)
        if key in self.flow_paths:
            switches = self.flow_paths[key]
            switch_str = " → ".join([f"s{s}" for s in sorted(switches)])
            self.logger.info("=" * 50)
            self.logger.info(f"  TRACED PATH:")
            self.logger.info(f"  {src_ip} → {switch_str} → {dst_ip}")
            self.logger.info("=" * 50)
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
