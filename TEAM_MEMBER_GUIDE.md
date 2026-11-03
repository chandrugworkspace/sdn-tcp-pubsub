# Team Member Execution Guide: Running by Role & Operating System

This guide provides step-by-step instructions for each of the 3 team members to clone, set up, and run their respective parts of the **Publish–Subscribe Messaging System over TCP with SDN** on their own machines.

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

## 3. Guide for Member 1: TCP Socket & Pub–Sub Lead

### Role Focus (Deliverable 1 — 15 Marks)
* **Files Owned:**
  * `pubsub/protocol.py` (Wire framing, 4-byte big-endian header)
  * `pubsub/broker.py` (Multi-port listeners, concurrency lock)
  * `pubsub/subscriber.py` (Subscription handling, latency timestamps)
  * `pubsub/publisher.py` (Reliability ACKs, sequence numbering)

### How Member 1 Runs & Demonstrates Standalone Mode
*(Can be run on any OS terminal without root/sudo and without Mininet!)*

```
[Terminal 1: Broker]  <--- TCP 5001 (Priority) & TCP 5002 (Standard)
         ^                                   ^
         |                                   |
[Terminal 2 & 3: Subscribers]      [Terminal 4: Publisher]
```

1. **Terminal 1 — Start the Multi-Port Broker:**
   ```bash
   source .venv/bin/activate
   python3 pubsub/broker.py --host 127.0.0.1 --priority-port 5001 --std-port 5002
   ```

2. **Terminal 2 — Start Standard Topic Subscriber:**
   ```bash
   source .venv/bin/activate
   python3 pubsub/subscriber.py --broker 127.0.0.1 --port 5002 --topics sensors/temp --csv std_latency.csv
   ```

3. **Terminal 3 — Start High-Priority Topic Subscriber:**
   ```bash
   source .venv/bin/activate
   python3 pubsub/subscriber.py --broker 127.0.0.1 --port 5001 --topics alerts/fire --csv prio_latency.csv
   ```

4. **Terminal 4 — Publish Messages:**
   ```bash
   source .venv/bin/activate
   # Publish standard traffic
   python3 pubsub/publisher.py --broker 127.0.0.1 --port 5002 --topic sensors/temp --count 20 --interval 0.2

   # Publish priority traffic
   python3 pubsub/publisher.py --broker 127.0.0.1 --port 5001 --topic alerts/fire --count 10 --interval 0.2
   ```

5. **Expected Output Verification:**
   * Terminal 1 logs client connections, subscriptions, and message deliveries.
   * Terminals 2 and 3 display real-time received payloads and one-way latency in milliseconds.
   * Terminal 4 confirms `PUB_ACK` with `delivered_to: X subs`.

---

## 4. Guide for Member 2: Mininet Topology & SDN Controller Lead

### Role Focus (Deliverable 2 — 25 Marks)
* **Files Owned:**
  * `topology/pubsub_topo.py` (4-Switch Diamond Multi-Path Topology)
  * `controller/sdn_controller.py` (OpenFlow 1.3 Controller, Port Steering, Directed ARP)

### How Member 2 Runs & Demonstrates the SDN Network

1. **Terminal 1 — Launch the OS-Ken OpenFlow Controller:**
   ```bash
   # In Bash / Zsh:
   source .venv/bin/activate
   osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py

   # In Fish shell (CachyOS):
   source .venv/bin/activate.fish
   osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py

   # OR directly without activating:
   .venv/bin/osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py
   ```
   *Expected Controller log:* Switches `s1`, `s2`, `s3`, `s4` connect and initialize.

2. **Terminal 2 — Launch the Mininet Diamond Topology:**
   ```bash
   # Clean previous state and start
   sudo mn -c
   sudo python3 topology/pubsub_topo.py
   ```

3. **Inside the `mininet>` prompt — Verify Network Reachability:**
   ```text
   mininet> pingall
   ```
   *Verification:* 0% dropped packets. Loop-free directed ARP ensures no broadcast storm.

4. **Inspect Flow Tables on Switch `s1`:**
   ```text
   mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
   ```
   *Verification:*
   * Port 5001 traffic matches rule forwarding to port 3 (`s1 -> s2` Fast Path).
   * Port 5002 traffic matches rule forwarding to port 4 (`s1 -> s3` Standard Path).

---

## 5. Guide for Member 3: Integration, Benchmarking & Failover Lead

### Role Focus (Deliverable 2 Integration — 25 Marks)
* **Files Owned:**
  * `benchmarks/plot_metrics.py` (Latency & Scalability graphs)
  * Webhook trigger logic in `pubsub/broker.py` & `controller/sdn_controller.py`
  * `README.md` & Performance Evaluation Reports

### How Member 3 Runs End-to-End Integration & Demonstrations

Follow this procedure with Terminal 1 (Controller) and Terminal 2 (Mininet) already running:

#### A. Start Broker and Subscribers on Mininet Hosts
Inside `mininet>` in Terminal 2:
```text
mininet> h3 python3 pubsub/broker.py --sdn-url http://127.0.0.1:8080 > broker.log 2>&1 &
mininet> h4 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5002 --topics sensors/temp --csv std_latency.csv > sub_std.log 2>&1 &
mininet> h5 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5001 --topics alerts/fire --csv prio_latency.csv > sub_prio.log 2>&1 &
```

#### B. Demonstrate Dynamic SDN Webhook Promotion
Publish 25 standard messages from `h1` and 25 priority messages from `h2`:
```text
mininet> h1 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5002 --topic sensors/temp --count 25 --interval 0.3
mininet> h2 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5001 --topic alerts/fire --count 25 --interval 0.3
```

*What happens automatically:*
* After message #15, the Broker fires the REST webhook `POST /sdn/policy` to the controller.
* The Controller pushes `priority=50` rules promoting `h1` from `s3` (Standard) to `s2` (Fast Path).
* Check the logs to see latency drop from **~55–60 ms** down to **~6–10 ms**:
  ```text
  mininet> sh tail -n 25 sub_std.log
  ```

#### C. Demonstrate the Challenging Scenario: Link Failure & Fast Failover
While `h2` is streaming priority traffic, simulate bringing down the Fast Path:
```text
mininet> link s1 s2 down
```
*Observe:* In Terminal 1, the controller detects `OFPPS_LINK_DOWN` and immediately reroutes all traffic over `s3`. Messages continue flowing with zero disconnections.  
Restore the link:
```text
mininet> link s1 s2 up
```

#### D. Generate Latency Comparison Plot
Exit Mininet (`mininet> exit`) and run:
```bash
python3 benchmarks/plot_metrics.py std_latency.csv prio_latency.csv latency_comparison.png
```
This produces `latency_comparison.png` for inclusion in your lab report and presentation slides.

---

## 6. Git Collaboration Workflow for Teammates

### Pulling the Latest Code
Before starting work, always pull the latest changes from `main`:
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

## 7. Quick Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Address already in use` | Old Broker/Controller process still running | Run `killall python3 osken-manager` |
| `Cannot find switch ovsbr` | Open vSwitch service is stopped | Run `sudo systemctl restart ovs-vswitchd` |
| Mininet fails with `Device or resource busy` | Previous Mininet crashed | Run `sudo mn -c` |
| `ModuleNotFoundError: No module named 'os_ken'` | Virtual environment not activated | Run `source .venv/bin/activate` |
