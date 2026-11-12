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

# Ensure local pubsub module directory is available for import
_pubsub_dir = os.path.dirname(os.path.abspath(__file__))
if _pubsub_dir not in sys.path:
    sys.path.insert(0, _pubsub_dir)

try:
    from protocol import send_msg, recv_msg
except ImportError:
    from pubsub.protocol import send_msg, recv_msg


def print_banner(broker_ip: str, port: int, topic: str, count: int, interval: float):
    is_prio = (port == 5001)
    port_label = f"{port} [FAST PATH]" if is_prio else f"{port} [STANDARD PATH]"
    if os.environ.get("TUI_MODE") == "1":
        print(f" ● [PUBLISHER] Target: {broker_ip}:{port_label} | Topic: {topic} | Plan: {count} msgs ({interval}s interval)")
        return
    port_color = C_GREEN if is_prio else C_YELLOW
    print(f"\n{C_MAGENTA}┌─────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_MAGENTA}│{C_BOLD}{C_WHITE}                    📤 TCP PUB-SUB PUBLISHER                    {C_RESET}{C_MAGENTA}│{C_RESET}")
    print(f"{C_MAGENTA}├─────────────────────────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_MAGENTA}│{C_RESET}  ● Broker Target : {broker_ip}:{port_color}{port_label:<38}{C_RESET}{C_MAGENTA}│{C_RESET}")
    print(f"{C_MAGENTA}│{C_RESET}  ● Target Topic  : {C_CYAN}{topic:<47}{C_RESET}{C_MAGENTA}│{C_RESET}")
    print(f"{C_MAGENTA}│{C_RESET}  ● Publish Plan  : {C_BOLD}{count}{C_RESET} messages (interval: {interval}s){' ' * (28 - len(f'{count}') - len(f'{interval}'))}{C_MAGENTA}│{C_RESET}")
    print(f"{C_MAGENTA}└─────────────────────────────────────────────────────────────────┘{C_RESET}\n")


def run_publisher(broker_ip: str, port: int, topic: str, count: int, interval: float):
    print_banner(broker_ip, port, topic, count, interval)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((broker_ip, port))
        print(f" {C_GREEN}✔ Connected to Broker at {broker_ip}:{port}{C_RESET}\n")
    except Exception as e:
        print(f" {C_RED}✖ Could not connect to Broker ({e}){C_RESET}")
        return

    start_time = time.time()
    delivered_total = 0

    try:
        for seq in range(1, count + 1):
            t_send = time.time()
            payload_data = {
                "type": "PUBLISH",
                "topic": topic,
                "seq": seq,
                "payload": f"Event #{seq} on {topic}",
                "pub_timestamp_ns": time.time_ns()
            }
            send_msg(sock, payload_data)
            ack = recv_msg(sock)
            rtt_ms = (time.time() - t_send) * 1000.0
            delivered = ack.get("delivered_to", 0) if ack else 0
            delivered_total += delivered

            # Progress indicator
            progress = f"[{seq:02d}/{count:02d}]"
            sub_badge = f"{C_GREEN}{delivered} sub(s){C_RESET}" if delivered > 0 else f"{C_YELLOW}0 subs{C_RESET}"
            print(f" {C_BLUE}✉ PUB {progress}{C_RESET} Topic: {C_CYAN}'{topic}'{C_RESET} | Delivered: {sub_badge} | Broker ACK: {C_GREEN}OK{C_RESET} ({rtt_ms:4.1f}ms)")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n {C_YELLOW}■ Publishing interrupted by user.{C_RESET}")
    finally:
        try:
            sock.close()
        except OSError:
            pass

        elapsed = time.time() - start_time
        if os.environ.get("TUI_MODE") == "1":
            print(f" ✔ [SUMMARY] Sent: {seq}/{count} msgs | Deliveries: {delivered_total} client events | Elapsed: {elapsed:.2f}s")
        else:
            print(f"\n{C_CYAN}┌─────────────────────────────────────────────────────────────┐{C_RESET}")
            print(f"{C_CYAN}│{C_BOLD}{C_WHITE}                  📊 PUBLISHING SUMMARY                      {C_RESET}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}├─────────────────────────────────────────────────────────────┤{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Messages Sent     : {C_BOLD}{seq} / {count}{C_RESET} completed{' ' * (30 - len(f'{seq} / {count}'))}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Total Deliveries  : {C_GREEN}{delivered_total} client events{C_RESET}{' ' * (27 - len(f'{delivered_total} client events'))}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Elapsed Time      : {elapsed:.2f} seconds{' ' * (34 - len(f'{elapsed:.2f} seconds'))}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}└─────────────────────────────────────────────────────────────┘{C_RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pub-Sub Publisher Client")
    parser.add_argument("--broker", default="10.0.0.3", help="Broker IP address")
    parser.add_argument("--port", type=int, default=5002, help="5001=High Priority, 5002=Standard")
    parser.add_argument("--topic", default="sensors/temp", help="Topic name")
    parser.add_argument("--count", type=int, default=30, help="Number of messages to publish")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between messages (seconds)")
    args = parser.parse_args()

    run_publisher(args.broker, args.port, args.topic, args.count, args.interval)
