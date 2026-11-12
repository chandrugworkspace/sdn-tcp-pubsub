# Team Member Execution & Presentation Guide (3 Members)

**Course:** Computer Networks (UE25CS243A) — SDN-Socket Programming Mini Project  
**Project Track:** Project #9 — Publish–Subscribe Messaging System over TCP with SDN  
**Total Marks:** 40 Marks (Deliverable 1: 15M | Deliverable 2: 25M)  
**Team Size:** 3 Members  

This handbook provides step-by-step instructions for each of the 3 teammates: environment setup by OS, role division mapped to project marks, a 7-minute teacher presentation script, live demo execution steps, and an individual viva Q&A defense cheat sheet.

---

## 1. Quick Repository Clone for All Teammates

Every teammate should first clone the shared repository:

```bash
git clone https://github.com/chandrugworkspace/sdn-tcp-pubsub.git
cd sdn-tcp-pubsub
```

---

## 2. Environment Setup by Operating System

### A. Teammate on Linux / CachyOS / Arch Linux (Native)
Mininet and Open vSwitch run natively with zero virtualization overhead.

```bash
# 1. Install required packages
sudo pacman -Syu mininet openvswitch iproute2 iperf3 python-pip uv git

# 2. Start and enable Open vSwitch
sudo systemctl enable --now ovs-vswitchd.service ovsdb-server.service

# 3. Create virtual environment and install dependencies
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

### B. Teammate on Windows 10/11 (Ubuntu 22.04 LTS VM)
> **Note for Windows users:** Standard WSL2 kernel does not include Open vSwitch and `TCLink` traffic shaping kernel modules. Run an **Ubuntu 22.04 LTS VM** inside **VirtualBox** or **VMware Workstation Player** (2 CPU cores, 4 GB RAM, NAT/Bridged network).

Inside the Ubuntu VM terminal:
```bash
# 1. Update and install networking packages
sudo apt update && sudo apt upgrade -y
sudo apt install mininet openvswitch-switch iproute2 iperf3 python3-pip python3-venv git -y

# 2. Verify Open vSwitch is running
sudo systemctl status openvswitch-switch

# 3. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### C. Teammate on macOS (Apple Silicon / Intel via UTM or VMware)
Run an **Ubuntu 22.04 LTS VM** using **UTM** (free) or **VMware Fusion Player**. Then inside the Ubuntu terminal, run the same commands as Section B above.

---

### Quick Verification for All Environments
```bash
# 1. Test Mininet & Open vSwitch
sudo mn --switch ovsbr --test pingall
sudo mn -c

# 2. Run automated test suite (verifies socket logic without root)
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## 3. Team Member Role Division & Evaluation Mapping

To secure full marks (40/40), the presentation is structured so each member demonstrates deep ownership of their engineering module:

| Member | Title / Role | Files Owned | Marks Mapped | Key Technical Concepts |
| :--- | :--- | :--- | :--- | :--- |
| **Member 1** | **TCP Socket & Pub-Sub Protocol Lead** | `pubsub/protocol.py`<br>`pubsub/broker.py`<br>`pubsub/subscriber.py`<br>`pubsub/publisher.py`<br>`tui.py` | **Deliverable 1**<br>(15 Marks) | Low-level TCP (`AF_INET`, `SOCK_STREAM`), 4-byte big-endian framing (`!I`), topic registry, delivery ACKs (`PUB_ACK`, `SUB_ACK`). |
| **Member 2** | **SDN Controller & Topology Lead** | `topology/pubsub_topo.py`<br>`controller/sdn_controller.py` | **Deliverable 2**<br>(SDN Core) | 4-switch Diamond topology, OpenFlow 1.3 controller, port-based traffic steering (5001 = Fast Path, 5002 = Standard Path), loop-free directed ARP. |
| **Member 3** | **Integration, Failover & Benchmarking Lead** | Dynamic Webhook in `broker.py`<br>`controller/sdn_controller.py`<br>`benchmarks/plot_metrics.py`<br>`local_latency_plot.png` | **Deliverable 2**<br>(Integration & QoS) | Application-to-SDN dynamic flow promotion (>15 msgs burst), sub-second link failure & fast failover (`link s1 s2 down`), latency graphs (55ms vs 6ms). |

---

## 4. The 7-Minute Teacher Presentation Flow

```
[0:00 - 2:00] Member 1: Problem Statement, TCP Socket Framing & Live TUI Demo
         │
[2:00 - 4:30] Member 2: Mininet Diamond Topology, OpenFlow 1.3 & Directed ARP
         │
