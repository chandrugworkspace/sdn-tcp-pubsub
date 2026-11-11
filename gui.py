#!/usr/bin/env python3
"""
gui.py - Minimal Tkinter Desktop GUI for TCP Pub-Sub Messaging System

A clean, non-AI styled native GUI that runs the 3 terminals (Broker, Subscriber,
Publisher) in side-by-side terminal panes with standard student-project controls.
"""

import os
import queue
import subprocess
import sys
import threading
import time

try:
    import tkinter as tk
    from tkinter import scrolledtext, ttk, messagebox
except ImportError as e:
    print("\n" + "=" * 60)
    print("❌ Tkinter is not installed on this Python environment.")
    print("=" * 60)
    print("To install Tkinter:")
    print("  • On Ubuntu / Debian : sudo apt install python3-tk")
    print("  • On Arch / CachyOS  : sudo pacman -S tk")
    print("=" * 60 + "\n")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PubSubTkinterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SDN TCP Pub-Sub Messaging System - UE25CS243A")
        self.root.geometry("1100x680")
        self.root.minsize(950, 600)

        # Process handles
        self.broker_proc = None
        self.sub_proc = None
        self.pub_proc = None

        # Queue for thread-safe GUI updates
        self.msg_queue = queue.Queue()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(50, self._process_queue)

    def _build_ui(self):
        # 1. Top Title Frame
        top_frame = tk.Frame(self.root, bg="#e0e0e0", relief=tk.RAISED, bd=1, pady=6)
        top_frame.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            top_frame,
            text="TCP Publish-Subscribe Messaging System with SDN Flow Control",
            font=("Arial", 12, "bold"),
            bg="#e0e0e0"
        )
        title_label.pack(side=tk.LEFT, padx=12)

        subtitle_label = tk.Label(
            top_frame,
            text="Course: Computer Networks (UE25CS243A) | Project #9",
            font=("Arial", 9),
            bg="#e0e0e0",
            fg="#555555"
        )
        subtitle_label.pack(side=tk.RIGHT, padx=12)

        # 2. Main 3-Column Panes
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Pane 1: Broker
        self.broker_frame = tk.LabelFrame(main_paned, text=" 1. Central Broker (Ports 5001 & 5002) ", font=("Arial", 9, "bold"), padx=6, pady=6)
        main_paned.add(self.broker_frame, minsize=280)
        self._build_broker_controls(self.broker_frame)

        # Pane 2: Subscriber
        self.sub_frame = tk.LabelFrame(main_paned, text=" 2. Subscriber Client ", font=("Arial", 9, "bold"), padx=6, pady=6)
        main_paned.add(self.sub_frame, minsize=320)
        self._build_sub_controls(self.sub_frame)

        # Pane 3: Publisher
        self.pub_frame = tk.LabelFrame(main_paned, text=" 3. Publisher Client ", font=("Arial", 9, "bold"), padx=6, pady=6)
        main_paned.add(self.pub_frame, minsize=320)
        self._build_pub_controls(self.pub_frame)

        # 3. Bottom Status Bar
        status_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=1, bg="#f5f5f5")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

        self.status_var = tk.StringVar(value="Status: Ready | Broker: Stopped | Subscriber: Idle | Publisher: Idle")
        status_lbl = tk.Label(status_frame, textvariable=self.status_var, font=("Arial", 8), bg="#f5f5f5", anchor=tk.W)
        status_lbl.pack(side=tk.LEFT, padx=6, pady=2)

        clear_btn = tk.Button(status_frame, text="Clear All Terminals", font=("Arial", 8), command=self.clear_all_terminals)
        clear_btn.pack(side=tk.RIGHT, padx=6, pady=2)

    # ----------------------------------------------------------------------
    # PANE 1: BROKER
    # ----------------------------------------------------------------------
    def _build_broker_controls(self, parent):
        ctrl_frame = tk.Frame(parent)
        ctrl_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_start_broker = tk.Button(ctrl_frame, text="Start Broker", bg="#d4edda", fg="#155724", font=("Arial", 9, "bold"), command=self.start_broker)
        self.btn_start_broker.pack(side=tk.LEFT, padx=2)

        self.btn_stop_broker = tk.Button(ctrl_frame, text="Stop Broker", bg="#f8d7da", fg="#721c24", font=("Arial", 9), state=tk.DISABLED, command=self.stop_broker)
        self.btn_stop_broker.pack(side=tk.LEFT, padx=2)

        lbl_info = tk.Label(parent, text="Fast Path: Port 5001 | Std Path: Port 5002\nBurst threshold >= 15 msgs triggers SDN policy", font=("Arial", 8), fg="#666666", justify=tk.LEFT)
        lbl_info.pack(anchor=tk.W, pady=(0, 4))

        # Terminal Console
        self.broker_txt = scrolledtext.ScrolledText(parent, bg="black", fg="#00ff66", insertbackground="white", font=("Courier", 8), wrap=tk.WORD)
        self.broker_txt.pack(fill=tk.BOTH, expand=True)

    def start_broker(self):
        if self.broker_proc is not None:
            return

        cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "broker.py"), "--host", "127.0.0.1", "--priority-port", "5001", "--std-port", "5002"]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.broker_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
            self.btn_start_broker.config(state=tk.DISABLED)
            self.btn_stop_broker.config(state=tk.NORMAL)
            self.status_var.set("Status: Broker Running on ports 5001 & 5002")

            threading.Thread(target=self._stream_output, args=(self.broker_proc, self.broker_txt, "broker"), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Could not start Broker: {e}")

    def stop_broker(self):
        if self.broker_proc:
            try:
                self.broker_proc.terminate()
            except Exception:
                pass
            self.broker_proc = None
        self.btn_start_broker.config(state=tk.NORMAL)
        self.btn_stop_broker.config(state=tk.DISABLED)
        self.append_terminal(self.broker_txt, "\n[BROKER STOPPED BY USER]\n")
        self.status_var.set("Status: Broker Stopped")

    # ----------------------------------------------------------------------
    # PANE 2: SUBSCRIBER
    # ----------------------------------------------------------------------
    def _build_sub_controls(self, parent):
        top_ctrl = tk.Frame(parent)
        top_ctrl.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top_ctrl, text="Topic:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, padx=2)
        self.sub_topic_entry = tk.Entry(top_ctrl, font=("Arial", 9), width=16)
        self.sub_topic_entry.insert(0, "sensors/temp")
        self.sub_topic_entry.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)

        tk.Label(top_ctrl, text="Port:", font=("Arial", 9)).grid(row=0, column=2, sticky=tk.W, padx=2)
        self.sub_port_var = tk.StringVar(value="5002")
        port_combo = ttk.Combobox(top_ctrl, textvariable=self.sub_port_var, values=["5002", "5001"], width=6, state="readonly")
        port_combo.grid(row=0, column=3, padx=2, pady=2)

        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=(0, 4))

        self.btn_sub = tk.Button(btn_row, text="Subscribe", bg="#cce5ff", fg="#004085", font=("Arial", 9, "bold"), command=self.start_subscriber)
        self.btn_sub.pack(side=tk.LEFT, padx=2)

        self.btn_unsub = tk.Button(btn_row, text="Stop Subscriber", bg="#f8d7da", fg="#721c24", font=("Arial", 9), state=tk.DISABLED, command=self.stop_subscriber)
        self.btn_unsub.pack(side=tk.LEFT, padx=2)

        # Quick topic buttons
        tk.Button(btn_row, text="Temp", font=("Arial", 8), command=lambda: self._set_sub_topic("sensors/temp", "5002")).pack(side=tk.RIGHT, padx=1)
        tk.Button(btn_row, text="Fire Alert", font=("Arial", 8), command=lambda: self._set_sub_topic("alerts/fire", "5001")).pack(side=tk.RIGHT, padx=1)

        self.sub_txt = scrolledtext.ScrolledText(parent, bg="black", fg="#ffffff", insertbackground="white", font=("Courier", 8), wrap=tk.WORD)
        self.sub_txt.pack(fill=tk.BOTH, expand=True)

    def _set_sub_topic(self, topic, port):
        self.sub_topic_entry.delete(0, tk.END)
        self.sub_topic_entry.insert(0, topic)
        self.sub_port_var.set(port)

    def start_subscriber(self):
        if self.sub_proc is not None:
            return

        topic = self.sub_topic_entry.get().strip() or "sensors/temp"
        port = self.sub_port_var.get().strip() or "5002"

        cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "subscriber.py"), "--broker", "127.0.0.1", "--port", port, "--topics", topic]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.sub_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
            self.btn_sub.config(state=tk.DISABLED)
            self.btn_unsub.config(state=tk.NORMAL)
            self.status_var.set(f"Status: Subscriber active on '{topic}' (Port {port})")

            threading.Thread(target=self._stream_output, args=(self.sub_proc, self.sub_txt, "sub"), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Could not start Subscriber: {e}")

    def stop_subscriber(self):
        if self.sub_proc:
            try:
                self.sub_proc.terminate()
            except Exception:
                pass
            self.sub_proc = None
        self.btn_sub.config(state=tk.NORMAL)
        self.btn_unsub.config(state=tk.DISABLED)
        self.append_terminal(self.sub_txt, "\n[SUBSCRIBER DISCONNECTED]\n")

    # ----------------------------------------------------------------------
    # PANE 3: PUBLISHER
    # ----------------------------------------------------------------------
    def _build_pub_controls(self, parent):
        top_ctrl = tk.Frame(parent)
        top_ctrl.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top_ctrl, text="Topic:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, padx=2)
        self.pub_topic_entry = tk.Entry(top_ctrl, font=("Arial", 9), width=16)
        self.pub_topic_entry.insert(0, "sensors/temp")
        self.pub_topic_entry.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)

        tk.Label(top_ctrl, text="Port:", font=("Arial", 9)).grid(row=0, column=2, sticky=tk.W, padx=2)
        self.pub_port_var = tk.StringVar(value="5002")
        pub_combo = ttk.Combobox(top_ctrl, textvariable=self.pub_port_var, values=["5002", "5001"], width=6, state="readonly")
        pub_combo.grid(row=0, column=3, padx=2, pady=2)

        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=(0, 4))

        self.btn_pub_single = tk.Button(btn_row, text="Publish 1 Msg", bg="#fff3cd", fg="#856404", font=("Arial", 9, "bold"), command=lambda: self.run_publisher(count=1))
        self.btn_pub_single.pack(side=tk.LEFT, padx=2)

        self.btn_pub_burst = tk.Button(btn_row, text="Burst 16 (SDN Promotion)", bg="#d1ecf1", fg="#0c5460", font=("Arial", 9, "bold"), command=lambda: self.run_publisher(count=16))
        self.btn_pub_burst.pack(side=tk.LEFT, padx=2)

        # Quick topic buttons
        tk.Button(btn_row, text="Temp", font=("Arial", 8), command=lambda: self._set_pub_topic("sensors/temp", "5002")).pack(side=tk.RIGHT, padx=1)
        tk.Button(btn_row, text="Fire Alert", font=("Arial", 8), command=lambda: self._set_pub_topic("alerts/fire", "5001")).pack(side=tk.RIGHT, padx=1)

        self.pub_txt = scrolledtext.ScrolledText(parent, bg="black", fg="#ffcc00", insertbackground="white", font=("Courier", 8), wrap=tk.WORD)
        self.pub_txt.pack(fill=tk.BOTH, expand=True)

    def _set_pub_topic(self, topic, port):
        self.pub_topic_entry.delete(0, tk.END)
        self.pub_topic_entry.insert(0, topic)
        self.pub_port_var.set(port)

    def run_publisher(self, count=1):
        topic = self.pub_topic_entry.get().strip() or "sensors/temp"
        port = self.pub_port_var.get().strip() or "5002"

        self.btn_pub_single.config(state=tk.DISABLED)
        self.btn_pub_burst.config(state=tk.DISABLED)

        def worker():
            cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "publisher.py"), "--broker", "127.0.0.1", "--port", port, "--topic", topic, "--count", str(count), "--interval", "0.06"]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
                for line in proc.stdout:
                    self.msg_queue.put((self.pub_txt, line))
                proc.wait()
            except Exception as e:
                self.msg_queue.put((self.pub_txt, f"[ERROR] Publisher failed: {e}\n"))
            finally:
                self.root.after(0, lambda: self.btn_pub_single.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.btn_pub_burst.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    # ----------------------------------------------------------------------
    # STREAMING & HELPER FUNCTIONS
    # ----------------------------------------------------------------------
    def _stream_output(self, proc, widget, role):
        for line in proc.stdout:
            self.msg_queue.put((widget, line))
        proc.stdout.close()
        if role == "broker":
            self.root.after(0, lambda: self.btn_start_broker.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop_broker.config(state=tk.DISABLED))
        elif role == "sub":
            self.root.after(0, lambda: self.btn_sub.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_unsub.config(state=tk.DISABLED))

    def _process_queue(self):
        while not self.msg_queue.empty():
            try:
                widget, text = self.msg_queue.get_nowait()
                self.append_terminal(widget, text)
            except queue.Empty:
                break
        self.root.after(50, self._process_queue)

    def append_terminal(self, widget, text):
        widget.insert(tk.END, text)
        widget.see(tk.END)

    def clear_all_terminals(self):
        self.broker_txt.delete("1.0", tk.END)
        self.sub_txt.delete("1.0", tk.END)
        self.pub_txt.delete("1.0", tk.END)

    def on_closing(self):
        self.stop_subscriber()
        self.stop_broker()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = PubSubTkinterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
