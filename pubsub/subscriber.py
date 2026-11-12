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


def print_banner(broker_ip: str, port: int, topics: list, csv_file: str):
    is_prio = (port == 5001)
    port_label = f"{port} [FAST PATH]" if is_prio else f"{port} [STANDARD PATH]"
    if os.environ.get("TUI_MODE") == "1":
        print(f" ● [SUBSCRIBER] Connected to {broker_ip}:{port_label} | Topics: {', '.join(topics)}")
        return
    port_color = C_GREEN if is_prio else C_YELLOW
    print(f"\n{C_BLUE}┌─────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_BLUE}│{C_BOLD}{C_WHITE}                    📥 TCP PUB-SUB SUBSCRIBER                    {C_RESET}{C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}├─────────────────────────────────────────────────────────────────┤{C_RESET}")
    print(f"{C_BLUE}│{C_RESET}  ● Broker Target : {broker_ip}:{port_color}{port_label:<38}{C_RESET}{C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}│{C_RESET}  ● Topics        : {C_CYAN}{', '.join(topics):<47}{C_RESET}{C_BLUE}│{C_RESET}")
    csv_label = csv_file if csv_file else "(stdout only)"
    print(f"{C_BLUE}│{C_RESET}  ● Latency CSV   : {C_MAGENTA}{csv_label:<47}{C_RESET}{C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}└─────────────────────────────────────────────────────────────────┘{C_RESET}\n")


def print_table_header():
    if os.environ.get("TUI_MODE") == "1":
        print("  SEQ │ TOPIC            │ TRAFFIC CLASS   │ LATENCY   │ PAYLOAD")
        print(" ─────┼──────────────────┼─────────────────┼───────────┼──────────────────────────────")
        return
    print(f"{C_DIM}┌───────┬──────────────────┬─────────────────┬──────────────┬───────────────────────────────┐{C_RESET}")
    print(f"{C_BOLD}│  SEQ  │ TOPIC            │ TRAFFIC CLASS   │ LATENCY (ms) │ PAYLOAD                       │{C_RESET}")
    print(f"{C_DIM}├───────┼──────────────────┼─────────────────┼──────────────┼───────────────────────────────┤{C_RESET}")


