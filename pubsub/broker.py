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
            print(f"[SDN-HOOK] Triggered SDN policy '{action}' for topic '{topic}' (host {client_ip}) -> Status {resp.status_code}")
        except Exception as e:
            print(f"[SDN-HOOK] Controller notification skipped: {e}")

    def handle_client(self, conn: socket.socket, addr, listen_port: int):
        client_ip, client_port = addr
        traffic_class = "HIGH_PRIORITY" if listen_port == self.priority_port else "STANDARD"
        print(f"[CONNECT] {client_ip}:{client_port} on port {listen_port} ({traffic_class})")

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
            try:
                conn.close()
            except OSError:
                pass
            print(f"[DISCONNECT] {client_ip}:{client_port}")

    def start_listener(self, port: int):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, port))
        server.listen(128)
        with self.lock:
            self.server_sockets.append(server)
        print(f"[BROKER] Listening on {self.host}:{port}")
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
        t1 = threading.Thread(target=self.start_listener, args=(self.priority_port,), daemon=True)
        t2 = threading.Thread(target=self.start_listener, args=(self.std_port,), daemon=True)
        t1.start()
        t2.start()
        print("[BROKER] Pub-Sub Broker running. Press Ctrl+C to stop.")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[BROKER] Shutting down.")
            self.running = False
            with self.lock:
                for s in self.server_sockets:
                    try:
                        s.close()
                    except OSError:
                        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Port Concurrent Pub-Sub Broker")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--priority-port", type=int, default=5001, help="High-Priority port")
    parser.add_argument("--std-port", type=int, default=5002, help="Standard port")
    parser.add_argument("--sdn-url", default="http://127.0.0.1:8080", help="SDN Controller REST API base URL")
    args = parser.parse_args()

    broker = PubSubBroker(args.host, args.priority_port, args.std_port, args.sdn_url)
    broker.run()