[4:30 - 7:00] Member 3: Dynamic QoS Webhook, Link Failover & Benchmark Latency Plot
```

### Stage 1: Member 1 — TCP Socket & Pub-Sub Protocol (2 Minutes)

#### Speech Script:
> *"Good morning/afternoon, Sir/Ma'am. Our project is **Project #9: Publish–Subscribe Messaging System over TCP with SDN** (Course UE25CS243A).*  
> *I was responsible for Deliverable 1: designing the core TCP transport layer and the pub-sub wire protocol.*  
> *Because standard TCP is a continuous byte stream without application-level packet boundaries, consecutive packets can concatenate or fragment. To prevent this, I implemented a **4-byte big-endian length-prefixed framing header** using `struct.pack('!I')` in `pubsub/protocol.py`.*  
> *Our Central Broker handles concurrent client threads and listens on two separate TCP ports: **5001 (Priority)** and **5002 (Standard)**. Every publish event requires end-to-end confirmation with a `PUB_ACK` packet containing sequence numbers and delivery counts."*

#### Live Demonstration Action:
1. Open the terminal and launch the In-Terminal TUI (configured with responsive form factor & solid black background):
   ```bash
   source .venv/bin/activate
   python3 tui.py
   ```
2. **Interactive Manual Demo Flow:**
   - Press **`B`** $\rightarrow$ Show the Broker initializing listeners on ports 5001 (Priority) and 5002 (Standard) in Pane 1.
   - Press **`S`** $\rightarrow$ Show Subscriber connecting to topic `sensors/temp` in Pane 2.
   - Press **`P`** $\rightarrow$ Show Publisher sending a packet in Pane 3, Broker routing it, Subscriber receiving it, and Publisher displaying `Broker ACK: OK` with latency.
   - Press **`2`** $\rightarrow$ Show Priority publishing (5 packets on `alerts/fire` port 5001).
   - Press **`X`** $\rightarrow$ Burst 16 packets on `sensors/temp` to trigger the dynamic SDN Promotion webhook ($\ge 15$ threshold).
3. **One-Touch Automated Demo / Viva Backup:**
   - Press **`A`** $\rightarrow$ Runs the entire End-to-End sequence automatically (Broker -> Sub -> Std -> Prio -> Burst).
   - Press **`U`** $\rightarrow$ Runs Python unit tests (`tests/test_pubsub.py`) with live passing logs inside the console.
   - Press **`L`** $\rightarrow$ Toggles layout between Stacked (Full-Width Rows) and Split (2-Column Grid).

---

### Stage 2: Member 2 — Mininet Diamond Topology & SDN Steering (2.5 Minutes)

#### Speech Script:
> *"Once the socket layer was verified, I developed the Software-Defined Networking architecture in Deliverable 2.*  
> *We implemented a 4-switch diamond topology (`topology/pubsub_topo.py`):*  
> *- **Upper Fast Path (`s1 -> s2 -> s4`):** 20 Mbps bandwidth, 2ms delay per hop.*  
> *- **Lower Standard Path (`s1 -> s3 -> s4`):** 5 Mbps bandwidth, 25ms delay per hop.*  
> *In diamond topologies, standard Layer 2 broadcasting causes ARP broadcast storms and packet looping. I solved this in `controller/sdn_controller.py` by implementing **directed ARP handling**—the controller intercepts ARP requests (`PacketIn`), inspects its internal IP-to-port table, and forwards ARP requests as point-to-point unicast packets, ensuring a loop-free network.*  
> *The controller installs proactive OpenFlow 1.3 rules matching on destination TCP port: port 5001 traffic is steered to `s2` (Fast Path), while port 5002 traffic is steered to `s3` (Standard Path)."*

#### Live Demonstration Action (inside Mininet):
1. Show the OS-Ken Controller running:
   ```bash
   osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py
   ```
2. Start Mininet:
   ```bash
   sudo mn -c
   sudo python3 topology/pubsub_topo.py
   ```
3. Test reachability:
   ```text
   mininet> pingall
   ```
   *(Point to screen: 0% dropped packets).*
4. Dump flow tables on switch `s1`:
   ```text
   mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
   ```
   *(Point to screen: `tcp_dst=5001` forwards to output port 3 (`s2`), `tcp_dst=5002` forwards to output port 4 (`s3`)).*

---

### Stage 3: Member 3 — Dynamic QoS, Failover & Benchmarks (2.5 Minutes)

#### Speech Script:
> *"I integrated the socket layer with the SDN control plane to achieve dynamic QoS adaptation, fault tolerance, and performance benchmarking.*  
> *In real networks, IoT sensors initially sending low-priority telemetry may encounter an emergency requiring low-latency delivery. In `pubsub/broker.py`, I implemented a **burst threshold detector**.*  
> *When message volume on a standard topic exceeds 15 packets, the Broker fires an HTTP REST webhook `POST /sdn/policy` to the controller. The controller immediately pushes higher-priority OpenFlow rules (`priority=50`) that promote that flow from `s3` to `s2` in real-time without terminating the TCP socket.*  
> *Furthermore, if the primary fast link `s1-s2` experiences physical failure, the controller detects `OFPPS_LINK_DOWN` and instantly fails over all traffic to `s3` with **zero dropped connections**."*

#### Live Demonstration Action:
1. In `tui.py`, press **`X`** (Burst 16 messages):
   - Show Broker alert: `🚀 [BURST-DETECTED] Topic reached 15 msgs! Triggering SDN Fast Path (Port 5001)...`
2. Demonstrate **Link Failure & Fast Failover** (inside Mininet):
   ```text
   mininet> link s1 s2 down
   ```
   - Show controller detecting link state change and rerouting to `s3`.
   - Restore link:
   ```text
   mininet> link s1 s2 up
   ```
3. Show **Benchmark Latency Graph**:
   - Open `local_latency_plot.png` or `latency_comparison.png`:
   - Point out the metrics:
     - **Standard Path:** Average Latency $\approx 55 - 60 \text{ ms}$ (5 Mbps link + 25ms delay).
     - **Priority Path:** Average Latency $\approx 6 - 8 \text{ ms}$ (20 Mbps link + 2ms delay).
     - **Result:** **~88% latency reduction** achieved through SDN path steering.

---

## 5. Teacher Viva & Q&A Defense Cheat Sheet

Be prepared for the teacher to question each teammate individually:

### Questions for Member 1 (Socket Programming & Protocol)

* **Q: Why did you use TCP instead of UDP for this Pub-Sub system?**  
  *Answer:* Pub-Sub event systems (such as financial transactions or safety alarms) require guaranteed, ordered delivery and delivery acknowledgments (`PUB_ACK`). UDP is connectionless and loss-prone, whereas TCP provides reliability, flow control, and sequence tracking.

* **Q: Why did you need custom framing (`!I`) if TCP already guarantees delivery?**  
  *Answer:* TCP is a byte-stream protocol, not a message-oriented protocol. It does not preserve application message boundaries. Consecutive packets can concatenate (framing error) or split across buffer chunks (fragmentation). The 4-byte big-endian header explicitly informs the receiver exactly how many bytes belong to the current message payload.

* **Q: How does the Broker handle concurrent clients without blocking?**  
  *Answer:* The broker spawns a dedicated worker thread per connected client socket (`threading.Thread`) and protects the shared subscription dictionary using a `threading.Lock()` to prevent race conditions during concurrent publishes and unsubscribes.

---

### Questions for Member 2 (SDN & OpenFlow)

* **Q: Why does a diamond topology cause broadcast storms, and how did you prevent it?**  
  *Answer:* Switches `s1, s2, s3, s4` form a physical cycle. Standard Layer 2 switches flood ARP broadcasts across all ports, causing packets to circulate infinitely. In `sdn_controller.py`, we intercept ARP requests, maintain an IP-to-port mapping table, and forward ARP requests as point-to-point unicast packets directly to the destination switch port.

* **Q: Which OpenFlow match fields did you use for traffic steering?**  
  *Answer:* We match on `eth_type=0x0800` (IPv4), `ip_proto=6` (TCP), and `tcp_dst=5001` vs `tcp_dst=5002` to forward packets to different physical switch output ports.

* **Q: What is the difference between proactive and reactive flow installation?**  
  *Answer:* Proactive flows are pre-installed by the controller during switch handshake (`switch_features`), avoiding `PacketIn` latency for known paths. Reactive flows are installed on demand when an unhandled packet triggers a `PacketIn` event.

---

### Questions for Member 3 (QoS, Dynamic Triggers & Failover)

* **Q: How does the application layer communicate with the SDN controller?**  
  *Answer:* We implemented an Application-to-SDN REST interface. The broker exposes an internal metric counter. When the count exceeds 15 packets, it makes an HTTP `POST` request to the controller's REST endpoint at `http://127.0.0.1:8080/sdn/policy` with the flow parameters.

