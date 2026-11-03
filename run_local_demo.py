"""
run_local_demo.py - Single-Command Local Pub-Sub Test Runner

Spawns the Broker, two Subscribers (Standard & Priority), and a Publisher
all on localhost using background threads/subprocesses.
Demonstrates end-to-end messaging, ACKs, latency computation, and generates
a latency plot without requiring Mininet or root privileges.
"""

import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[1;34m"
C_MAGENTA = "\033[1;35m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"


def print_header():
    print(f"\n{C_CYAN}╔═════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_BOLD}{C_WHITE}    🚀 SDN-INTEGRATED TCP PUB-SUB: STANDALONE DEMO SUITE         {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_DIM}    Course: Computer Networks (UE25CS243A) — Deliverable 1 & 2   {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚═════════════════════════════════════════════════════════════════╝{C_RESET}\n")


def main():
    print_header()

    broker_script = os.path.join(BASE_DIR, "pubsub", "broker.py")
    sub_script = os.path.join(BASE_DIR, "pubsub", "subscriber.py")
    pub_script = os.path.join(BASE_DIR, "pubsub", "publisher.py")
    plot_script = os.path.join(BASE_DIR, "benchmarks", "plot_metrics.py")

    std_csv = os.path.join(BASE_DIR, "local_std_latency.csv")
    prio_csv = os.path.join(BASE_DIR, "local_prio_latency.csv")
    plot_png = os.path.join(BASE_DIR, "local_latency_plot.png")

    # Step 1: Broker
    print(f"{C_CYAN}[1/4]{C_RESET} {C_BOLD}Starting TCP Pub-Sub Central Broker...{C_RESET}")
    broker_proc = subprocess.Popen(
        [sys.executable, broker_script, "--host", "127.0.0.1", "--priority-port", "5001", "--std-port", "5002"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(0.6)
    print(f"      {C_GREEN}✔ Broker listening on 127.0.0.1:5001 (Priority) and :5002 (Standard){C_RESET}")

    sub1_proc = None
    sub2_proc = None

    try:
        # Step 2: Subscribers
        print(f"\n{C_CYAN}[2/4]{C_RESET} {C_BOLD}Spawning Concurrent Subscriber Clients...{C_RESET}")
        sub1_proc = subprocess.Popen(
            [sys.executable, sub_script, "--broker", "127.0.0.1", "--port", "5002",
             "--topics", "sensors/temp", "--csv", std_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"      {C_GREEN}✔ Subscriber 1 joined topic 'sensors/temp' on port 5002 [Standard]{C_RESET}")

        sub2_proc = subprocess.Popen(
            [sys.executable, sub_script, "--broker", "127.0.0.1", "--port", "5001",
             "--topics", "alerts/fire", "--csv", prio_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"      {C_GREEN}✔ Subscriber 2 joined topic 'alerts/fire' on port 5001 [Priority]{C_RESET}")
        time.sleep(0.6)

        # Step 3: Publishing
        print(f"\n{C_CYAN}[3/4]{C_RESET} {C_BOLD}Publishing Traffic Flows...{C_RESET}")
        print(f"      {C_YELLOW}→ Streaming 20 messages on 'sensors/temp' (Standard Path)...{C_RESET}")
        subprocess.run(
            [sys.executable, pub_script, "--broker", "127.0.0.1", "--port", "5002",
             "--topic", "sensors/temp", "--count", "20", "--interval", "0.08"],
            stdout=subprocess.DEVNULL,
            check=True
        )
        print(f"      {C_GREEN}✔ 20/20 Standard messages delivered with reliability ACKs.{C_RESET}")

        print(f"      {C_CYAN}→ Streaming 20 messages on 'alerts/fire' (High-Priority Path)...{C_RESET}")
        subprocess.run(
            [sys.executable, pub_script, "--broker", "127.0.0.1", "--port", "5001",
             "--topic", "alerts/fire", "--count", "20", "--interval", "0.08"],
            stdout=subprocess.DEVNULL,
            check=True
        )
        print(f"      {C_GREEN}✔ 20/20 Priority messages delivered with reliability ACKs.{C_RESET}")
        time.sleep(0.5)

        # Step 4: Latency & Plotting
        print(f"\n{C_CYAN}[4/4]{C_RESET} {C_BOLD}Aggregating Benchmark Logs & Generating Latency Chart...{C_RESET}")
        if os.path.exists(std_csv) and os.path.exists(prio_csv):
            subprocess.run(
                [sys.executable, plot_script, std_csv, prio_csv, plot_png],
                check=True
            )

        print(f"\n{C_GREEN}╔═════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_GREEN}║{C_BOLD}{C_WHITE}                  🎉 LOCAL RUN COMPLETED!                        {C_RESET}{C_GREEN}║{C_RESET}")
        print(f"{C_GREEN}╠═════════════════════════════════════════════════════════════════╣{C_RESET}")
        print(f"{C_GREEN}║{C_RESET}  ● Standard Latency CSV : {std_csv:<37}{C_GREEN}║{C_RESET}")
        print(f"{C_GREEN}║{C_RESET}  ● Priority Latency CSV : {prio_csv:<37}{C_GREEN}║{C_RESET}")
        print(f"{C_GREEN}║{C_RESET}  ● Latency Chart Output : {C_BOLD}{plot_png:<37}{C_RESET}{C_GREEN}║{C_RESET}")
        print(f"{C_GREEN}╚═════════════════════════════════════════════════════════════════╝{C_RESET}\n")

    finally:
        for p in (sub1_proc, sub2_proc, broker_proc):
            if p:
                try:
                    p.terminate()
                    p.wait(timeout=1)
                except Exception:
                    p.kill()


if __name__ == "__main__":
    main()