def run_subscriber(broker_ip: str, port: int, topics: list, csv_file: str):
    print_banner(broker_ip, port, topics, csv_file)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((broker_ip, port))
        print(f" {C_GREEN}✔ Connected to Broker at {broker_ip}:{port}{C_RESET}")
    except Exception as e:
        print(f" {C_RED}✖ Failed to connect to Broker ({e}){C_RESET}")
        return

    for topic in topics:
        send_msg(sock, {"type": "SUBSCRIBE", "topic": topic})
        ack = recv_msg(sock)
        status = ack.get("status") if ack else "NO_ACK"
        print(f" {C_CYAN}✔ Subscribed to '{topic}' -> Broker ACK: {C_GREEN}{status}{C_RESET}")

    print()
    print_table_header()

    csv_writer = None
    f_out = None
    if csv_file:
        f_out = open(csv_file, "w", newline="")
        csv_writer = csv.writer(f_out)
        csv_writer.writerow(["seq", "topic", "traffic_class", "latency_ms", "timestamp"])

    latencies = []
    msg_count = 0

    try:
        while True:
            msg = recv_msg(sock)
            if not msg:
                print(f"{C_DIM}├───────┴──────────────────┴─────────────────┴──────────────┴───────────────────────────────┤{C_RESET}")
                print(f" {C_YELLOW}⚠ Broker closed connection.{C_RESET}")
                break
            if msg.get("type") == "MESSAGE":
                msg_count += 1
                now_ns = time.time_ns()
                pub_ns = msg.get("pub_timestamp_ns", now_ns)
                latency_ms = (now_ns - pub_ns) / 1_000_000.0
                latencies.append(latency_ms)

                seq = msg.get("seq", 0)
                topic = msg.get("topic", "unknown")
                t_class = msg.get("traffic_class", "STANDARD")
                payload = msg.get("payload", "")

                # Formatting helpers
                if os.environ.get("TUI_MODE") == "1":
                    if latency_ms < 15.0:
                        lat_str = f"{C_GREEN}{latency_ms:6.2f} ms [FAST]{C_RESET}"
                        class_badge = f"{C_GREEN}FAST_PATH{C_RESET}"
                    else:
                        lat_str = f"{C_YELLOW}{latency_ms:6.2f} ms [STD ]{C_RESET}"
                        class_badge = f"{C_YELLOW}STANDARD {C_RESET}"
                    seq_fmt = f"#{seq:<3}"
                    top_fmt = (topic[:16] + "..") if len(topic) > 16 else f"{topic:<16}"
                    pay_fmt = (payload[:26] + "..") if len(payload) > 26 else f"{payload:<28}"
                    print(f"  {seq_fmt} │ {top_fmt} │ {class_badge}       │ {lat_str} │ {pay_fmt}")
                else:
                    if latency_ms < 15.0:
                        lat_str = f"{C_GREEN}{latency_ms:6.2f} ms 🚀{C_RESET}"
                        class_badge = f"{C_GREEN}FAST_PATH{C_RESET}"
                    else:
                        lat_str = f"{C_YELLOW}{latency_ms:6.2f} ms ⚠️ {C_RESET}"
                        class_badge = f"{C_YELLOW}STANDARD {C_RESET}"

                    seq_formatted = f"#{seq:<4}"
                    topic_truncated = (topic[:16] + "..") if len(topic) > 16 else f"{topic:<16}"
                    payload_truncated = (payload[:27] + "..") if len(payload) > 27 else f"{payload:<29}"

                    print(f"│ {seq_formatted} │ {topic_truncated} │ {class_badge}       │ {lat_str} │ {payload_truncated} │")

                if csv_writer:
                    csv_writer.writerow([seq, topic, t_class, f"{latency_ms:.3f}", time.time()])
                    f_out.flush()

    except KeyboardInterrupt:
        if os.environ.get("TUI_MODE") != "1":
            print(f"\n{C_DIM}├───────┴──────────────────┴─────────────────┴──────────────┴───────────────────────────────┤{C_RESET}")
        print(f" {C_YELLOW}■ Disconnecting subscriber...{C_RESET}")
    finally:
        if os.environ.get("TUI_MODE") != "1":
            print(f"{C_DIM}└───────────────────────────────────────────────────────────────────────────────────────────┘{C_RESET}")
        if f_out:
            f_out.close()
        try:
            sock.close()
        except OSError:
            pass

        # Print Summary Card
        if latencies:
            avg_lat = sum(latencies) / len(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
            print(f"\n{C_CYAN}┌─────────────────────────────────────────────────────────────┐{C_RESET}")
            print(f"{C_CYAN}│{C_BOLD}{C_WHITE}                  📊 SUBSCRIBER SUMMARY                      {C_RESET}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}├─────────────────────────────────────────────────────────────┤{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Total Received  : {C_BOLD}{msg_count}{C_RESET}{' ' * (37 - len(str(msg_count)))}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Average Latency : {C_GREEN}{avg_lat:.2f} ms{C_RESET}{' ' * (35 - len(f'{avg_lat:.2f} ms'))}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│{C_RESET}  ● Min / Max       : {min_lat:.2f} ms / {max_lat:.2f} ms{' ' * (30 - len(f'{min_lat:.2f} ms / {max_lat:.2f} ms'))}{C_CYAN}│{C_RESET}")
            if csv_file:
                print(f"{C_CYAN}│{C_RESET}  ● Saved Log       : {C_MAGENTA}{csv_file:<38}{C_RESET}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}└─────────────────────────────────────────────────────────────┘{C_RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pub-Sub Subscriber Client")
    parser.add_argument("--broker", default="10.0.0.3", help="Broker IP address")
    parser.add_argument("--port", type=int, default=5002, help="5001 for Priority, 5002 for Standard")
    parser.add_argument("--topics", nargs="+", default=["sensors/temp"], help="Topics to subscribe")
    parser.add_argument("--csv", default="", help="Optional CSV output path for latency logs")
    args = parser.parse_args()

    run_subscriber(args.broker, args.port, args.topics, args.csv)
