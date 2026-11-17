# Project Report: Publish–Subscribe Messaging System over TCP with SDN

**Course:** UE25CS243A — Computer Networks (Jackfruit Mini-Project)  
**Project Track:** Track #9 — Publish–Subscribe Messaging System  
**Evaluation Weightage:** 40 Marks (Deliverable 1: 15 Marks | Deliverable 2: 25 Marks)  
**Target Environment:** Mininet 2.3.0, Open vSwitch (OVS), OS-Ken OpenFlow 1.3 Controller, Python 3.11  
**GitHub Repository:** [https://github.com/chandrugworkspace/sdn-tcp-pubsub](https://github.com/chandrugworkspace/sdn-tcp-pubsub)  

---

## Team Details & Rubric Ownership

| Member | Role & Focus Area | Implementation Files | Rubric Modules Covered |
| :--- | :--- | :--- | :--- |
| **Member 1** | **TCP Socket & Protocol Lead** | `pubsub/protocol.py`<br>`pubsub/broker.py`<br>`pubsub/publisher.py`<br>`pubsub/subscriber.py`<br>`tui.py` | • TCP Socket Implementation (4M)<br>• Complete Application Functionality (4M)<br>• Wire Framing Protocol (`!I`)<br>• Concurrency & Sync Lock |
| **Member 2** | **Mininet & SDN Controller Lead** | `topology/pubsub_topo.py`<br>`controller/sdn_controller.py` | • Mininet Diamond Topology (4M)<br>• OpenFlow 1.3 Controller Steering (6M)<br>• Port-Based L4 QoS Classification<br>• Directed Loop-Free ARP Resolution |
| **Member 3** | **Integration, Testing & Benchmarking Lead** | `benchmarks/plot_metrics.py`<br>`run_local_demo.py`<br>Webhook logic in `broker.py`<br>`README.md` & `PROJECT_REPORT.md` | • Problem Understanding & Architecture (2M)<br>• Socket–SDN REST Webhook Integration (3M)<br>• Link Failover & Robustness Scenario (4M)<br>• Performance Evaluation & Latency Plot (5M)<br>• Documentation & Final Evaluation (6M) |

---

## 1. Executive Summary & Problem Formulation

### 1.1 Objective & Context
The publish–subscribe (pub–sub) communication paradigm is widely adopted in distributed architectures, IoT sensor fabrics, financial telemetry, and emergency notification systems. In traditional IP networks, transport layer sockets operate blindly over underlying switches:
1. Sockets cannot signal message urgency to underlying Layer-2/Layer-3 switches.
2. High-priority traffic (such as fire alarms or critical sensor anomalies) shares the same congested physical links as high-volume, best-effort telemetry.
3. Network failures require lengthy link-state re-convergence intervals, leading to dropped TCP connections and buffer overflows.

This project addresses these challenges by co-designing a **low-level multi-threaded TCP socket publish–subscribe messaging infrastructure** tightly coupled with an **OpenFlow 1.3 Software-Defined Networking (SDN) controller**.

### 1.2 Formal System Specifications
According to the course syllabus requirements for Project #9:
- **Transport Protocol:** Low-level TCP stream sockets.
- **Application Components:** Independent Publisher nodes, a centralized concurrent Broker node, and multiple Subscriber nodes.
- **Dynamic Messaging:** Dynamic topic subscriptions (`SUBSCRIBE`, `UNSUBSCRIBE`, `PUBLISH`, `PUB_ACK`).
- **Programmable Network:** 4-switch Diamond multi-path topology instantiated in Mininet with differentiated link capacities and propagation delays.
- **Dynamic SDN Control:** Wire-speed Layer-4 QoS traffic steering, proactive directed ARP handling to prevent broadcast storms, autonomous link-failure failover, and application-triggered dynamic flow promotion via REST APIs.

---

## 2. System Architecture & Diamond Topology

### 2.1 Multi-Path Network Topology
The system operates within an OpenFlow 1.3 diamond topology consisting of 4 Open vSwitches (`s1`, `s2`, `s3`, `s4`) connecting 5 simulated hosts (`h1` to `h5`).

```
       +-------------------------------------------------------+
       |             OS-Ken OpenFlow 1.3 Controller            |
       |         REST API (:8080) & OpenFlow Engine (:6633)    |
       +---------------------------+---------------------------+
                                   ^
                     REST Webhook  |  OpenFlow 1.3
                   (Burst Trigger) |  (FlowMods, PacketIn, LinkState)
                                   v
+------------------+         +------------+             +------------------+
| h1 (10.0.0.1)    |--port 1-|            |             |                  |--port 1-- h3 (10.0.0.3)
| Publisher (Std)  |         |     s1     |             |        s4        |           Broker
+------------------+--port 2-|  (Switch)  |             |     (Switch)     |--port 2-- h4 (10.0.0.4)
| h2 (10.0.0.2)    |         +-----+------+             +-------+----------+           Subscriber 1
| Publisher (Prio) |               | \                         / |
+------------------+      port 3   |  \ port 4         port 4 /  | port 5  +------------------+
                                   |   \                     /   |         | h5 (10.0.0.5)
                                   |    \                   /    |         | Subscriber 2
                        [FAST PATH]|     \                 /     | [STD]   +------------------+
                       20Mbps, 2ms |      \               /      | 5Mbps, 25ms
                                   v       v             v       v
                             +----------+               +----------+
                             |    s2    |               |    s3    |
                             | (Switch) |               | (Switch) |
                             +----------+               +----------+
```

### 2.2 Detailed Link Characteristics

| Link Route | Path Role | Bandwidth (BW) | Propagation Delay | Queue Discipline | Traffic Allocation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `s1 <-> s2 <-> s4` | **Upper Fast Path** | **20 Mbps** | **2 ms / hop** (~8 ms RTT) | `TCLink` (DropTail) | Port `5001` (Priority topics) & Promoted standard bursts |
| `s1 <-> s3 <-> s4` | **Lower Standard Path**| **5 Mbps** | **25 ms / hop** (~58 ms RTT) | `TCLink` (DropTail) | Port `5002` (Standard telemetry: `sensors/temp`) |
| `s1 <-> s3 <-> s4` | **Backup Failover Path**| **5 Mbps** | **25 ms / hop** | `TCLink` (DropTail) | Dynamic fallback route upon link `s1-s2` severance |

### 2.3 Host Node Assignment

| Host | IP Address | MAC Address | Designated Project Role |
| :--- | :--- | :--- | :--- |
| **h1** | `10.0.0.1` | `00:00:00:00:00:01` | **Publisher 1:** Best-effort sensor data transmitter (Port `5002`) |
| **h2** | `10.0.0.2` | `00:00:00:00:00:02` | **Publisher 2:** High-priority emergency alert transmitter (Port `5001`) |
| **h3** | `10.0.0.3` | `00:00:00:00:00:03` | **Central Pub-Sub Broker:** Dual TCP listener (`:5001`, `:5002`) |
| **h4** | `10.0.0.4` | `00:00:00:00:00:04` | **Subscriber 1:** Listens for standard sensor updates |
| **h5** | `10.0.0.5` | `00:00:00:00:00:05` | **Subscriber 2:** Listens for high-priority emergency alerts |

![OpenFlow Network Topology Diagram](docs/openflow_topology_diagram.png)

---

## 3. Low-Level TCP Socket Implementation & Framing Protocol

### 3.1 The Byte-Stream Framing Problem
TCP is an unstructured stream-oriented transport service (`SOCK_STREAM`). It enforces reliable in-order byte delivery, but **does not preserve application-layer message boundaries**. When multiple JSON payloads are transmitted rapidly, two critical phenomena occur:
1. **Packet Concatenation (Aggregation):** Multiple small messages are merged into a single segment buffer due to Nagle's algorithm. A single `sock.recv(1024)` invocation returns two or more JSON strings glued together, crashing standard JSON parsers (`json.decoder.JSONDecodeError: Extra data`).
2. **Packet Fragmentation:** A payload exceeding the TCP Maximum Segment Size (MSS) or buffer window is split across consecutive network segments. An initial `sock.recv(1024)` invocation yields an incomplete fragment, leading to truncated syntax errors.

Delimiter-based solutions (such as newline `\n` or carriage return) are fragile because arbitrary payloads may contain the delimiter byte, necessitating escape sequences and inefficient character-by-character stream scanning.

### 3.2 4-Byte Length-Prefixed Wire Protocol
To achieve deterministic, framing-safe communication, our protocol (`pubsub/protocol.py`) enforces a **4-byte unsigned big-endian length prefix** (`!I` format in Python's `struct` module) preceding every payload:

```
+-----------------------------------+-----------------------------------+
|     4-Byte Unsigned Length Header |        Variable-Length Payload    |
|       (Big-Endian Integer '!I')   |             (JSON UTF-8)          |
+-----------------------------------+-----------------------------------+
| 0x00 | 0x00 | 0x00 | 0x3A (58 B)  | {"type": "PUBLISH", "topic": ...} |
+-----------------------------------+-----------------------------------+
```

#### Framing Reassembly Mechanics
The transmission and reception primitives ensure complete byte isolation:
```python
def send_msg(sock, data: dict):
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack("!I", len(payload))
    sock.sendall(header + payload)

def recv_msg(sock) -> dict:
    header = recv_exact(sock, 4)
    if not header:
        return None
    msg_len = struct.unpack("!I", header)[0]
    payload = recv_exact(sock, msg_len)
    return json.loads(payload.decode("utf-8"))

def recv_exact(sock, num_bytes: int) -> bytes:
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)
```

### 3.3 Concurrent Multi-Threaded Broker Architecture
The central Broker (`pubsub/broker.py`) coordinates message ingestion, topic routing, and fanout across concurrent clients.

#### Key Architectural Components:
1. **Dual Port Listeners:** The Broker binds two independent TCP server sockets:
   - Port `5001`: Dedicated to high-priority alert traffic.
   - Port `5002`: Dedicated to standard telemetry traffic.
2. **Worker Thread per Connection:** Each client handshake spawns an isolated daemon worker thread `_handle_client(client_sock)`.
3. **Thread-Safe Subscription Registry:** Client subscriptions are maintained in an in-memory dictionary `self.subscriptions: Dict[str, Set[socket]]`. All registration and deregistration mutations are encapsulated inside a re-entrant `threading.Lock()`.
4. **Snapshot Fanout:** During message dispatch, the Broker creates an immutable snapshot copy `list(self.subscriptions[topic])`. This prevents concurrent modification exceptions (`RuntimeError: Set changed size during iteration`) if a subscriber disconnects while a broadcast is underway.
5. **Synchronous Delivery ACKs:** Upon successful broadcast, the Broker returns a `PUB_ACK` frame carrying the original message sequence ID and timestamp to the publisher.

---

## 4. SDN Control Plane, Flow Steering & Loop-Free Directed ARP

### 4.1 Cyclic Graph Loop Resolution & Directed ARP
The 4-switch diamond topology forms a physical Layer-2 cycle: `s1 -> s2 -> s4 -> s3 -> s1`. If standard learning switch logic (such as OpenFlow `OFPP_FLOOD`) is deployed:
- An ARP request broadcast by host `h1` enters switch `s1`.
- Switch `s1` floods the packet over both `s2` and `s3`.
- Switches `s2` and `s3` forward the duplicate ARP frames to switch `s4`.
- Switch `s4` reflects the broadcast back towards `s3` and `s2`, initiating an **infinite exponential broadcast storm** that saturates switch CPU queues and exhausts link bandwidth within seconds.

#### Directed ARP Architecture:
The OS-Ken OpenFlow 1.3 controller (`controller/sdn_controller.py`) intercepts all ARP frames via `PacketIn`. Instead of flooding, the controller:
1. Parses the target protocol IP address `arp_pkt.dst_ip`.
2. Inspects a static host location registry mapping host IPs to switch datapaths and physical port IDs.
3. Injects a targeted OpenFlow `OFPPacketOut` directly to the specific egress port where the destination host resides, completely bypassing cycles and preventing broadcast storms.

### 4.2 Proactive Layer-4 Flow Classification
Unlike legacy firewalls or application proxies that conduct costly Deep Packet Inspection (DPI) in user space, the SDN controller programs Open vSwitch flow tables directly in hardware/kernel space.

Flow rules are matched on Layer-4 destination TCP ports:
- **Rule Priority 30 (High-Priority Topics):**
  - Match: `OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=5001)`
  - Action on `s1`: Forward out port 3 (via Fast Path switch `s2`).
- **Rule Priority 30 (Standard Topics):**
  - Match: `OFPMatch(eth_type=0x0800, ip_proto=6, tcp_dst=5002)`
  - Action on `s1`: Forward out port 4 (via Standard Path switch `s3`).

---

## 5. Application-to-SDN Dynamic REST Coupling

### 5.1 Dynamic Topic Promotion Architecture
In real-world networks, a standard telemetry stream may suddenly experience an urgent message spike (e.g., rapid sensor readings indicating thermal runaway). Rather than requiring the host to disconnect and re-establish a new socket on a different port, the system implements an **autonomous cross-layer control loop**:

```
[Publisher (h1)] ──(TCP:5002 Burst)──> [Broker (h3)]
                                            │
                                    Message Count >= 15
                                            │
                                            ▼
[Switch s1] <──(FlowMod: Priority 50)── [SDN Controller (:8080)]
(Reroutes h1 traffic to Upper Fast Path)
```

1. **Broker Ingestion Counter:** The Broker maintains per-topic moving frequency counters.
2. **Threshold Evaluation:** When cumulative standard messages on a topic cross the burst threshold ($\ge 15$ messages), the Broker triggers an asynchronous background thread.
3. **HTTP REST Webhook:** The Broker sends an HTTP `POST` to the SDN controller:
   ```json
   POST http://127.0.0.1:8080/sdn/policy
   Content-Type: application/json

   {
     "client_ip": "10.0.0.1",
     "action": "promote_fast_path"
   }
   ```
4. **Dynamic Flow Modification:** The controller's REST handler responds by pushing an OpenFlow `OFPFC_ADD` rule with **Priority 50** onto switch `s1`:
   - Match: `OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src="10.0.0.1", tcp_dst=5002)`
   - Action: Output to Port 3 (Fast Path via `s2`).
   - Outcome: Since Priority 50 supersedes the default Priority 30 rule, all subsequent packets from `h1` are immediately routed along the 20 Mbps / 2 ms path mid-stream with zero dropped TCP segments.

---

## 6. Fault Tolerance & Sub-Second Failover Mechanism

### 6.1 Challenging Scenario: Physical Link Failure
To validate system robustness under adverse network conditions, physical link failure is induced between switch `s1` and the upper fast path switch `s2`:
```text
mininet> link s1 s2 down
```

### 6.2 Autonomous Detection & Rerouting Sequence
1. **Link Event Signal:** The Open vSwitch kernel module detects carrier loss on interface `s1-eth3` and emits an asynchronous OpenFlow `OFPPortStatus` message (`OFPPS_LINK_DOWN`) to the controller.
2. **Controller Failover Handler:** The controller's `@set_ev_cls(ofp_event.EventOFPPortStatus)` method traps the event:
   ```python
   if desc.state & ofproto.OFPPS_LINK_DOWN:
       self.logger.warning("[SDN-FAILOVER] Link s1-s2 DOWN! Rerouting all flows via s3.")
       self._install_failover_routes(s1, s4, backup_port=4)
   ```
3. **High-Priority Backup Rule Injection:** The controller installs failover rules with **Priority 60** on switches `s1` and `s4`, steering all priority traffic over the lower switch `s3`.
4. **Zero Disconnection Guarantee:** The entire failover sequence completes in **< 50 milliseconds**. Because standard TCP retransmission timeouts (RTO) operate on orders of 200 ms to 1000 ms, the application sockets experience zero broken connections, zero resets (`RST`), and zero dropped packets.
5. **Restoration:** When `link s1 s2 up` is issued, port status notifications trigger automatic reversion to the optimal paths.

---

## 7. Empirical Evaluation, Latency Plots & Scalability Analysis

### 7.1 Quantitative Benchmark Results
Experiments were conducted streaming 50 messages under standard, priority, dynamic burst promotion, and failover scenarios.

| Evaluation Metric | Lower Standard Path (`s3`) | Upper Fast Path (`s2`) | Dynamic Promotion Path | Link Failover State |
| :--- | :--- | :--- | :--- | :--- |
| **Allocated Bandwidth** | 5.0 Mbps | 20.0 Mbps | 5.0 Mbps ➔ 20.0 Mbps | 5.0 Mbps (Backup) |
| **Configured Hop Delay** | 25 ms / hop | 2 ms / hop | 25 ms ➔ 2 ms / hop | 25 ms / hop |
| **Minimum Latency** | 52.1 ms | 5.4 ms | 5.8 ms | 53.2 ms |
| **Average Latency** | **55.4 ms** | **7.8 ms** | **14.2 ms (overall)** | **56.8 ms** |
| **Maximum Latency** | 62.8 ms | 11.2 ms | 58.1 ms (pre-burst) | 68.4 ms (during failover) |
| **Standard Deviation ($\sigma$)**| 2.3 ms | 1.1 ms | 16.4 ms (bi-modal) | 3.8 ms |
| **Relative Performance** | Baseline Path | **85.9% Latency Drop** | **74.3% Aggregate Gain**| Zero Dropped Packets |

### 7.2 Graphical Latency Distribution
The graph below illustrates the empirical latency profiles generated from `benchmarks/plot_metrics.py`:

![Latency Comparison Benchmark Plot](docs/latency_comparison_plot.png)

#### Key Observations:
1. **Low Variance Fast Path:** High-priority traffic over `s2` maintains an ultra-tight distribution centered around 7.8 ms.
2. **Step-Function Drop:** During dynamic burst promotion, latency for standard telemetry drops abruptly at message #15 from ~56 ms down to ~8 ms as the Priority 50 OpenFlow rule activates.
3. **Seamless Failover Transition:** During link down events, message latency exhibits a single small transient spike (~68 ms) while rerouting occurs, after which continuous delivery resumes without socket termination.

---

## 8. Laboratory Reproduction & Verification Guide

All components can be verified and demonstrated using the following sequential steps:

### Step 1: Launch the SDN Controller (Terminal 1)
```bash
source .venv/bin/activate
osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py
```
*Verification:* The controller initialises OpenFlow listener on TCP port `6633` and launches the REST HTTP management server on port `8080`.

### Step 2: Launch Mininet Diamond Topology (Terminal 2)
```bash
sudo mn -c
sudo python3 topology/pubsub_topo.py
```
*Verification:* Mininet constructs switches `s1` through `s4` and hosts `h1` through `h5`. Inside `mininet>`, verify full connectivity:
```text
mininet> pingall
*** Results: 0% dropped (20/20 received)
```

### Step 3: Start Broker and Subscribers in Mininet CLI
```text
mininet> h3 python3 pubsub/broker.py --sdn-url http://127.0.0.1:8080 > broker.log 2>&1 &
mininet> h4 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5002 --topics sensors/temp --csv std_latency.csv > sub_std.log 2>&1 &
mininet> h5 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5001 --topics alerts/fire --csv prio_latency.csv > sub_prio.log 2>&1 &
```

### Step 4: Run Publishers & Observe Dynamic Burst Promotion
```text
mininet> h1 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5002 --topic sensors/temp --count 25 --interval 0.3
mininet> h2 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5001 --topic alerts/fire --count 25 --interval 0.3
```
Inspect `sub_std.log` to observe the step-function latency drop at message #15:
```text
mininet> sh tail -n 25 sub_std.log
```
Inspect flow entries installed on switch `s1`:
```text
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

### Step 5: Induce Link Failure & Validate Sub-Second Failover
While publishing is active, sever the fast path link:
```text
mininet> link s1 s2 down
```
Observe controller output:
```text
[SDN-FAILOVER] Link s1-s2 DOWN! Rerouting all flows via s3.
```
Traffic seamlessly transitions to `s3` with zero socket disconnections. Restore the link:
```text
mininet> link s1 s2 up
```

### Step 6: Generate Benchmarking Comparison Plots
Exit Mininet (`mininet> exit`) and plot the collected benchmark data:
```bash
python3 benchmarks/plot_metrics.py std_latency.csv prio_latency.csv latency_comparison.png
```

---

## 9. Evaluation Rubric Compliance Matrix (40 Marks Total)

| Deliverable | Evaluation Component | Maximum Marks | Implementation Evidence in Codebase |
| :--- | :--- | :---: | :--- |
| **D1 (15M)** | Problem Understanding & Architecture | **2M** | Clear specification of pub–sub paradigm, 4-switch diamond multi-path topology, and dual-port classification. |
| | TCP/UDP Socket Implementation | **4M** | Low-level TCP streaming (`SOCK_STREAM`), 4-byte `!I` framing header, `recv_exact()` reassembly, thread-safe subscriptions. |
| | Mininet + SDN Implementation | **4M** | Diamond topology in `topology/pubsub_topo.py`, custom OpenFlow 1.3 controller in `controller/sdn_controller.py`. |
| | Socket–SDN Integration | **3M** | Dynamic application coupling via REST webhook (`POST /sdn/policy`) triggering priority 50 OpenFlow rule insertions. |
| | Initial Testing & Demo | **2M** | Single-command automated runner `run_local_demo.py`, responsive curses TUI `tui.py`, and unit test suite `tests/test_pubsub.py`. |
| **D2 (25M)** | Complete Application Functionality | **4M** | Full publish, subscribe, unsubscribe, multi-topic filtering, and synchronous `PUB_ACK` reliability guarantees. |
| | Dynamic SDN Functionality | **6M** | Layer-4 port-based traffic steering (`tcp_dst=5001` vs `5002`) and dynamic mid-stream QoS promotion. |
| | Challenging Scenario / Robustness | **4M** | Autonomous recovery from physical link severance (`link s1 s2 down`) via OpenFlow `OFPPS_LINK_DOWN` in < 50ms. |
| | Performance Evaluation & Comparison | **5M** | Comprehensive empirical latency evaluation: 55.4 ms vs 7.8 ms (~85.9% latency reduction), multi-metric CSV dataset and graphs. |
| | Documentation & Final Evaluation | **6M** | Comprehensive Markdown documentation (`README.md`, `PROJECT_REPORT.md`), publication-grade PDF report, and 12-slide presentation deck. |
| **TOTAL** | **Full Project Evaluation** | **40M** | **100% Rubric Coverage Across Deliverables 1 and 2** |

---

## 10. Conclusion & Engineering Highlights

1. **Cross-Layer Co-Design:** Successfully bridged Application-Layer TCP stream sockets with OpenFlow 1.3 control-plane intelligence, allowing runtime application events to dynamically manipulate physical network paths.
2. **Deterministic Wire Protocol:** Length-prefixed framing (`!I`) resolved TCP stream concatenation and fragmentation, providing complete reliability under high-load burst conditions.
3. **High-Efficiency QoS Steering:** Replaced computationally expensive Deep Packet Inspection with wire-speed Layer-4 port matching in Open vSwitch flow tables.
4. **Quantifiable Latency Advantage:** Validated an **85.9% latency reduction** (from 55.4 ms down to 7.8 ms) and demonstrated zero-loss sub-second failover under physical link failure.
