"""
pubsub/subscriber.py - Concurrent TCP Subscriber with Latency Logging (Member 1)

Subscribes to one or more topics over TCP, receives messages from the broker,
measures one-way end-to-end delivery latency using nanosecond timestamps,
and writes benchmark logs to CSV for performance evaluation.
"""

import argparse
import csv
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
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pub-Sub Subscriber Client")
    parser.add_argument("--broker", default="10.0.0.3", help="Broker IP address")
    parser.add_argument("--port", type=int, default=5002, help="5001 for Priority, 5002 for Standard")
    parser.add_argument("--topics", nargs="+", default=["sensors/temp"], help="Topics to subscribe")
    parser.add_argument("--csv", default="", help="Optional CSV output path for latency logs")
    args = parser.parse_args()

    run_subscriber(args.broker, args.port, args.topics, args.csv)
