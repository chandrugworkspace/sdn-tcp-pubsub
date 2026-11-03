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
        print(f" {C_YELLOW}⚠ Standard latency file '{std_csv}' not found.{C_RESET}")
        sys.exit(1)
    if not os.path.exists(prio_csv):
        print(f" {C_YELLOW}⚠ Priority latency file '{prio_csv}' not found.{C_RESET}")
        sys.exit(1)

    s_seq, s_lat = read_data(std_csv)
    p_seq, p_lat = read_data(prio_csv)

    if not s_lat or not p_lat:
        print(" ⚠ CSV files contain no latency data.")
        return

    # Statistical computation
    s_avg = sum(s_lat) / len(s_lat)
    p_avg = sum(p_lat) / len(p_lat)
    s_min, s_max = min(s_lat), max(s_lat)
    p_min, p_max = min(p_lat), max(p_lat)

    # Plot generation
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.figure(figsize=(10, 5.5))
    plt.plot(s_seq, s_lat, marker="o", color="#d9534f", linewidth=2.0, markersize=5,
             label="Standard Path (s1->s3->s4) → SDN Promoted at Seq #15")
    plt.plot(p_seq, p_lat, marker="s", color="#0275d8", linewidth=2.0, markersize=5,
             label="High-Priority Path (s1->s2->s4) [Fast Path]")
    plt.axvline(x=15, color="#5cb85c", linestyle="--", linewidth=2.2,
                label="Broker Dynamic SDN Webhook Trigger (Seq=15)")

    plt.title("SDN-Integrated TCP Pub-Sub End-to-End Latency Evaluation", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Message Sequence Number", fontsize=11, fontweight="bold")
    plt.ylabel("One-Way Delivery Latency (ms)", fontsize=11, fontweight="bold")
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(loc="upper right", frameon=True, fontsize=10)
    plt.tight_layout()
    plt.savefig(out_png, dpi=250)

    # Terminal Statistical Card
    print(f"\n{C_CYAN}┌─────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}│{C_BOLD}{C_WHITE}                 📈 LATENCY PERFORMANCE METRICS                  {C_RESET}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}├──────────────────────────────┬──────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}│{C_BOLD} Metric                       {C_CYAN}│{C_BOLD} Observed Values                  {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}├──────────────────────────────┼──────────────────────────────────┤{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  Standard Flow Average       │ {C_YELLOW}{s_avg:6.2f} ms{C_RESET} (min: {s_min:.1f}, max: {s_max:.1f}){' ' * (10 - len(f'{s_min:.1f}') - len(f'{s_max:.1f}'))}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  Priority Flow Average       │ {C_GREEN}{p_avg:6.2f} ms{C_RESET} (min: {p_min:.1f}, max: {p_max:.1f}){' ' * (10 - len(f'{p_min:.1f}') - len(f'{p_max:.1f}'))}{C_CYAN}│{C_RESET}")
    diff_pct = ((s_avg - p_avg) / s_avg) * 100 if s_avg > 0 else 0
    print(f"{C_CYAN}│{C_RESET}  Fast Path Latency Reduction │ {C_BOLD}{C_GREEN}{diff_pct:6.1f} % faster{C_RESET}{' ' * 19}{C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  Output Plot Image Saved     │ {C_MAGENTA}{out_png:<32}{C_RESET} {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}└──────────────────────────────┴──────────────────────────────────┘{C_RESET}\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 benchmarks/plot_metrics.py <std_latency.csv> <prio_latency.csv> [output.png]")
        sys.exit(1)
    output_path = sys.argv[3] if len(sys.argv) >= 4 else "latency_comparison.png"
    plot_latency(sys.argv[1], sys.argv[2], output_path)