* **Q: What happens when the primary fast link `s1-s2` is cut?**  
  *Answer:* The controller listens for OpenFlow PortStatus events (`OFPPortStatus`). When `OFPPS_LINK_DOWN` is received, the controller removes the `s2` flow entries and installs failover rules directing traffic to `s3`, achieving sub-second recovery without restarting client sockets.

* **Q: Why is the latency difference so significant between the two paths?**  
  *Answer:* The Fast Path has 20 Mbps bandwidth with 2ms per-hop link delay, while the Standard Path has 5 Mbps bandwidth with 25ms per-hop link delay, creating an empirical latency difference of ~6ms vs ~55ms.

---

## 6. Git Collaboration Workflow for Teammates

### Pulling the Latest Code
Before starting work or practicing the presentation, always pull the latest changes:
```bash
git pull origin main
```

### Making Changes on a Feature Branch
```bash
# 1. Create your branch
git checkout -b feature/member1-socket-improvements

# 2. Make your edits and commit
git add .
git commit -m "Enhance subscriber error handling on socket EOF"

# 3. Push your branch to GitHub
git push -u origin feature/member1-socket-improvements
```

### Merging Changes Back to Main
```bash
git checkout main
git pull origin main
git merge feature/member1-socket-improvements
git push origin main
```

---

## 7. Quick Troubleshooting Reference

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Address already in use` | Old Broker/Controller process still running | Run `killall python3 osken-manager` |
| `Cannot find switch ovsbr` | Open vSwitch service is stopped | Run `sudo systemctl restart ovs-vswitchd` |
| Mininet fails with `Device or resource busy` | Previous Mininet crashed | Run `sudo mn -c` |
| `ModuleNotFoundError: No module named 'os_ken'` | Virtual environment not activated | Run `source .venv/bin/activate` |
