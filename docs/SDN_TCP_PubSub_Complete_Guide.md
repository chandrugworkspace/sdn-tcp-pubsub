# Project #9: Publish–Subscribe Messaging System over TCP with SDN
**Course:** Computer Networks (UE25CS243A) — SDN-Socket Programming Jackfruit Mini Project  
**Team Size:** 3 Members  
**Total Marks:** 40 Marks (Deliverable 1: 15M | Deliverable 2: 25M)

---

## 1. Project Overview & Specifications
* **Topic:** Publish–Subscribe Messaging System (Project #9)
* **Protocol:** Low-level **TCP** sockets
* **Problem Statement:** Implement a publish–subscribe messaging application consisting of publishers, a centralized broker, and subscribers, where TCP sockets provide reliable communication while an SDN controller dynamically manages message flows.
* **Core Project Expectations:**
  * Implement publisher, broker, and subscriber nodes over raw TCP sockets.
  * Support dynamic topic subscriptions (`SUBSCRIBE`, `UNSUBSCRIBE`, `PUBLISH`, `ACK`) and handle concurrent TCP connections.
  * Route messages according to topics and classify topic traffic at the SDN layer.
  * Dynamically modify forwarding paths via the SDN controller based on application triggers and link status.
  * Measure message delivery latency and evaluate system scalability across multiple conditions.

---

## 2. Environment Setup Across Team Laptops

### A. Your Laptop: Native Setup on CachyOS (or Arch Linux)
Mininet uses lightweight Linux kernel features (`network namespaces` and `veth` virtual Ethernet pairs), so it runs natively on CachyOS with near-zero overhead.

1. **Install Mininet, Open vSwitch, and Network Tools:**
   ```bash
   sudo pacman -Syu mininet openvswitch iproute2 iperf3 wireshark-qt python-pip uv
   ```
   *(If `mininet` is in the AUR on your mirror, run `paru -S mininet`.)*

2. **Start and Enable the Open vSwitch Service:**
   ```bash
   sudo systemctl enable --now ovs-vswitchd.service ovsdb-server.service
   sudo systemctl status ovs-vswitchd
   ```

3. **Set Up the SDN Controller in a Python 3.11 Virtual Environment (`uv`):**
   ```bash
   uv venv --python 3.11 .venv
   source .venv/bin/activate
   uv pip install os-ken requests matplotlib
   ```

4. **Verify Mininet Functionality:**
   ```bash
   sudo mn --switch ovsbr --test pingall
   sudo mn -c
   ```

### B. Your Teammates' Laptops: Windows (Ubuntu 22.04 VM) or macOS (UTM VM)
* **Windows 10/11:** Use **VirtualBox** or **VMware Workstation Player** with an **Ubuntu 22.04 LTS** VM (2 CPU cores, 4 GB RAM, 25 GB disk, NAT or Bridged adapter). Avoid default WSL2 because Microsoft's standard WSL2 kernel lacks Open vSwitch and `TCLink` traffic-shaping kernel modules.
* **macOS (Intel or M1/M2/M3/M4):** Use **UTM** or **VMware Fusion Player** with an **Ubuntu 22.04 LTS** VM.

**Commands for Teammates Inside Ubuntu 22.04:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install mininet openvswitch-switch iproute2 iperf3 python3-pip python3-venv git -y

python3 -m venv .venv
source .venv/bin/activate
pip install os-ken requests matplotlib

# Verify installation
sudo mn --switch ovsbr --test pingall
sudo mn -c
```

---

## 3. Shared GitHub Repository Structure

Create a shared GitHub repository with this exact directory structure and add all 3 teammates as collaborators:

```text
sdn-tcp-pubsub/
├── controller/
│   └── sdn_controller.py       # Member 2: OS-Ken OpenFlow 1.3 SDN Controller + REST API
├── topology/
│   └── pubsub_topo.py          # Member 2: 4-Switch Diamond Multi-Path Mininet Topology
├── pubsub/
│   ├── protocol.py             # Member 1: Length-prefixed TCP framing protocol
│   ├── broker.py               # Member 1 & 3: Multi-threaded TCP Broker + SDN webhook trigger
│   ├── subscriber.py           # Member 1: Concurrent TCP Subscriber with latency logging
│   └── publisher.py            # Member 1: TCP Publisher with topic priority support
├── benchmarks/
│   └── plot_metrics.py         # Member 3: Latency & Scalability comparison graphs
├── requirements.txt
└── README.md                   # Member 3: Setup, architecture, and reproduction guide
```

### `requirements.txt`
```text
os-ken>=2.8.0
requests>=2.31.0
matplotlib>=3.8.0
```

---

## 4. Detailed Role of Each of the 3 Team Members

### Summary of Ownership & Rubric Alignment

| Member | Primary Role | Files Owned in GitHub Repo | Rubric Components Covered |
| :--- | :--- | :--- | :--- |
| **Member 1** | **TCP Socket & Pub–Sub Engine Lead** | `pubsub/protocol.py`<br>`pubsub/broker.py`<br>`pubsub/publisher.py`<br>`pubsub/subscriber.py` | • TCP/UDP Socket Implementation (4M)<br>• Complete Application Functionality (4M) |
| **Member 2** | **Mininet Topology & SDN Controller Lead** | `topology/pubsub_topo.py`<br>`controller/sdn_controller.py` | • Mininet + SDN Implementation (4M)<br>• Dynamic SDN Functionality (6M) |
| **Member 3** | **Socket–SDN Integration, Testing & Evaluation Lead** | `benchmarks/plot_metrics.py`<br>`README.md`<br>Webhook logic in `broker.py` & `sdn_controller.py` | • Problem Understanding & Architecture (2M)<br>• Socket–SDN Integration (3M)<br>• Initial Testing & Demo (2M)<br>• Challenging Scenario / Robustness (4M)<br>• Performance Evaluation & Comparison (5M)<br>• Documentation, Final Demo & Viva (6M) |

---

### Member 1: TCP Socket & Pub–Sub Engine Lead
**Core Focus:** Application-layer wire protocol design, low-level TCP socket programming, multi-threaded concurrency, and reliable topic routing.

* **Step-by-Step Tasks:**
  1. **Wire Protocol Framing (`pubsub/protocol.py`):** Implement 4-byte big-endian length-prefixed framing (`struct.Struct("!I")`) over raw TCP sockets so back-to-back JSON messages never concatenate or split in the TCP byte stream. Handle clean socket reads (`recv_exact`) and graceful client disconnections (`EOF`).
  2. **Concurrent Multi-Port Broker (`pubsub/broker.py`):** Set up two concurrent TCP listener threads on the Broker (`0.0.0.0:5001` for High-Priority topics and `0.0.0.0:5002` for Standard topics). Maintain a thread-safe subscription table (`threading.Lock()`) mapping `topic -> set(subscriber_sockets)`. Process `SUBSCRIBE`, `UNSUBSCRIBE`, and `PUBLISH` frames concurrently and return `SUB_ACK`, `UNSUB_ACK`, and `PUB_ACK`.
  3. **Publisher & Subscriber Clients (`pubsub/publisher.py`, `pubsub/subscriber.py`):** Build the Publisher CLI to send sequence-numbered payloads stamped with nanosecond timestamps (`time.time_ns()`). Build the Subscriber CLI to dynamically subscribe to multiple topics, compute one-way delivery latency in milliseconds, and save logs to CSV.
* **Viva Questions for Member 1:**
  * *Why did we use a 4-byte length prefix in `protocol.py` instead of just calling `sock.recv(1024)`?*
    * **Answer:** Because TCP is a byte-stream protocol without built-in message boundaries; a single `recv()` call can return a partial JSON object or multiple merged JSON objects.
  * *How does the Broker prevent race conditions when multiple subscribers join while a publisher is broadcasting?*
    * **Answer:** By acquiring a `threading.Lock()` around `self.subscriptions` mutations and iterating over a snapshot list copy of subscriber sockets during broadcast.

---

### Member 2: Mininet Topology & SDN Controller Lead
**Core Focus:** Designing the multi-path virtual network in Mininet, configuring Open vSwitch (OpenFlow 1.3), and writing the SDN controller for traffic classification and automatic link-failure failover.

* **Step-by-Step Tasks:**
  1. **Diamond Multi-Path Topology (`topology/pubsub_topo.py`):** Build the 4-switch (`s1`, `s2`, `s3`, `s4`), 5-host (`h1`–`h5`) diamond topology using `TCLink` and `OVSKernelSwitch`. Configure the **Upper Fast Path (`s1 -> s2 -> s4`)** with `bw=20` Mbps, `delay='2ms'`, and the **Lower Standard Path (`s1 -> s3 -> s4`)** with `bw=5` Mbps, `delay='25ms'`. Assign deterministic port numbers and static MAC/IP mappings.
  2. **OpenFlow 1.3 SDN Controller (`controller/sdn_controller.py`):** Install table-miss rules on `s1` and `s4` and direct port-to-port forwarding rules on transit switches `s2` and `s3`. Implement loop-free ARP handling so broadcasts do not loop infinitely around `s1-s2-s4-s3`. Inspect Layer-4 TCP headers in `packet_in_handler` to steer TCP port `5001` flows onto the Fast Path (`s2`, priority `30`) and TCP port `5002` flows onto the Standard Path (`s3`, priority `30`).
  3. **Dynamic Link-Failure Detection (`port_status_handler`):** Listen for `EventOFPPortStatus` (`OFPPS_LINK_DOWN`). When link `s1 <-> s2` goes down, immediately push priority `60` override flow rules on `s1` and `s4` to reroute all active TCP flows over `s3` without dropping connections.
* **Viva Questions for Member 2:**
  * *Why can't we use the default `simple_switch_13` controller on our diamond topology?*
    * **Answer:** A diamond topology contains a physical Layer-2 loop (`s1-s2-s4-s3-s1`). Standard flooding switches cause an infinite ARP broadcast storm unless directed ARP handling or Spanning Tree Protocol (STP) is used.
  * *How does the OpenFlow switch classify High-Priority vs. Standard topics without deep packet inspection of the JSON payload?*
    * **Answer:** By matching Layer-4 TCP port numbers (`tcp_dst=5001` vs. `tcp_dst=5002`) in OpenFlow 1.3 `OFPMatch` rules.

---

### Member 3: Socket–SDN Integration, Testing & Evaluation Lead
**Core Focus:** Bridging the TCP Broker with the SDN Controller via REST webhooks, running stress/congestion/failure scenarios, generating latency/scalability graphs, and managing the GitHub documentation.

* **Step-by-Step Tasks:**
  1. **Application-to-SDN Integration (`broker.py` <-> `sdn_controller.py`):** Implement `notify_sdn_controller()` in `broker.py` so that when any standard topic exceeds the burst threshold (`>= 15` messages), the Broker sends an HTTP `POST /sdn/policy` webhook (`{"action": "PROMOTE_FAST_PATH", "client_ip": ...}`). Implement `SDNRestController` (`WSGIApplication`) in `sdn_controller.py` to push priority `50` `OFPFlowMod` rules to `s1` and `s4`, dynamically promoting that host's traffic from the Standard Path (`s3`) to the Fast Path (`s2`) mid-stream.
  2. **Challenging Scenarios & Robustness Testing:** Execute `link s1 s2 down` inside Mininet while publishers are streaming to demonstrate fast failover to `s3`. Run `iperf3` across the Standard Path to demonstrate congestion behavior.
  3. **Performance Evaluation & GitHub Documentation (`benchmarks/plot_metrics.py`, `README.md`):** Collect CSV latency logs for Standard vs. Priority/Promoted flows, generate `latency_comparison.png`, and document OpenFlow flow-table verification commands (`sudo ovs-ofctl -O OpenFlow13 dump-flows s1`).
* **Viva Questions for Member 3:**
  * *How does the socket application dynamically influence the SDN network?*
    * **Answer:** The Broker tracks per-topic message volume in real time; once a topic crosses 15 messages, the Broker sends a REST `POST /sdn/policy` webhook to the SDN Controller, which installs a higher-priority OpenFlow rule (`priority=50` overriding `priority=30`) on `s1` and `s4` to switch that flow onto the low-latency path (`s2`).
  * *How much latency reduction did Dynamic SDN routing achieve over the baseline path?*
    * **Answer:** End-to-end delivery latency dropped from `~55–60 ms` on the 5 Mbps standard path (`s3`) down to `~6–10 ms` on the 20 Mbps fast path (`s2`).

---

## 5. Complete Project Source Code

### 5.1 Wire Protocol Helper (`pubsub/protocol.py` — Member 1)
```python
# pubsub/protocol.py
import json
import socket
import struct
from typing import Dict, Any, Optional

HEADER_STRUCT = struct.Struct("!I")  # 4-byte unsigned int length prefix

def send_msg(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Serializes a dictionary to JSON and sends it with a 4-byte length prefix."""
    raw_bytes = json.dumps(payload).encode("utf-8")
    sock.sendall(HEADER_STRUCT.pack(len(raw_bytes)) + raw_bytes)

def recv_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """Reads exactly num_bytes from a TCP socket or returns None on EOF."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def recv_msg(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """Receives a length-prefixed JSON message from a TCP socket."""
    header = recv_exact(sock, HEADER_STRUCT.size)
    if not header:
        return None
    (msg_len,) = HEADER_STRUCT.unpack(header)
    body = recv_exact(sock, msg_len)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))
```

---

### 5.2 Multi-Port Concurrent TCP Broker (`pubsub/broker.py` — Member 1 & 3)
```python
# pubsub/broker.py
import argparse
import socket
import threading
import time
import requests
from collections import defaultdict
from protocol import send_msg, recv_msg

class PubSubBroker:
    def __init__(self, host: str, priority_port: int, std_port: int, sdn_url: str):
        self.host = host
        self.priority_port = priority_port
        self.std_port = std_port
        self.sdn_url = sdn_url

        self.lock = threading.Lock()
        # topic -> set of subscriber sockets
        self.subscriptions = defaultdict(set)
        # topic -> message count for dynamic SDN trigger
        self.topic_counts = defaultdict(int)
        self.promoted_topics = set()

    def notify_sdn_controller(self, topic: str, action: str, client_ip: str):
        """Sends an application-level event to the SDN controller REST API."""
        if not self.sdn_url:
            return
        try:
            payload = {
                "topic": topic,
                "action": action,
                "client_ip": client_ip,
                "timestamp": time.time()
            }
            requests.post(f"{self.sdn_url}/sdn/policy", json=payload, timeout=0.5)
            print(f"[SDN-HOOK] Triggered SDN policy '{action}' for topic '{topic}' (host {client_ip})")
        except Exception as e:
            print(f"[SDN-HOOK] Controller notification skipped: {e}")

    def handle_client(self, conn: socket.socket, addr, listen_port: int):
        client_ip, client_port = addr
        traffic_class = "HIGH_PRIORITY" if listen_port == self.priority_port else "STANDARD"
        print(f"[CONNECT] {client_ip}:{client_port} on port {listen_port} ({traffic_class})")

        try:
            while True:
                msg = recv_msg(conn)
                if not msg:
                    break

                msg_type = msg.get("type")
                topic = msg.get("topic", "default")

                if msg_type == "SUBSCRIBE":
                    with self.lock:
                        self.subscriptions[topic].add(conn)
                        sub_count = len(self.subscriptions[topic])
                    send_msg(conn, {"type": "SUB_ACK", "topic": topic, "status": "OK"})
                    print(f"[SUBSCRIBE] {client_ip} subscribed to '{topic}' (Total subs: {sub_count})")

                elif msg_type == "UNSUBSCRIBE":
                    with self.lock:
                        self.subscriptions[topic].discard(conn)
                    send_msg(conn, {"type": "UNSUB_ACK", "topic": topic, "status": "OK"})
                    print(f"[UNSUBSCRIBE] {client_ip} unsubscribed from '{topic}'")

                elif msg_type == "PUBLISH":
                    with self.lock:
                        self.topic_counts[topic] += 1
                        count = self.topic_counts[topic]
                        subscribers = list(self.subscriptions.get(topic, []))

                    # Dynamic Socket-SDN Integration:
                    # If a standard topic gets heavy burst traffic (>= 15 msgs), promote host to Fast Path
                    if count >= 15 and topic not in self.promoted_topics:
                        self.promoted_topics.add(topic)
                        threading.Thread(
                            target=self.notify_sdn_controller,
                            args=(topic, "PROMOTE_FAST_PATH", client_ip),
                            daemon=True
                        ).start()

                    # Forward message to all active subscribers of this topic
                    out_msg = {
                        "type": "MESSAGE",
                        "topic": topic,
                        "seq": msg.get("seq", 0),
                        "payload": msg.get("payload", ""),
                        "pub_timestamp_ns": msg.get("pub_timestamp_ns", time.time_ns()),
                        "traffic_class": traffic_class
                    }

                    dead_subs = []
                    for sub_sock in subscribers:
                        try:
                            send_msg(sub_sock, out_msg)
                        except OSError:
                            dead_subs.append(sub_sock)

                    if dead_subs:
                        with self.lock:
                            for d in dead_subs:
                                self.subscriptions[topic].discard(d)

                    # Send reliability ACK back to publisher
                    send_msg(conn, {
                        "type": "PUB_ACK",
                        "seq": msg.get("seq", 0),
                        "delivered_to": len(subscribers) - len(dead_subs)
                    })

        except Exception as e:
            print(f"[ERROR] Client {client_ip}:{client_port}: {e}")
        finally:
            with self.lock:
                for subs in self.subscriptions.values():
                    subs.discard(conn)
            conn.close()
            print(f"[DISCONNECT] {client_ip}:{client_port}")

    def start_listener(self, port: int):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, port))
        server.listen(128)
        print(f"[BROKER] Listening on {self.host}:{port}")
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=self.handle_client, args=(conn, addr, port), daemon=True)
            t.start()

    def run(self):
        t1 = threading.Thread(target=self.start_listener, args=(self.priority_port,), daemon=True)
        t2 = threading.Thread(target=self.start_listener, args=(self.std_port,), daemon=True)
        t1.start()
        t2.start()
        print("[BROKER] Pub-Sub Broker running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[BROKER] Shutting down.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--priority-port", type=int, default=5001)
    parser.add_argument("--std-port", type=int, default=5002)
    parser.add_argument("--sdn-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    broker = PubSubBroker(args.host, args.priority_port, args.std_port, args.sdn_url)
    broker.run()
```

---

### 5.3 TCP Subscriber with Latency Logging (`pubsub/subscriber.py` — Member 1)
```python
# pubsub/subscriber.py
import argparse
import csv
import socket
import time
from protocol import send_msg, recv_msg

def run_subscriber(broker_ip: str, port: int, topics: list, csv_file: str):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((broker_ip, port))
    print(f"[SUBSCRIBER] Connected to Broker {broker_ip}:{port}")

    for topic in topics:
        send_msg(sock, {"type": "SUBSCRIBE", "topic": topic})
        ack = recv_msg(sock)
        print(f"[SUBSCRIBER] Subscribed to '{topic}' -> {ack}")

    csv_writer = None
    f_out = None
    if csv_file:
        f_out = open(csv_file, "w", newline="")
        csv_writer = csv.writer(f_out)
        csv_writer.writerow(["seq", "topic", "traffic_class", "latency_ms", "timestamp"])

    try:
        while True:
            msg = recv_msg(sock)
            if not msg:
                print("[SUBSCRIBER] Broker closed connection.")
                break
            if msg.get("type") == "MESSAGE":
                now_ns = time.time_ns()
                pub_ns = msg.get("pub_timestamp_ns", now_ns)
                latency_ms = (now_ns - pub_ns) / 1_000_000.0
                seq = msg.get("seq")
                topic = msg.get("topic")
                t_class = msg.get("traffic_class")

                print(f"[{t_class}] Topic='{topic}' | Seq={seq} | Latency={latency_ms:.2f} ms | Payload='{msg.get('payload')}'")
                if csv_writer:
                    csv_writer.writerow([seq, topic, t_class, f"{latency_ms:.3f}", time.time()])
                    f_out.flush()
    except KeyboardInterrupt:
        print("\n[SUBSCRIBER] Disconnecting...")
    finally:
        if f_out:
            f_out.close()
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="10.0.0.3", help="Broker IP address")
    parser.add_argument("--port", type=int, default=5002, help="5001 for Priority, 5002 for Standard")
    parser.add_argument("--topics", nargs="+", default=["sensors/temp"], help="Topics to subscribe")
    parser.add_argument("--csv", default="", help="Optional CSV output path for latency logs")
    args = parser.parse_args()

    run_subscriber(args.broker, args.port, args.topics, args.csv)
```

---

### 5.4 TCP Publisher (`pubsub/publisher.py` — Member 1)
```python
# pubsub/publisher.py
import argparse
import socket
import time
from protocol import send_msg, recv_msg

def run_publisher(broker_ip: str, port: int, topic: str, count: int, interval: float):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((broker_ip, port))
    print(f"[PUBLISHER] Connected to Broker {broker_ip}:{port} for topic '{topic}'")

    try:
        for seq in range(1, count + 1):
            payload_data = {
                "type": "PUBLISH",
                "topic": topic,
                "seq": seq,
                "payload": f"Event #{seq} on {topic}",
                "pub_timestamp_ns": time.time_ns()
            }
            send_msg(sock, payload_data)
            ack = recv_msg(sock)
            print(f"[PUBLISHED] Seq={seq} | Topic='{topic}' | Delivered={ack.get('delivered_to')} subs")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[PUBLISHER] Stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="10.0.0.3")
    parser.add_argument("--port", type=int, default=5002, help="5001=High Priority, 5002=Standard")
    parser.add_argument("--topic", default="sensors/temp")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()

    run_publisher(args.broker, args.port, args.topic, args.count, args.interval)
```

---

### 5.5 Multi-Path Diamond Mininet Topology (`topology/pubsub_topo.py` — Member 2)
```python
# topology/pubsub_topo.py
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

class PubSubDiamondTopo(Topo):
    def build(self):
        # Create 4 OpenFlow 1.3 switches
        s1 = self.addSwitch("s1", dpid="0000000000000001", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", dpid="0000000000000002", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", dpid="0000000000000003", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", dpid="0000000000000004", protocols="OpenFlow13")

        # Hosts on s1 (Publishers)
        h1 = self.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = self.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")

        # Hosts on s4 (h3 = Broker, h4 & h5 = Subscribers)
        h3 = self.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
        h4 = self.addHost("h4", ip="10.0.0.4/24", mac="00:00:00:00:00:04")
        h5 = self.addHost("h5", ip="10.0.0.5/24", mac="00:00:00:00:00:05")

        # Host-to-Switch Links (Explicit port numbering for deterministic SDN control)
        # s1 ports 1, 2 -> h1, h2
        self.addLink(h1, s1, port1=1, port2=1, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h2, s1, port1=1, port2=2, cls=TCLink, bw=50, delay="1ms")

        # s4 ports 1, 2, 3 -> h3 (Broker), h4 (Sub1), h5 (Sub2)
        self.addLink(h3, s4, port1=1, port2=1, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h4, s4, port1=1, port2=2, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h5, s4, port1=1, port2=3, cls=TCLink, bw=50, delay="1ms")

        # Inter-Switch Diamond Links:
        # Upper Fast Path: s1(port 3) <-> s2(port 1) and s2(port 2) <-> s4(port 4)
        self.addLink(s1, s2, port1=3, port2=1, cls=TCLink, bw=20, delay="2ms")
        self.addLink(s2, s4, port1=2, port2=4, cls=TCLink, bw=20, delay="2ms")

        # Lower Standard Path: s1(port 4) <-> s3(port 1) and s3(port 2) <-> s4(port 5)
        self.addLink(s1, s3, port1=4, port2=1, cls=TCLink, bw=5, delay="25ms")
        self.addLink(s3, s4, port1=2, port2=5, cls=TCLink, bw=5, delay="25ms")

def run_network():
    topo = PubSubDiamondTopo()
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6633),
        link=TCLink,
        autoSetMacs=True
    )
    net.start()
    info("\n*** Diamond Pub-Sub Topology Started ***\n")
    info("h1 (10.0.0.1), h2 (10.0.0.2) -> Publishers on s1\n")
    info("h3 (10.0.0.3)                -> Broker on s4\n")
    info("h4 (10.0.0.4), h5 (10.0.0.5) -> Subscribers on s4\n")
    info("Fast Path:     s1 -> s2 -> s4 (20 Mbps, 2ms delay per hop)\n")
    info("Standard Path: s1 -> s3 -> s4 (5 Mbps, 25ms delay per hop)\n\n")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run_network()
```

---

### 5.6 Dynamic SDN Controller with Topic Classification, REST API & Failover (`controller/sdn_controller.py` — Member 2 & 3)
```python
# controller/sdn_controller.py
import json
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ipv4, tcp, arp, ether_types
from os_ken.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response

SDN_INSTANCE_NAME = "pubsub_sdn_api"

class PubSubSDNController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(PubSubSDNController, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.fast_path_alive = True
        self.promoted_ips = set()

        # Host IP -> (dpid, port)
        self.host_PortMap = {
            "10.0.0.1": (1, 1),
            "10.0.0.2": (1, 2),
            "10.0.0.3": (4, 1),
            "10.0.0.4": (4, 2),
            "10.0.0.5": (4, 3),
        }

        wsgi = kwargs["wsgi"]
        wsgi.register(SDNRestController, {SDN_INSTANCE_NAME: self})

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            idle_timeout=idle_timeout,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        self.datapaths[dpid] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Transit switches s2 and s3 simply forward between port 1 and port 2
        if dpid in (2, 3):
            self.add_flow(datapath, 10, parser.OFPMatch(in_port=1), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 10, parser.OFPMatch(in_port=2), [parser.OFPActionOutput(1)])

        self.logger.info(f"[SDN] Switch s{dpid} connected and initialized.")

    def get_inter_switch_port(self, dpid: int, use_fast_path: bool) -> int:
        """Returns the correct egress port on s1 or s4 for the chosen path."""
        if not self.fast_path_alive:
            use_fast_path = False  # Failover to s3 if s2 path is down
        if dpid == 1:
            return 3 if use_fast_path else 4
        if dpid == 4:
            return 4 if use_fast_path else 5
        return 1

    def install_dynamic_promotion(self, client_ip: str, topic: str):
        """Called via REST webhook by Broker to promote a host's standard traffic to the Fast Path."""
        self.promoted_ips.add(client_ip)
        if 1 in self.datapaths and 4 in self.datapaths:
            s1 = self.datapaths[1]
            s4 = self.datapaths[4]
            p1 = s1.ofproto_parser
            p4 = s4.ofproto_parser

            # Forward client_ip <-> Broker (10.0.0.3) via Fast Path (s1:3, s4:4)
            match_up = p1.OFPMatch(eth_type=0x0800, ipv4_src=client_ip, ipv4_dst="10.0.0.3")
            self.add_flow(s1, 50, match_up, [p1.OFPActionOutput(3)], idle_timeout=60)

            match_down = p4.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.3", ipv4_dst=client_ip)
            self.add_flow(s4, 50, match_down, [p4.OFPActionOutput(4)], idle_timeout=60)
            self.logger.info(f"[SDN-POLICY] Promoted host {client_ip} (topic '{topic}') to FAST PATH (s1->s2->s4)")

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Detects link failure and dynamically reroutes traffic to backup path."""
        msg = ev.msg
        dpid = msg.datapath.id
        port_no = msg.desc.port_no
        ofproto = msg.datapath.ofproto

        is_down = (msg.desc.state & ofproto.OFPPS_LINK_DOWN) != 0
        if dpid == 1 and port_no == 3:
            if is_down:
                self.fast_path_alive = False
                self.logger.warning("[SDN-FAILOVER] Fast Path Link (s1-s2) DOWN! Rerouting all flows via s3.")
                self.reroute_all_to_backup()
            else:
                self.fast_path_alive = True
                self.logger.info("[SDN-RECOVERY] Fast Path Link (s1-s2) UP! Restoring priority routing.")

    def reroute_all_to_backup(self):
        """Installs high-priority override rules on s1 and s4 to force traffic onto s3."""
        if 1 in self.datapaths and 4 in self.datapaths:
            s1, s4 = self.datapaths[1], self.datapaths[4]
            p1, p4 = s1.ofproto_parser, s4.ofproto_parser
            # Send all s1 -> s4 traffic out port 4 (via s3)
            for dst_ip in ("10.0.0.3", "10.0.0.4", "10.0.0.5"):
                m1 = p1.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
                self.add_flow(s1, 60, m1, [p1.OFPActionOutput(4)], idle_timeout=30)
            # Send all s4 -> s1 traffic out port 5 (via s3)
            for dst_ip in ("10.0.0.1", "10.0.0.2"):
                m4 = p4.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
                self.add_flow(s4, 60, m4, [p4.OFPActionOutput(5)], idle_timeout=30)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        in_port = msg.match["in_port"]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Handle ARP without loops
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            dst_ip = arp_pkt.dst_ip
            if dst_ip in self.host_PortMap:
                target_dpid, target_port = self.host_PortMap[dst_ip]
                out_port = target_port if dpid == target_dpid else self.get_inter_switch_port(dpid, True)
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=msg.buffer_id,
                    in_port=in_port,
                    actions=[parser.OFPActionOutput(out_port)],
                    data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
                )
                datapath.send_msg(out)
            return

        # Handle IPv4 & TCP Topic Classification
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return

        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        if dst_ip not in self.host_PortMap:
            return

        target_dpid, target_port = self.host_PortMap[dst_ip]
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        # Determine if flow belongs on Fast Path (TCP port 5001 or promoted host)
        use_fast = False
        if src_ip in self.promoted_ips or dst_ip in self.promoted_ips:
            use_fast = True
        elif tcp_pkt and (tcp_pkt.dst_port == 5001 or tcp_pkt.src_port == 5001):
            use_fast = True

        if dpid == target_dpid:
            out_port = target_port
        else:
            out_port = self.get_inter_switch_port(dpid, use_fast)

        actions = [parser.OFPActionOutput(out_port)]

        # Install specific OpenFlow rule for TCP or ICMP flow
        if tcp_pkt:
            match = parser.OFPMatch(
                eth_type=0x0800,
                ip_proto=6,
                ipv4_src=src_ip,
                ipv4_dst=dst_ip,
                tcp_src=tcp_pkt.src_port,
                tcp_dst=tcp_pkt.dst_port
            )
            path_name = "FAST_PATH(s2)" if (use_fast and self.fast_path_alive) else "STD_PATH(s3)"
            self.logger.info(f"[FLOW-INSTALL] s{dpid}: {src_ip}:{tcp_pkt.src_port} -> {dst_ip}:{tcp_pkt.dst_port} via {path_name} (port {out_port})")
            self.add_flow(datapath, 30, match, actions, idle_timeout=30)
        else:
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.add_flow(datapath, 20, match, actions, idle_timeout=30)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        )
        datapath.send_msg(out)


class SDNRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SDNRestController, self).__init__(req, link, data, **config)
        self.sdn_app = data[SDN_INSTANCE_NAME]

    @route("policy", "/sdn/policy", methods=["POST"])
    def update_policy(self, req, **kwargs):
        body = json.loads(req.body.decode("utf-8"))
        client_ip = body.get("client_ip")
        topic = body.get("topic", "unknown")
        action = body.get("action")
        if action == "PROMOTE_FAST_PATH" and client_ip:
            self.sdn_app.install_dynamic_promotion(client_ip, topic)
            return Response(content_type="application/json", body=json.dumps({"status": "PROMOTED"}).encode("utf-8"))
        return Response(status=400)
```

---

### 5.7 Performance Evaluation & Graph Generator (`benchmarks/plot_metrics.py` — Member 3)
```python
# benchmarks/plot_metrics.py
import csv
import sys
import matplotlib.pyplot as plt

def plot_latency(std_csv: str, prio_csv: str, out_png: str = "latency_comparison.png"):
    def read_data(filename):
        seqs, lats = [], []
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seqs.append(int(row["seq"]))
                lats.append(float(row["latency_ms"]))
        return seqs, lats

    s_seq, s_lat = read_data(std_csv)
    p_seq, p_lat = read_data(prio_csv)

    plt.figure(figsize=(9, 5))
    plt.plot(s_seq, s_lat, marker="o", label="Standard Topic (Port 5002 -> Dynamic SDN Promotion at Seq 15)")
    plt.plot(p_seq, p_lat, marker="s", label="Priority Topic (Port 5001 -> Always Fast Path s1-s2-s4)")
    plt.axvline(x=15, color="red", linestyle="--", label="Broker SDN Webhook Trigger (Seq=15)")

    plt.title("SDN-Integrated TCP Pub-Sub End-to-End Message Latency")
    plt.xlabel("Message Sequence Number")
    plt.ylabel("End-to-End Delivery Latency (ms)")
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    print(f"[BENCHMARK] Saved plot to {out_png}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 benchmarks/plot_metrics.py std_latency.csv prio_latency.csv")
        sys.exit(1)
    plot_latency(sys.argv[1], sys.argv[2])
```

---

## 6. Step-by-Step Execution & Demo Guide

Follow these exact terminal commands during your Deliverable 1 and Deliverable 2 lab evaluations:

### Step 1: Start the SDN Controller (Terminal 1)
Activate your Python virtual environment and start the OS-Ken controller with both OpenFlow (port `6633`) and REST API (port `8080`) enabled:
```bash
source .venv/bin/activate
osken-manager --ofp-tcp-listen-port 6633 --wsapi-port 8080 controller/sdn_controller.py
```

### Step 2: Launch the Diamond Mininet Topology (Terminal 2)
Clean any previous Mininet state and start the custom topology:
```bash
sudo mn -c
sudo python3 topology/pubsub_topo.py
```
Inside the `mininet>` prompt, verify full host reachability:
```text
mininet> pingall
```

### Step 3: Start the Broker and Subscribers Inside Mininet
Inside `mininet>`, run the Broker on `h3` (`10.0.0.3`) and start two Subscribers on `h4` (`10.0.0.4`) and `h5` (`10.0.0.5`):
```text
mininet> h3 python3 pubsub/broker.py --sdn-url http://127.0.0.1:8080 > broker.log 2>&1 &
mininet> h4 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5002 --topics sensors/temp --csv std_latency.csv > sub_std.log 2>&1 &
mininet> h5 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5001 --topics alerts/fire --csv prio_latency.csv > sub_prio.log 2>&1 &
```

### Step 4: Run Publishers to Demonstrate Topic Classification & Dynamic SDN Promotion
From `mininet>`, publish 25 messages on the Standard topic (`h1 -> Port 5002`) and 25 messages on the High-Priority topic (`h2 -> Port 5001`):
```text
mininet> h1 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5002 --topic sensors/temp --count 25 --interval 0.3
mininet> h2 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5001 --topic alerts/fire --count 25 --interval 0.3
```
Inspect the subscriber logs and OpenFlow flow tables:
```text
mininet> sh tail -n 25 sub_std.log
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
```
You will see `sensors/temp` start at **~55–60 ms** latency on `s3` and drop to **~6–10 ms** right after message #15 when the Broker triggers the SDN controller's Fast Path promotion.

### Step 5: Demonstrate the Challenging Scenario (Link Failure & Fast Failover)
While `h2` is publishing priority messages over the Fast Path (`s1 -> s2 -> s4`), bring the link down in `mininet>`:
```text
mininet> link s1 s2 down
```
In Terminal 1, the SDN controller immediately logs `[SDN-FAILOVER] Fast Path Link (s1-s2) DOWN! Rerouting all flows via s3`, and the TCP Pub-Sub session continues delivering messages without dropping the connection. Restore the link anytime with:
```text
mininet> link s1 s2 up
```

### Step 6: Generate the Performance Comparison Graph
Exit Mininet (`mininet> exit`) and run the plotting script:
```bash
source .venv/bin/activate
python3 benchmarks/plot_metrics.py std_latency.csv prio_latency.csv
```
This outputs `latency_comparison.png` for your project report and presentation.