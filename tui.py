#!/usr/bin/env python3
"""
tui.py - Minimal Terminal GUI (TUI) for TCP Pub-Sub Messaging System

A clean, non-AI styled terminal user interface using Python's standard 'curses'
library. Displays 3 live terminal panes directly inside your terminal window:
  - Box 1: Broker Console (Ports 5001 & 5002)
  - Box 2: Subscriber Console (sensors/temp)
  - Box 3: Publisher Console (Transmissions & ACKs)

Controls:
  [B] Start / Stop Broker
  [S] Start / Stop Subscriber
  [P] Publish 1 Message
  [X] Burst 16 Messages (Triggers Dynamic SDN Promotion)
  [C] Clear Terminals
  [Q] Quit & Clean Exit
"""

import curses
import os
import queue
import subprocess
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class PubSubTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True

        # Process handles
        self.broker_proc = None
        self.sub_proc = None

        # Log buffers (list of strings for each pane)
        self.broker_logs = []
        self.sub_logs = []
        self.pub_logs = []

        self.log_queue = queue.Queue()
        self.status_msg = "Ready. Press [B] to start Broker, [S] to Subscribe, [P] to Publish, [Q] to Quit."

        # Setup curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)

        # Colors if supported
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # Broker
        curses.init_pair(2, curses.COLOR_CYAN, -1)    # Subscriber
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Publisher
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE) # Header bar

    def run(self):
        while self.running:
            self._handle_input()
            self._drain_queue()
            self._draw()
            time.sleep(0.04)

        self._cleanup()

    def _handle_input(self):
        try:
            ch = self.stdscr.getch()
        except Exception:
            return

        if ch in (ord('q'), ord('Q'), 27): # 'q' or ESC
            self.running = False
        elif ch in (ord('b'), ord('B')):
            self._toggle_broker()
        elif ch in (ord('s'), ord('S')):
            self._toggle_subscriber()
        elif ch in (ord('p'), ord('P')):
            self._publish_messages(count=1)
        elif ch in (ord('x'), ord('X')):
            self._publish_messages(count=16)
        elif ch in (ord('c'), ord('C')):
            self.broker_logs.clear()
            self.sub_logs.clear()
            self.pub_logs.clear()
            self.status_msg = "Cleared all terminal panes."

    def _toggle_broker(self):
        if self.broker_proc is None:
            cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "broker.py"), "--host", "127.0.0.1", "--priority-port", "5001", "--std-port", "5002"]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            try:
                self.broker_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
                threading.Thread(target=self._stream_reader, args=(self.broker_proc, "broker"), daemon=True).start()
                self.status_msg = "Broker started on ports 5001 (Priority) and 5002 (Standard)."
            except Exception as e:
                self.status_msg = f"Failed to start broker: {e}"
        else:
            try:
                self.broker_proc.terminate()
            except Exception:
                pass
            self.broker_proc = None
            self.log_queue.put(("broker", "\n[BROKER TERMINATED]\n"))
            self.status_msg = "Broker stopped."

    def _toggle_subscriber(self):
        if self.sub_proc is None:
            cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "subscriber.py"), "--broker", "127.0.0.1", "--port", "5002", "--topics", "sensors/temp"]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            try:
                self.sub_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
                threading.Thread(target=self._stream_reader, args=(self.sub_proc, "sub"), daemon=True).start()
                self.status_msg = "Subscriber connected to 'sensors/temp' on port 5002."
            except Exception as e:
                self.status_msg = f"Failed to start subscriber: {e}"
        else:
            try:
                self.sub_proc.terminate()
            except Exception:
                pass
            self.sub_proc = None
            self.log_queue.put(("sub", "\n[SUBSCRIBER DISCONNECTED]\n"))
            self.status_msg = "Subscriber disconnected."

    def _publish_messages(self, count=1):
        def worker():
            cmd = [sys.executable, "-u", os.path.join(BASE_DIR, "pubsub", "publisher.py"), "--broker", "127.0.0.1", "--port", "5002", "--topic", "sensors/temp", "--count", str(count), "--interval", "0.06"]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
                for line in proc.stdout:
                    self.log_queue.put(("pub", line))
                proc.wait()
            except Exception as e:
                self.log_queue.put(("pub", f"[ERROR] {e}\n"))

        threading.Thread(target=worker, daemon=True).start()
        self.status_msg = f"Published {count} message(s) to topic 'sensors/temp'."

    def _stream_reader(self, proc, tag):
        for line in proc.stdout:
            self.log_queue.put((tag, line))
        proc.stdout.close()

    def _drain_queue(self):
        while not self.log_queue.empty():
            try:
                tag, line = self.log_queue.get_nowait()
                # Clean ANSI codes if any
                clean_line = self._strip_ansi(line).rstrip("\r\n")
                if not clean_line.strip():
                    continue

                if tag == "broker":
                    self.broker_logs.append(clean_line)
                    if len(self.broker_logs) > 300:
                        self.broker_logs.pop(0)
                elif tag == "sub":
                    self.sub_logs.append(clean_line)
                    if len(self.sub_logs) > 300:
                        self.sub_logs.pop(0)
                elif tag == "pub":
                    self.pub_logs.append(clean_line)
                    if len(self.pub_logs) > 300:
                        self.pub_logs.pop(0)
            except queue.Empty:
                break

    def _strip_ansi(self, s):
        import re
        return re.sub(r'\x1b\[[0-9;]*[mK]', '', s)

    def _draw(self):
        self.stdscr.erase()
        max_y, max_x = self.stdscr.getmaxyx()
        if max_y < 18 or max_x < 70:
            self.stdscr.addstr(0, 0, "Terminal window too small! Please expand window.")
            self.stdscr.refresh()
            return

        # 1. Top Title Bar
        title = " TCP PUB-SUB MESSAGING SYSTEM (UE25CS243A) - MINIMAL TERMINAL GUI "
        self.stdscr.attron(curses.color_pair(4))
        self.stdscr.addstr(0, 0, title.center(max_x - 1))
        self.stdscr.attroff(curses.color_pair(4))

        # Layout: Top half split into 2 columns (Broker on left, Sub on right), Bottom half for Publisher
        mid_y = max_y // 2
        col_w = max_x // 2

        # PANE 1: BROKER (Top Left)
        b_status = "RUNNING" if self.broker_proc else "STOPPED"
        self._draw_box(1, 0, mid_y - 1, col_w - 1, f" 1. Central Broker [{b_status}] ", self.broker_logs, curses.color_pair(1))

        # PANE 2: SUBSCRIBER (Top Right)
        s_status = "CONNECTED" if self.sub_proc else "IDLE"
        self._draw_box(1, col_w, mid_y - 1, max_x - col_w - 1, f" 2. Subscriber: sensors/temp [{s_status}] ", self.sub_logs, curses.color_pair(2))

        # PANE 3: PUBLISHER (Bottom Half)
        self._draw_box(mid_y, 0, max_y - mid_y - 2, max_x - 1, " 3. Publisher Console ", self.pub_logs, curses.color_pair(3))

        # Bottom Controls & Status Bar
        ctrl_bar = " [B] Toggle Broker | [S] Toggle Subscriber | [P] Publish 1 | [X] Burst 16 (SDN Promo) | [Q] Quit "
        self.stdscr.addstr(max_y - 2, 0, ctrl_bar[:max_x - 1], curses.A_BOLD)
        self.stdscr.addstr(max_y - 1, 0, f" Status: {self.status_msg}"[:max_x - 1], curses.A_DIM)

        self.stdscr.refresh()

    def _draw_box(self, start_y, start_x, height, width, title, logs, color):
        if height <= 2 or width <= 4:
            return

        try:
            # Draw borders
            self.stdscr.addstr(start_y, start_x, "+" + "-" * (width - 2) + "+")
            for y in range(start_y + 1, start_y + height - 1):
                self.stdscr.addstr(y, start_x, "|")
                self.stdscr.addstr(y, start_x + width - 1, "|")
            self.stdscr.addstr(start_y + height - 1, start_x, "+" + "-" * (width - 2) + "+")

            # Draw Title
            self.stdscr.addstr(start_y, start_x + 2, title[:width - 4], curses.A_BOLD)

            # Draw logs (last lines that fit)
            content_height = height - 2
            content_width = width - 4
            visible_logs = logs[-content_height:]

            for i, line in enumerate(visible_logs):
                self.stdscr.addstr(start_y + 1 + i, start_x + 2, line[:content_width], color)
        except Exception:
            pass

    def _cleanup(self):
        if self.sub_proc:
            try:
                self.sub_proc.terminate()
            except Exception:
                pass
        if self.broker_proc:
            try:
                self.broker_proc.terminate()
            except Exception:
                pass


def main():
    curses.wrapper(lambda stdscr: PubSubTUI(stdscr).run())


if __name__ == "__main__":
    main()
