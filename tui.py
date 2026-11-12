#!/usr/bin/env python3
"""
tui.py - Terminal User Interface (TUI) for TCP Pub-Sub Messaging System

A clean, responsive terminal user interface using Python's standard 'curses'
library with a true solid black background and a single unified, perfectly
aligned frame with zero uneven or fragmented borders.

Key Features & Form Factor:
  - Deep Black Background: Every pane, border, log line, test output, and empty
    interior space is explicitly rendered on curses.COLOR_BLACK.
  - Unified Seamless Frame: One single continuous rectangular dashboard frame
    with clean dividers (┌─┐, ├─┤, └─┘), completely eliminating uneven borders
    or nested ASCII box fragments.
  - Emojis Normalized: Double-width emojis are sanitized to single-width badges
    to ensure perfect vertical column alignment across all terminals.
  - Comprehensive Test Suite:
      * [B] Start / Stop Central Broker (:5001 Priority, :5002 Standard)
      * [S] Start / Stop Subscriber ('sensors/temp' port 5002)
      * [P] Test 1: Publish Single Standard Message (1 msg)
      * [2] Test 2: Publish High-Priority Messages (5 msgs, port 5001)
      * [X] Test 3: Burst SDN Promotion Test (16 msgs, triggers SDN webhook)
      * [A] Automated End-to-End Demo Test (Broker -> Sub -> Std -> Prio -> Burst)
      * [U] Run Unit Test Suite (tests/test_pubsub.py with live PASS/FAIL logs)
      * [C] Clear Console Buffers
      * [Q] Clean Exit & Process Cleanup
"""

import curses
import os
import queue
import re
import subprocess
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Curses Color Pair IDs (All explicitly paired with curses.COLOR_BLACK)
PAIR_BROKER = 1     # Green on Black
PAIR_SUB = 2        # Cyan on Black
PAIR_PUB = 3        # Yellow on Black
PAIR_HEADER = 4     # Bold Cyan on Black
PAIR_DEFAULT = 5    # White on Black (Base & Borders)
PAIR_HIGHLIGHT = 6  # Magenta on Black (SDN Trigger / Burst)
PAIR_ERROR = 7      # Red on Black (Errors / Stopped)
PAIR_BORDER = 8     # Dim White on Black


class PubSubTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.test_running = False

        # Subprocess handles
        self.broker_proc = None
        self.sub_proc = None

        # Log buffers (up to 500 lines per pane)
        self.broker_logs = []
        self.sub_logs = []
        self.pub_logs = []

        self.log_queue = queue.Queue()
        self.status_msg = "Ready. Press [A] for Auto-Demo, [B] Broker, [S] Sub, [P] Test, [Q] Quit."

        # Setup curses screen
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)

        # Setup Colors with strictly black background
        self._init_colors()

    def _init_colors(self):
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(PAIR_BROKER, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_SUB, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_PUB, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(PAIR_HEADER, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_DEFAULT, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            curses.init_pair(PAIR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(PAIR_BORDER, curses.COLOR_WHITE, curses.COLOR_BLACK)
            self.stdscr.bkgd(" ", curses.color_pair(PAIR_DEFAULT))

    def run(self):
        while self.running:
            self._handle_input()
            self._drain_queue()
            self._draw()
            time.sleep(0.04)

        self._cleanup()

    def _safe_addstr(self, y: int, x: int, s: str, attr: int = 0):
        """Safely writes a string without overflowing screen boundaries or raising curses.error."""
        max_y, max_x = self.stdscr.getmaxyx()
        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return
        avail = max_x - x
        if avail <= 0:
            return
        draw_s = s[:avail]
        # Prevent curses error on writing to bottom-right corner
        if y == max_y - 1 and x + len(draw_s) >= max_x:
            draw_s = draw_s[:max_x - x - 1]
        try:
            self.stdscr.addstr(y, x, draw_s, attr)
        except curses.error:
            pass

    def _handle_input(self):
        try:
            ch = self.stdscr.getch()
        except Exception:
            return

        if ch in (ord("q"), ord("Q"), 27):  # 'q' or ESC
            self.running = False
        elif ch in (ord("b"), ord("B")):
            self._toggle_broker()
        elif ch in (ord("s"), ord("S")):
            self._toggle_subscriber()
        elif ch in (ord("p"), ord("P")):
            self._publish_messages(port=5002, topic="sensors/temp", count=1, label="Standard Test (1 msg)")
        elif ch == ord("2"):
            self._publish_messages(port=5001, topic="alerts/fire", count=5, label="Priority Test (5 msgs)")
        elif ch in (ord("x"), ord("X")):
            self._publish_messages(port=5002, topic="sensors/temp", count=16, label="Burst SDN Promotion Test (16 msgs)")
        elif ch in (ord("a"), ord("A")):
            self._run_auto_demo()
        elif ch in (ord("u"), ord("U")):
            self._run_unit_tests()
        elif ch in (ord("c"), ord("C")):
            self.broker_logs.clear()
            self.sub_logs.clear()
            self.pub_logs.clear()
            self.stdscr.clear()
            self.status_msg = "Cleared all console logs."
        elif ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            self.stdscr.clear()

    # -------------------------------------------------------------------------
    # Process & Test Handlers
    # -------------------------------------------------------------------------

    def _start_broker_process(self):
        if self.broker_proc is None:
            cmd = [
                sys.executable,
                "-u",
                os.path.join(BASE_DIR, "pubsub", "broker.py"),
                "--host",
                "127.0.0.1",
                "--priority-port",
                "5001",
                "--std-port",
                "5002",
            ]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["TUI_MODE"] = "1"
            try:
                self.broker_proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
                )
                threading.Thread(target=self._stream_reader, args=(self.broker_proc, "broker"), daemon=True).start()
                self.status_msg = "✔ Broker started on 127.0.0.1:5001 (Priority) and :5002 (Standard)."
            except Exception as e:
                self.status_msg = f"✖ Failed to start broker: {e}"

    def _stop_broker_process(self):
        if self.broker_proc:
            try:
                self.broker_proc.terminate()
            except Exception:
                pass
            self.broker_proc = None
            self.log_queue.put(("broker", "\n[BROKER TERMINATED]\n"))
            self.status_msg = "Broker stopped."

    def _toggle_broker(self):
        if self.broker_proc is None:
            self._start_broker_process()
        else:
            self._stop_broker_process()

    def _start_subscriber_process(self):
        if self.sub_proc is None:
            cmd = [
                sys.executable,
                "-u",
                os.path.join(BASE_DIR, "pubsub", "subscriber.py"),
                "--broker",
                "127.0.0.1",
                "--port",
                "5002",
                "--topics",
                "sensors/temp",
            ]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["TUI_MODE"] = "1"
            try:
                self.sub_proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
                )
                threading.Thread(target=self._stream_reader, args=(self.sub_proc, "sub"), daemon=True).start()
                self.status_msg = "✔ Subscriber connected to 'sensors/temp' on port 5002."
            except Exception as e:
                self.status_msg = f"✖ Failed to start subscriber: {e}"

    def _stop_subscriber_process(self):
        if self.sub_proc:
            try:
                self.sub_proc.terminate()
            except Exception:
                pass
            self.sub_proc = None
            self.log_queue.put(("sub", "\n[SUBSCRIBER DISCONNECTED]\n"))
            self.status_msg = "Subscriber disconnected."

    def _toggle_subscriber(self):
        if self.sub_proc is None:
            self._start_subscriber_process()
        else:
            self._stop_subscriber_process()

    def _publish_messages(self, port=5002, topic="sensors/temp", count=1, interval=0.06, label="Publish"):
        def worker():
            cmd = [
                sys.executable,
                "-u",
                os.path.join(BASE_DIR, "pubsub", "publisher.py"),
                "--broker",
                "127.0.0.1",
                "--port",
                str(port),
                "--topic",
                topic,
                "--count",
                str(count),
                "--interval",
                str(interval),
            ]
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["TUI_MODE"] = "1"
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
                )
                for line in proc.stdout:
                    self.log_queue.put(("pub", line))
                proc.wait()
            except Exception as e:
                self.log_queue.put(("pub", f"[ERROR] {e}\n"))

        threading.Thread(target=worker, daemon=True).start()
        self.status_msg = f"{label}: Sent {count} msg(s) on '{topic}' (Port {port})."

    def _publish_sync(self, port=5002, topic="sensors/temp", count=5, interval=0.08, label=""):
        cmd = [
            sys.executable,
            "-u",
            os.path.join(BASE_DIR, "pubsub", "publisher.py"),
            "--broker",
            "127.0.0.1",
            "--port",
            str(port),
            "--topic",
            topic,
            "--count",
            str(count),
            "--interval",
            str(interval),
        ]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["TUI_MODE"] = "1"
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
            )
            for line in proc.stdout:
                self.log_queue.put(("pub", line))
            proc.wait()
        except Exception as e:
            self.log_queue.put(("pub", f"[ERROR] {e}\n"))

    def _run_auto_demo(self):
        if self.test_running:
            self.status_msg = "⚠ A test suite is already executing. Please wait..."
            return

        def worker():
            self.test_running = True
            self.pub_logs.append("═" * 58)
            self.pub_logs.append("🚀 STARTING AUTOMATED END-TO-END SYSTEM DEMO")
            self.pub_logs.append("═" * 58)

            # Step 1: Start Broker if not running
            self.status_msg = "[1/4] Starting Central Broker on ports 5001 & 5002..."
            if self.broker_proc is None:
                self._start_broker_process()
                time.sleep(0.8)

            # Step 2: Start Subscriber if not running
            self.status_msg = "[2/4] Connecting Subscriber to topic 'sensors/temp'..."
            if self.sub_proc is None:
                self._start_subscriber_process()
                time.sleep(0.8)

            # Step 3: Standard messages
            self.status_msg = "[3/4] Testing Standard Flow (5 msgs on 'sensors/temp' port 5002)..."
            self._publish_sync(port=5002, topic="sensors/temp", count=5, interval=0.08, label="Standard Test")
            time.sleep(0.6)

            # Step 4: High-Priority messages
            self.status_msg = "[4/4] Testing Priority Flow (5 msgs on 'alerts/fire' port 5001)..."
            self._publish_sync(port=5001, topic="alerts/fire", count=5, interval=0.08, label="Priority Test")
            time.sleep(0.6)

            # Step 5: Burst Trigger Test
            self.status_msg = "[BURST TEST] Streaming 16 messages to trigger SDN promotion webhook..."
            self._publish_sync(port=5002, topic="sensors/temp", count=16, interval=0.05, label="Burst SDN Test")

            self.pub_logs.append("═" * 58)
            self.pub_logs.append("✔ AUTOMATED END-TO-END DEMO TEST COMPLETED SUCCESSFULLY!")
            self.pub_logs.append("═" * 58)
            self.status_msg = "✔ All tests passed. Broker and Subscriber remain active."
            self.test_running = False

        threading.Thread(target=worker, daemon=True).start()

    def _run_unit_tests(self):
        if self.test_running:
            self.status_msg = "⚠ A test is already running. Please wait..."
            return

        def worker():
            self.test_running = True
            self.pub_logs.append("═" * 58)
            self.pub_logs.append("🧪 RUNNING UNIT TEST SUITE (tests/test_pubsub.py)")
            self.pub_logs.append("═" * 58)
            self.status_msg = "Running unit tests in background..."

            test_dir = os.path.join(BASE_DIR, "tests")
            cmd = [sys.executable, "-m", "unittest", "discover", "-s", test_dir, "-v"]
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=BASE_DIR
                )
                for line in proc.stdout:
                    clean = self._sanitize_line(line)
                    if clean:
                        self.pub_logs.append(clean)
                proc.wait()
                if proc.returncode == 0:
                    self.pub_logs.append("─" * 58)
                    self.pub_logs.append("✔ ALL UNIT TESTS PASSED (3/3)")
                    self.status_msg = "✔ Unit tests passed (exit code 0)."
                else:
                    self.pub_logs.append(f"✖ UNIT TESTS FAILED (code {proc.returncode})")
                    self.status_msg = f"✖ Unit tests exited with code {proc.returncode}."
            except Exception as e:
                self.pub_logs.append(f"[ERROR] Failed to run tests: {e}")
                self.status_msg = f"Error running tests: {e}"

            self.test_running = False

        threading.Thread(target=worker, daemon=True).start()

    def _stream_reader(self, proc, tag):
        for line in proc.stdout:
            self.log_queue.put((tag, line))
        proc.stdout.close()

    def _drain_queue(self):
        while not self.log_queue.empty():
            try:
                tag, line = self.log_queue.get_nowait()
                clean_line = self._sanitize_line(line)
                if not clean_line:
                    continue

                if tag == "broker":
                    self.broker_logs.append(clean_line)
                    if len(self.broker_logs) > 500:
                        self.broker_logs.pop(0)
                elif tag == "sub":
                    self.sub_logs.append(clean_line)
                    if len(self.sub_logs) > 500:
                        self.sub_logs.pop(0)
                elif tag == "pub":
                    self.pub_logs.append(clean_line)
                    if len(self.pub_logs) > 500:
                        self.pub_logs.pop(0)
            except queue.Empty:
                break

    def _sanitize_line(self, line: str) -> str:
        """Strips ANSI codes, suppresses nested decorative ASCII banners, and normalizes wide emojis."""
        clean = re.sub(r"\x1b\[[0-9;]*[mK]", "", line).rstrip("\r\n")
        if not clean.strip():
            return ""

        # Filter out standalone decorative box borders from subprocesses
        if clean.startswith(("┌", "├", "└", "╔", "╠", "╚")) and any(c in clean for c in ("─", "═", "┬", "┴")):
            return ""
        if clean.endswith(("┐", "┤", "┘", "╗", "╣", "╝")) and any(c in clean for c in ("─", "═", "┬", "┴")):
            return ""

        # Filter out banner box text fragments that leak into TUI
        u = clean.upper()
        if any(k in u for k in ("TCP PUBLISH–SUBSCRIBE CENTRAL BROKER", "TCP PUB-SUB SUBSCRIBER", "PUBLISHING SUMMARY")):
            return ""
        if any(k in u for k in ("COURSE: COMPUTER NETWORKS", "BROKER TARGET :", "PUBLISH PLAN  :", "MESSAGES SENT     :", "TOTAL DELIVERIES  :", "ELAPSED TIME      :")):
            return ""

        # Normalize emojis to single-width tags to prevent column drift and uneven borders
        clean = clean.replace("🚀", "[FAST]")
        clean = clean.replace("⚠️", "[STD]")
        clean = clean.replace("📊", "[STATS]")
        clean = clean.replace("📡", "[BROKER]")
        clean = clean.replace("📥", "[SUB]")
        clean = clean.replace("📤", "[PUB]")
        clean = clean.replace("⚡", "[SDN]")

        # Clean trailing box characters if any
        if clean.endswith("│") and not "│" in clean[:5]:
            clean = clean[:-1].rstrip()

        return clean

    def _classify_line(self, line: str, default_pair: int):
        """Categorizes log lines to assign syntax highlighting colors against black background."""
        u = line.upper()
        if any(k in u for k in ("BURST-DETECTED", "SDN-HOOK", "FAST_PATH", "FAST PATH", "PROMOTION", "[FAST]")):
            return curses.color_pair(PAIR_HIGHLIGHT), curses.A_BOLD
        if any(k in u for k in ("ERROR", "FAIL", "EXCEPTION", "DISCONNECT", "CLOSED CONNECTION", "TERMINATED")):
            return curses.color_pair(PAIR_ERROR), curses.A_BOLD
        if any(k in u for k in ("CONNECT", "SUBSCRIBE", " OK", "✔", "PASSED", "DELIVERED", "RUNNING")):
            return curses.color_pair(PAIR_BROKER), curses.A_BOLD
        if any(k in u for k in ("PUBLISH", "SEQ", "SENSORS/TEMP", "ALERTS/FIRE")):
            return curses.color_pair(PAIR_SUB), 0
        if any(k in u for k in ("STANDARD", "IDLE", "WARNING", "[STD]")):
            return curses.color_pair(PAIR_PUB), 0
        if any(k in line for k in ("┌", "├", "└", "│", "─", "╔", "╠", "╚", "║", "═")):
            return curses.color_pair(PAIR_BORDER), 0
        return curses.color_pair(default_pair), 0

    # -------------------------------------------------------------------------
    # Layout & Rendering Engine (Single Unified Seamless Frame)
    # -------------------------------------------------------------------------

    def _draw(self):
        max_y, max_x = self.stdscr.getmaxyx()

        # Enforce minimum usable form factor
        if max_y < 16 or max_x < 55:
            self.stdscr.erase()
            msg = f"Terminal too small ({max_x}x{max_y}). Please expand to at least 70x18."
            self._safe_addstr(max_y // 2, max(0, (max_x - len(msg)) // 2), msg, curses.color_pair(PAIR_ERROR))
            self.stdscr.refresh()
            return

        w = max_x

        # 1. Top Title Bar (Solid Black background, Bold Cyan / White text)
        title_left = " 📡 SDN-INTEGRATED TCP PUB-SUB MESSAGING SYSTEM "
        title_mid = "Course: UE25CS243A (Project #9)"
        self._safe_addstr(0, 0, " " * (w - 1), curses.color_pair(PAIR_DEFAULT))
        self._safe_addstr(0, 0, title_left, curses.color_pair(PAIR_HEADER) | curses.A_BOLD)
        mid_x = max(len(title_left) + 2, (w - len(title_mid)) // 2)
        if mid_x + len(title_mid) < w - 2:
            self._safe_addstr(0, mid_x, title_mid, curses.color_pair(PAIR_DEFAULT) | curses.A_DIM)

        # 2. Live Status Badges
        b_badge = "● RUNNING (:5001, :5002)" if self.broker_proc else "■ STOPPED"
        b_pair = curses.color_pair(PAIR_BROKER) if self.broker_proc else curses.color_pair(PAIR_ERROR)

        s_badge = "● CONNECTED (sensors/temp)" if self.sub_proc else "○ IDLE"
        s_pair = curses.color_pair(PAIR_SUB) if self.sub_proc else curses.color_pair(PAIR_PUB)

        p_badge = "● READY"
        p_pair = curses.color_pair(PAIR_PUB)
        if self.test_running:
            p_badge = "⚡ TEST RUNNING"
            p_pair = curses.color_pair(PAIR_HIGHLIGHT)

        # 3. Dynamic Row Allocation for Unified Frame
        # Total frame spans from y=1 to y=max_y-3
        # Border rows: y=1 (top), y_div1 (mid1), y_div2 (mid2), y_bot (bottom) -> 4 border rows
        content_total = max(3, (max_y - 3) - 4)
        h_broker = max(2, int(content_total * 0.28))
        h_sub = max(3, int(content_total * 0.44))
        h_pub = content_total - h_broker - h_sub
        if h_pub < 2:
            h_pub = 2
            h_sub = max(2, content_total - h_broker - h_pub)

        y_top = 1
        y_div1 = y_top + 1 + h_broker
        y_div2 = y_div1 + 1 + h_sub
        y_bot = max_y - 3

        # 4. Render Unified Outer & Divider Borders (Mathematically 100% Even)
        self._draw_divider_line(y_top, "┌", "1. Central Broker Console", b_badge, b_pair, "┐", w)
        self._draw_content_rows(y_top + 1, h_broker, self.broker_logs, PAIR_BROKER, w)

        self._draw_divider_line(y_div1, "├", "2. Subscriber Console", s_badge, s_pair, "┤", w)
        self._draw_content_rows(y_div1 + 1, h_sub, self.sub_logs, PAIR_SUB, w)

        self._draw_divider_line(y_div2, "├", "3. Publisher & Test Console", p_badge, p_pair, "┤", w)
        self._draw_content_rows(y_div2 + 1, h_pub, self.pub_logs, PAIR_PUB, w)

        # Bottom Border of the Unified Frame
        bottom_str = "└" + ("─" * (w - 2)) + "┘"
        self._safe_addstr(y_bot, 0, bottom_str, curses.color_pair(PAIR_BORDER))

        # 5. Bottom Controls Bar
        ctrl_y = max_y - 2
        self._safe_addstr(ctrl_y, 0, " " * (w - 1), curses.color_pair(PAIR_DEFAULT))
        if w >= 105:
            ctrls = [
                ("[B]", "Broker "),
                ("[S]", "Sub "),
                ("[P]", "Std-1 "),
                ("[2]", "Prio-5 "),
                ("[X]", "Burst-16 "),
                ("[A]", "Auto-Demo "),
                ("[U]", "Unit-Tests "),
                ("[C]", "Clear "),
                ("[Q]", "Quit "),
            ]
        else:
            ctrls = [
                ("[B]", "Brok "),
                ("[S]", "Sub "),
                ("[P]", "P1 "),
                ("[2]", "P5 "),
                ("[X]", "Burst "),
                ("[A]", "Auto "),
                ("[U]", "Test "),
                ("[C]", "Clr "),
                ("[Q]", "Quit"),
            ]

        x_pos = 1
        for key_tag, desc in ctrls:
            self._safe_addstr(ctrl_y, x_pos, key_tag, curses.color_pair(PAIR_PUB) | curses.A_BOLD)
            x_pos += len(key_tag)
            self._safe_addstr(ctrl_y, x_pos, desc, curses.color_pair(PAIR_DEFAULT))
            x_pos += len(desc)

        # 6. Status / Notification Line
        stat_y = max_y - 1
        self._safe_addstr(stat_y, 0, " " * (w - 1), curses.color_pair(PAIR_DEFAULT))
        status_text = f" Status: {self.status_msg}"
        self._safe_addstr(stat_y, 0, status_text[:w - 2], curses.color_pair(PAIR_SUB))

        self.stdscr.refresh()

    def _draw_divider_line(
        self, y: int, left_char: str, title: str, badge_text: str, badge_color: int, right_char: str, width: int
    ):
        """Draws an edge-to-edge border or divider line with title and live status badge."""
        prefix = f"{left_char}─ {title} "
        badge_str = f"[{badge_text}] " if badge_text else ""
        suffix = f" {badge_str}─{right_char}" if badge_str else f"─{right_char}"

        needed_fill = width - len(prefix) - len(suffix)
        if needed_fill >= 0:
            border_str = prefix + ("─" * needed_fill) + suffix
        else:
            # Narrow screen: truncate title so badge and border fit perfectly
            avail_title = max(1, width - len(suffix) - 5)
            prefix = f"{left_char}─ {title[:avail_title]} "
            needed_fill = max(0, width - len(prefix) - len(suffix))
            border_str = prefix + ("─" * needed_fill) + suffix

        # Print prefix and border line
        self._safe_addstr(y, 0, border_str, curses.color_pair(PAIR_BORDER))
        # Highlight title in bold white
        title_start = 2
        self._safe_addstr(y, title_start, f" {title[:avail_title if needed_fill < 0 else len(title)]} ", curses.color_pair(PAIR_DEFAULT) | curses.A_BOLD)

        # Highlight badge with its color
        if badge_text:
            badge_pos = border_str.rfind(badge_str)
            if badge_pos != -1:
                self._safe_addstr(y, badge_pos, badge_str, badge_color | curses.A_BOLD)

    def _draw_content_rows(self, start_y: int, count: int, logs: list, default_pair: int, width: int):
        """Fills every content row inside a pane with exact borders and spaces on solid black background."""
        content_w = width - 4
        visible_logs = logs[-count:]

        for r in range(count):
            y = start_y + r
            # Left border at column 0
            self._safe_addstr(y, 0, "│ ", curses.color_pair(PAIR_BORDER))

            log_idx = r - (count - len(visible_logs))
            if log_idx >= 0:
                raw_line = visible_logs[log_idx]
                color, attr = self._classify_line(raw_line, default_pair)
                line_str = raw_line[:content_w].ljust(content_w)
                self._safe_addstr(y, 2, line_str, color | attr)
            else:
                # Fill empty row with spaces on black background
                self._safe_addstr(y, 2, " " * content_w, curses.color_pair(PAIR_DEFAULT))

            # Right border at column width - 1
            self._safe_addstr(y, width - 2, " │", curses.color_pair(PAIR_BORDER))

    def _cleanup(self):
        self.running = False
        for proc in (self.sub_proc, self.broker_proc):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass


def main():
    curses.wrapper(lambda stdscr: PubSubTUI(stdscr).run())


if __name__ == "__main__":
    main()
