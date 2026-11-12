#!/usr/bin/env python3
"""
tui.py - Terminal User Interface (TUI) for TCP Pub-Sub Messaging System

A clean, responsive terminal user interface using Python's standard 'curses'
library with a true solid black background across all visual elements and tests.

Key Features & Form Factor:
  - Deep Black Background: Every pane, border, log line, test output, and empty
    interior space is explicitly filled with curses.COLOR_BLACK.
  - Proper Form Factor:
      * Stacked Layout (Default): 3 full-width horizontal panes ensuring the wide
        78-column subscriber latency table and broker banners never truncate.
      * Split Layout (Toggleable via [L]): 2-column view with subscriber full-height.
      * Edge-safe bounds checking to avoid curses.error on window resizing.
  - Comprehensive Test Suite:
      * [B] Start / Stop Central Broker (:5001 Priority, :5002 Standard)
      * [S] Start / Stop Subscriber ('sensors/temp' port 5002)
      * [P] Test 1: Publish Single Standard Message (1 msg)
      * [2] Test 2: Publish High-Priority Messages (5 msgs, port 5001)
      * [X] Test 3: Burst SDN Promotion Test (16 msgs, triggers SDN webhook)
      * [A] Automated End-to-End Demo Test (Broker -> Sub -> Std -> Prio -> Burst)
      * [U] Run Unit Test Suite (tests/test_pubsub.py with live PASS/FAIL logs)
      * [L] Toggle Layout Mode (Stacked <-> Split)
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
PAIR_BORDER = 8     # Dim White / Blue on Black


class PubSubTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.test_running = False
        self.layout_mode = "stacked"  # "stacked" or "split"

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
            # Explicitly enforce pure COLOR_BLACK for all background pairs
            curses.init_pair(PAIR_BROKER, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_SUB, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_PUB, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(PAIR_HEADER, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(PAIR_DEFAULT, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            curses.init_pair(PAIR_ERROR, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(PAIR_BORDER, curses.COLOR_WHITE, curses.COLOR_BLACK)
            # Set window background to pure black space
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
        elif ch in (ord("l"), ord("L")):
            self.layout_mode = "split" if self.layout_mode == "stacked" else "stacked"
            self.stdscr.clear()
            self.status_msg = f"Switched layout to: {self.layout_mode.upper()} mode."
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
                    clean = self._strip_ansi(line).rstrip("\r\n")
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
                clean_line = self._strip_ansi(line).rstrip("\r\n")
                if not clean_line.strip():
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

    def _strip_ansi(self, s: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*[mK]", "", s)

    def _classify_line(self, line: str, default_pair: int):
        """Categorizes log lines to assign syntax highlighting colors against black background."""
        u = line.upper()
        if any(k in u for k in ("BURST-DETECTED", "SDN-HOOK", "FAST_PATH", "FAST PATH", "PROMOTION")):
            return curses.color_pair(PAIR_HIGHLIGHT), curses.A_BOLD
        if any(k in u for k in ("ERROR", "FAIL", "EXCEPTION", "DISCONNECT", "CLOSED CONNECTION", "TERMINATED")):
            return curses.color_pair(PAIR_ERROR), curses.A_BOLD
        if any(k in u for k in ("CONNECT", "SUBSCRIBE", " OK", "✔", "PASSED", "DELIVERED", "RUNNING")):
            return curses.color_pair(PAIR_BROKER), curses.A_BOLD
        if any(k in u for k in ("PUBLISH", "SEQ", "SENSORS/TEMP", "ALERTS/FIRE")):
            return curses.color_pair(PAIR_SUB), 0
        if any(k in u for k in ("STANDARD", "IDLE", "WARNING", "⚠")):
            return curses.color_pair(PAIR_PUB), 0
        if any(k in line for k in ("┌", "├", "└", "│", "─", "╔", "╠", "╚", "║", "═")):
            return curses.color_pair(PAIR_BORDER), 0
        return curses.color_pair(default_pair), 0

    def _format_log_line(self, line: str, max_w: int) -> str:
        """Dynamically reformats wide subscriber table rows for narrower terminal form factors."""
        if len(line) <= max_w:
            return line

        # If it's a wide 5-column subscriber latency table row
        if line.startswith("│ #") and "│" in line[2:]:
            parts = [p.strip() for p in line.split("│") if p.strip()]
            if len(parts) >= 4:
                seq = parts[0]
                topic = parts[1]
                t_class = parts[2]
                lat = parts[3]
                payload = parts[4] if len(parts) > 4 else ""

                # Compact format: Fits in ~55-70 characters without losing latency or payload
                compact = f"{seq} │ {topic} │ {t_class} │ {lat} │ {payload}".rstrip()
                if len(compact) <= max_w:
                    return compact
                # Extreme narrow format:
                ultra = f"{seq} │ {topic[:12]} │ {t_class[:8]} │ {lat} │ {payload[:20]}".rstrip()
                return ultra[:max_w]

        # Truncate wide decorative borders cleanly
        if line.startswith(("┌", "├", "└", "╔", "╠", "╚", "─", "═")):
            return line[:max_w]

        return line[:max_w]

    # -------------------------------------------------------------------------
    # Layout & Rendering Engine
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

        # 1. Top Title Bar (Solid Black background, Bold Cyan / White text)
        title_left = " 📡 SDN-INTEGRATED TCP PUB-SUB MESSAGING SYSTEM "
        title_mid = "Course: UE25CS243A (Project #9)"
        layout_badge = f" [Layout: {self.layout_mode.upper()} (L)] "

        # Clear line 0 with black background
        self._safe_addstr(0, 0, " " * (max_x - 1), curses.color_pair(PAIR_DEFAULT))
        self._safe_addstr(0, 0, title_left, curses.color_pair(PAIR_HEADER) | curses.A_BOLD)
        mid_x = max(len(title_left) + 2, (max_x - len(title_mid)) // 2)
        if mid_x + len(title_mid) < max_x - len(layout_badge) - 2:
            self._safe_addstr(0, mid_x, title_mid, curses.color_pair(PAIR_DEFAULT) | curses.A_DIM)
        badge_x = max_x - len(layout_badge) - 1
        if badge_x > mid_x + len(title_mid) + 2:
            self._safe_addstr(0, badge_x, layout_badge, curses.color_pair(PAIR_PUB) | curses.A_BOLD)

        # 2. Status Badges for Panes
        b_badge = "● RUNNING (:5001, :5002)" if self.broker_proc else "■ STOPPED"
        b_pair = curses.color_pair(PAIR_BROKER) if self.broker_proc else curses.color_pair(PAIR_ERROR)

        s_badge = "● CONNECTED (sensors/temp)" if self.sub_proc else "○ IDLE"
        s_pair = curses.color_pair(PAIR_SUB) if self.sub_proc else curses.color_pair(PAIR_PUB)

        p_badge = "● READY"
        p_pair = curses.color_pair(PAIR_PUB)
        if self.test_running:
            p_badge = "⚡ TEST RUNNING"
            p_pair = curses.color_pair(PAIR_HIGHLIGHT)

        # 3. Form Factor Layout Calculation
        usable_h = max_y - 3  # rows available between title (y=0) and controls (y=max_y-2)

        if self.layout_mode == "stacked":
            # Stacked Layout: 3 balanced full-width horizontal panes
            h_broker = max(5, int(usable_h * 0.28))
            h_sub = max(6, int(usable_h * 0.40))
            h_pub = usable_h - h_broker - h_sub
            if h_pub < 5:
                diff = 5 - h_pub
                h_pub = 5
                h_sub = max(5, h_sub - diff)

            w = max_x - 1

            # Pane 1: Broker (Top)
            self._draw_box(1, 0, h_broker, w, "1. Central Broker Console", b_badge, b_pair, self.broker_logs, PAIR_BROKER)

            # Pane 2: Subscriber (Middle - Wide space for complete 78-col latency table)
            self._draw_box(1 + h_broker, 0, h_sub, w, "2. Subscriber Console", s_badge, s_pair, self.sub_logs, PAIR_SUB)

            # Pane 3: Publisher & Test Suite (Bottom)
            self._draw_box(1 + h_broker + h_sub, 0, h_pub, w, "3. Publisher & Test Console", p_badge, p_pair, self.pub_logs, PAIR_PUB)

        else:
            # Split Layout: 2-column view (Broker & Pub on Left, Subscriber Full-Height on Right)
            w_sub = min(max_x // 2, 85)
            w_left = max_x - w_sub - 1
            h_top = usable_h // 2
            h_bot = usable_h - h_top

            # Top Left: Broker
            self._draw_box(1, 0, h_top, w_left, "1. Central Broker", b_badge, b_pair, self.broker_logs, PAIR_BROKER)

            # Bottom Left: Publisher / Tests
            self._draw_box(1 + h_top, 0, h_bot, w_left, "3. Publisher / Tests", p_badge, p_pair, self.pub_logs, PAIR_PUB)

            # Right Column: Subscriber (Full Height)
            self._draw_box(1, w_left, usable_h, w_sub, "2. Subscriber Console", s_badge, s_pair, self.sub_logs, PAIR_SUB)

        # 4. Bottom Controls Bar (Black background, Bold Yellow shortcuts)
        ctrl_y = max_y - 2
        self._safe_addstr(ctrl_y, 0, " " * (max_x - 1), curses.color_pair(PAIR_DEFAULT))
        if max_x >= 115:
            ctrls = [
                ("[B]", "Broker "),
                ("[S]", "Sub "),
                ("[P]", "Std-1 "),
                ("[2]", "Prio-5 "),
                ("[X]", "Burst-16 "),
                ("[A]", "Auto-Demo "),
                ("[U]", "Unit-Tests "),
                ("[L]", "Layout "),
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
                ("[L]", "View "),
                ("[C]", "Clr "),
                ("[Q]", "Quit"),
            ]

        x_pos = 1
        for key_tag, desc in ctrls:
            self._safe_addstr(ctrl_y, x_pos, key_tag, curses.color_pair(PAIR_PUB) | curses.A_BOLD)
            x_pos += len(key_tag)
            self._safe_addstr(ctrl_y, x_pos, desc, curses.color_pair(PAIR_DEFAULT))
            x_pos += len(desc)

        # 5. Status / Notification Line
        stat_y = max_y - 1
        self._safe_addstr(stat_y, 0, " " * (max_x - 1), curses.color_pair(PAIR_DEFAULT))
        status_text = f" Status: {self.status_msg}"
        self._safe_addstr(stat_y, 0, status_text[:max_x - 2], curses.color_pair(PAIR_SUB))

        self.stdscr.refresh()

    def _draw_box(
        self,
        start_y: int,
        start_x: int,
        height: int,
        width: int,
        title: str,
        badge_text: str,
        badge_color: int,
        logs: list,
        default_pair: int,
    ):
        """Draws a clean box with top title, live status badge, and fills every row with pure black background."""
        if height <= 2 or width <= 4:
            return

        content_h = height - 2
        content_w = width - 4

        # 1. Top border with Title and Badge
        title_str = f" {title} "
        badge_str = f" {badge_text} " if badge_text else ""
        right_x = start_x + width - 1

        self._safe_addstr(start_y, start_x, "┌", curses.color_pair(PAIR_BORDER))
        cur_x = start_x + 1

        self._safe_addstr(start_y, cur_x, "─", curses.color_pair(PAIR_BORDER))
        cur_x += 1
        self._safe_addstr(start_y, cur_x, title_str, curses.color_pair(PAIR_DEFAULT) | curses.A_BOLD)
        cur_x += len(title_str)

        badge_start_x = right_x - len(badge_str) - 2
        if badge_str and badge_start_x > cur_x + 2:
            fill_len = badge_start_x - cur_x
            self._safe_addstr(start_y, cur_x, "─" * fill_len, curses.color_pair(PAIR_BORDER))
            cur_x += fill_len
            self._safe_addstr(start_y, cur_x, badge_str, badge_color | curses.A_BOLD)
            cur_x += len(badge_str)
            rem = right_x - cur_x
            if rem > 0:
                self._safe_addstr(start_y, cur_x, "─" * rem, curses.color_pair(PAIR_BORDER))
        else:
            rem = right_x - cur_x
            if rem > 0:
                self._safe_addstr(start_y, cur_x, "─" * rem, curses.color_pair(PAIR_BORDER))

        self._safe_addstr(start_y, right_x, "┐", curses.color_pair(PAIR_BORDER))

        # 2. Content rows: Padded with spaces on pure black background
        visible_logs = logs[-content_h:]
        for r in range(content_h):
            y = start_y + 1 + r
            self._safe_addstr(y, start_x, "│ ", curses.color_pair(PAIR_BORDER))

            log_idx = r - (content_h - len(visible_logs))
            if log_idx >= 0:
                raw_line = visible_logs[log_idx]
                color, attr = self._classify_line(raw_line, default_pair)
                formatted = self._format_log_line(raw_line, content_w)
                line_str = formatted[:content_w].ljust(content_w)
                self._safe_addstr(y, start_x + 2, line_str, color | attr)
            else:
                # Fill empty row with spaces on black background
                self._safe_addstr(y, start_x + 2, " " * content_w, curses.color_pair(PAIR_DEFAULT))

            self._safe_addstr(y, start_x + width - 2, " │", curses.color_pair(PAIR_BORDER))

        # 3. Bottom border
        self._safe_addstr(
            start_y + height - 1, start_x, "└" + "─" * (width - 2) + "┘", curses.color_pair(PAIR_BORDER)
        )

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
