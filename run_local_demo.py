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


def main():
    print("=" * 65)
    print("  SDN-Integrated TCP Pub-Sub: Single-Laptop Standalone Test")
    print("=" * 65)

    broker_script = os.path.join(BASE_DIR, "pubsub", "broker.py")
    sub_script = os.path.join(BASE_DIR, "pubsub", "subscriber.py")
    pub_script = os.path.join(BASE_DIR, "pubsub", "publisher.py")
    plot_script = os.path.join(BASE_DIR, "benchmarks", "plot_metrics.py")

    std_csv = os.path.join(BASE_DIR, "local_std_latency.csv")
    prio_csv = os.path.join(BASE_DIR, "local_prio_latency.csv")
    plot_png = os.path.join(BASE_DIR, "local_latency_plot.png")

    # 1. Start Broker
    print("\n[1/4] Starting TCP Pub-Sub Broker on 127.0.0.1 (:5001 & :5002)...")
    broker_proc = subprocess.Popen(
        [sys.executable, broker_script, "--host", "127.0.0.1", "--priority-port", "5001", "--std-port", "5002"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(0.5)

    try:
        # 2. Start Subscriber 1 (Standard topic on port 5002)
        print("[2/4] Starting Subscriber 1 for topic 'sensors/temp' on port 5002...")
        sub1_proc = subprocess.Popen(
            [sys.executable, sub_script, "--broker", "127.0.0.1", "--port", "5002",
             "--topics", "sensors/temp", "--csv", std_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Start Subscriber 2 (Priority topic on port 5001)
        print("      Starting Subscriber 2 for topic 'alerts/fire' on port 5001...")
        sub2_proc = subprocess.Popen(
            [sys.executable, sub_script, "--broker", "127.0.0.1", "--port", "5001",
             "--topics", "alerts/fire", "--csv", prio_csv],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(0.5)

        # 3. Publish messages
        print("\n[3/4] Publishing messages to Broker...")
        print("      -> Sending 20 messages to 'sensors/temp' on port 5002...")
        subprocess.run(
            [sys.executable, pub_script, "--broker", "127.0.0.1", "--port", "5002",
             "--topic", "sensors/temp", "--count", "20", "--interval", "0.1"],
            check=True
        )

        print("      -> Sending 20 messages to 'alerts/fire' on port 5001...")
        subprocess.run(
            [sys.executable, pub_script, "--broker", "127.0.0.1", "--port", "5001",
             "--topic", "alerts/fire", "--count", "20", "--interval", "0.1"],
            check=True
        )

        time.sleep(0.5)

        # 4. Generate Plot
        print("\n[4/4] Generating latency comparison plot...")
        if os.path.exists(std_csv) and os.path.exists(prio_csv):
            subprocess.run(
                [sys.executable, plot_script, std_csv, prio_csv, plot_png],
                check=True
            )
            print(f"      Saved plot to: {plot_png}")

        print("\n" + "=" * 65)
        print("  TEST COMPLETED SUCCESSFULLY!")
        print(f"  - Standard Latency Log: {std_csv}")
        print(f"  - Priority Latency Log: {prio_csv}")
        print(f"  - Generated Plot:       {plot_png}")
        print("=" * 65)

    finally:
        # Clean up processes
        for p in (sub1_proc, sub2_proc, broker_proc):
            try:
                p.terminate()
                p.wait(timeout=1)
            except Exception:
                p.kill()


if __name__ == "__main__":
    main()
