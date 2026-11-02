"""
benchmarks/plot_metrics.py - Performance Evaluation & Latency Visualization (Member 3)

Generates comparative latency plots from subscriber CSV logs:
- Standard Topic Path (s1 -> s3 -> s4)
- High-Priority Topic Path (s1 -> s2 -> s4)
- Dynamic SDN Promotion Trigger at Sequence 15
"""

import csv
import os
import sys

# Ensure Matplotlib has a writable configuration directory
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_pubsub"

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

    if not os.path.exists(std_csv):
        print(f"[ERROR] Standard latency file '{std_csv}' not found.")
        sys.exit(1)
    if not os.path.exists(prio_csv):
        print(f"[ERROR] Priority latency file '{prio_csv}' not found.")
        sys.exit(1)

    s_seq, s_lat = read_data(std_csv)
    p_seq, p_lat = read_data(prio_csv)

    plt.figure(figsize=(10, 5.5))
    plt.plot(s_seq, s_lat, marker="o", color="#d9534f", linewidth=1.8,
             label="Standard Topic (Port 5002 -> Dynamic SDN Promotion at Seq 15)")
    plt.plot(p_seq, p_lat, marker="s", color="#0275d8", linewidth=1.8,
             label="Priority Topic (Port 5001 -> Fast Path s1-s2-s4)")
    plt.axvline(x=15, color="#5cb85c", linestyle="--", linewidth=2.0,
                label="Broker SDN Webhook Trigger (Seq=15)")

    plt.title("SDN-Integrated TCP Pub-Sub End-to-End Message Latency", fontsize=13, fontweight="bold")
    plt.xlabel("Message Sequence Number", fontsize=11)
    plt.ylabel("End-to-End Delivery Latency (ms)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    print(f"[BENCHMARK] Successfully generated and saved plot to {out_png}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 benchmarks/plot_metrics.py <std_latency.csv> <prio_latency.csv> [output.png]")
        sys.exit(1)
    output_path = sys.argv[3] if len(sys.argv) >= 4 else "latency_comparison.png"
    plot_latency(sys.argv[1], sys.argv[2], output_path)
