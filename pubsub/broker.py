"""
pubsub/broker.py - Multi-Port Concurrent TCP Broker (Member 1 & 3)

Centralized pub-sub broker listening concurrently on two TCP ports:
- High-Priority Port (default: 5001): Direct low-latency path
- Standard Port (default: 5002): Standard path with dynamic SDN promotion

Integrates with SDN Controller via REST webhook when standard topic volume
crosses the burst threshold (>= 15 messages).
"""

import argparse
import os
import socket
import sys
import threading
import time
from collections import defaultdict

# ANSI Terminal Styling
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RED = "\033[1;31m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[1;34m"
C_MAGENTA = "\033[1;35m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"
BG_BLUE = "\033[44m"
BG_GREEN = "\033[42m"
BG_MAGENTA = "\033[45m"

# Ensure local pubsub module directory is available for import
_pubsub_dir = os.path.dirname(os.path.abspath(__file__))
if _pubsub_dir not in sys.path:
    sys.path.insert(0, _pubsub_dir)

try:
    from protocol import send_msg, recv_msg
except ImportError:
    from pubsub.protocol import send_msg, recv_msg

try:
    import requests
except ImportError:
    requests = None


def print_banner(host: str, prio_port: int, std_port: int, sdn_url: str):
    if os.environ.get("TUI_MODE") == "1":
        print(f" ● [BROKER] Priority Port: {host}:{prio_port} [FAST PATH] | Standard Port: {host}:{std_port} [STANDARD PATH]")
        print(f" ● [SDN-POLICY] Webhook URL: {sdn_url} (Promotion threshold: >= 15 msgs)")
        return
    print(f"\n{C_CYAN}┌─────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}│{C_BOLD}{C_WHITE}            📡 TCP PUBLISH–SUBSCRIBE CENTRAL BROKER              {C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_DIM}     Course: Computer Networks (UE25CS243A) — Project #9          {C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}├─────────────────────────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}● Priority Port   :{C_RESET} {host}:{prio_port} {C_GREEN}[FAST PATH]{C_RESET}{' ' * 19}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_YELLOW}● Standard Port   :{C_RESET} {host}:{std_port} {C_YELLOW}[STANDARD PATH]{C_RESET}{' ' * 15}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_BLUE}● SDN Webhook URL :{C_RESET} {sdn_url:<37}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_MAGENTA}● Burst Promotion :{C_RESET} >= 15 msgs triggers Fast Path Promotion    {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}└─────────────────────────────────────────────────────────────────┘{C_RESET}\n")


