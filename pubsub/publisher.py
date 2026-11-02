"""
pubsub/publisher.py - TCP Publisher Client (Member 1)

Publishes sequence-numbered messages with nanosecond timestamps to the broker
over TCP, awaits delivery confirmation ACKs, and controls sending rate.
"""

import argparse
import os
import socket
import sys
import time

# Ensure local pubsub module directory is available for import
_pubsub_dir = os.path.dirname(os.path.abspath(__file__))
if _pubsub_dir not in sys.path:
    sys.path.insert(0, _pubsub_dir)

try:
    from protocol import send_msg, recv_msg
except ImportError:
    from pubsub.protocol import send_msg, recv_msg


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
            delivered = ack.get("delivered_to") if ack else 0
            print(f"[PUBLISHED] Seq={seq} | Topic='{topic}' | Delivered={delivered} subs")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[PUBLISHER] Stopped.")
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pub-Sub Publisher Client")
    parser.add_argument("--broker", default="10.0.0.3", help="Broker IP address")
    parser.add_argument("--port", type=int, default=5002, help="5001=High Priority, 5002=Standard")
    parser.add_argument("--topic", default="sensors/temp", help="Topic name")
    parser.add_argument("--count", type=int, default=30, help="Number of messages to publish")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between messages (seconds)")
    args = parser.parse_args()

    run_publisher(args.broker, args.port, args.topic, args.count, args.interval)