class PubSubBroker:
    def __init__(self, host: str, priority_port: int, std_port: int, sdn_url: str):
        self.host = host
        self.priority_port = priority_port
        self.std_port = std_port
        self.sdn_url = sdn_url

        self.lock = threading.Lock()
        self.subscriptions = defaultdict(set)
        self.topic_counts = defaultdict(int)
        self.promoted_topics = set()
        self.server_sockets = []
        self.running = True

    def notify_sdn_controller(self, topic: str, action: str, client_ip: str):
        """Sends an application-level event to the SDN controller REST API."""
        if not self.sdn_url or requests is None:
            return
        try:
            payload = {
                "topic": topic,
                "action": action,
                "client_ip": client_ip,
                "timestamp": time.time()
            }
            resp = requests.post(f"{self.sdn_url}/sdn/policy", json=payload, timeout=0.5)
            print(f" {C_BOLD}{C_MAGENTA}⚡ [SDN-HOOK]{C_RESET} Triggered policy {C_YELLOW}'{action}'{C_RESET} for topic {C_CYAN}'{topic}'{C_RESET} (host {client_ip}) -> Status {C_GREEN}{resp.status_code} OK{C_RESET}")
        except Exception as e:
            print(f" {C_DIM}[SDN-HOOK] Controller notification skipped ({e}){C_RESET}")

    def handle_client(self, conn: socket.socket, addr, listen_port: int):
        client_ip, client_port = addr
        is_prio = (listen_port == self.priority_port)
        badge = f"{C_GREEN}[HIGH_PRIO :5001]{C_RESET}" if is_prio else f"{C_YELLOW}[STANDARD  :5002]{C_RESET}"
        print(f" {C_CYAN}▶ [CONNECT]{C_RESET} {client_ip}:{client_port} via {badge}")

        try:
            while self.running:
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
                    print(f" {C_GREEN}✓ [SUBSCRIBE]{C_RESET} {client_ip} joined {C_CYAN}'{topic}'{C_RESET} (Active subs on topic: {C_BOLD}{sub_count}{C_RESET})")

                elif msg_type == "UNSUBSCRIBE":
                    with self.lock:
                        self.subscriptions[topic].discard(conn)
                    send_msg(conn, {"type": "UNSUB_ACK", "topic": topic, "status": "OK"})
                    print(f" {C_YELLOW}✗ [UNSUBSCRIBE]{C_RESET} {client_ip} left {C_CYAN}'{topic}'{C_RESET}")

                elif msg_type == "PUBLISH":
                    with self.lock:
                        self.topic_counts[topic] += 1
                        count = self.topic_counts[topic]
                        subscribers = list(self.subscriptions.get(topic, []))

                    # Dynamic Socket-SDN Trigger:
                    if count >= 15 and topic not in self.promoted_topics:
                        self.promoted_topics.add(topic)
                        print(f"\n {C_BOLD}{C_MAGENTA}🚀 [BURST-DETECTED]{C_RESET} Topic {C_CYAN}'{topic}'{C_RESET} reached {C_BOLD}{count}{C_RESET} msgs! Triggering SDN Fast Path...")
                        threading.Thread(
                            target=self.notify_sdn_controller,
                            args=(topic, "PROMOTE_FAST_PATH", client_ip),
                            daemon=True
                        ).start()

                    out_msg = {
                        "type": "MESSAGE",
                        "topic": topic,
                        "seq": msg.get("seq", 0),
                        "payload": msg.get("payload", ""),
                        "pub_timestamp_ns": msg.get("pub_timestamp_ns", time.time_ns()),
                        "traffic_class": "HIGH_PRIORITY" if is_prio else "STANDARD"
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

                    delivered = len(subscribers) - len(dead_subs)
                    send_msg(conn, {
                        "type": "PUB_ACK",
                        "seq": msg.get("seq", 0),
                        "delivered_to": delivered
                    })
                    seq_str = f"#{msg.get('seq', 0):<3}"
                    print(f" {C_BLUE}✉ [PUBLISH {seq_str}]{C_RESET} Topic: {C_CYAN}'{topic}'{C_RESET} | Delivered: {C_BOLD}{delivered}{C_RESET} subs | ACK returned")

        except Exception as e:
            print(f" {C_RED}✖ [ERROR]{C_RESET} Client {client_ip}:{client_port}: {e}")
        finally:
            with self.lock:
                for subs in self.subscriptions.values():
                    subs.discard(conn)
            try:
                conn.close()
            except OSError:
                pass
            print(f" {C_DIM}■ [DISCONNECT] {client_ip}:{client_port}{C_RESET}")

    def start_listener(self, port: int):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, port))
        server.listen(128)
        with self.lock:
            self.server_sockets.append(server)
        while self.running:
            try:
                conn, addr = server.accept()
                t = threading.Thread(target=self.handle_client, args=(conn, addr, port), daemon=True)
                t.start()
            except OSError:
                break
        try:
            server.close()
        except OSError:
            pass

    def run(self):
        print_banner(self.host, self.priority_port, self.std_port, self.sdn_url)
        t1 = threading.Thread(target=self.start_listener, args=(self.priority_port,), daemon=True)
        t2 = threading.Thread(target=self.start_listener, args=(self.std_port,), daemon=True)
        t1.start()
        t2.start()
        print(f" {C_GREEN}● Broker active and listening. Press {C_BOLD}Ctrl+C{C_RESET}{C_GREEN} to stop.{C_RESET}\n")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}■ Shutting down Broker gracefully...{C_RESET}")
            self.running = False
            with self.lock:
                for s in self.server_sockets:
                    try:
                        s.close()
                    except OSError:
                        pass
            print(f"{C_GREEN}✔ Broker stopped.{C_RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Port Concurrent Pub-Sub Broker")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--priority-port", type=int, default=5001, help="High-Priority port")
    parser.add_argument("--std-port", type=int, default=5002, help="Standard port")
    parser.add_argument("--sdn-url", default="http://127.0.0.1:8080", help="SDN Controller REST API base URL")
    args = parser.parse_args()

    broker = PubSubBroker(args.host, args.priority_port, args.std_port, args.sdn_url)
    broker.run()
