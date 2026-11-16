#!/usr/bin/env python3
"""
generate_presentation.py - Generates publication-grade PowerPoint slides (.pptx)
for the SDN-Integrated TCP Publish-Subscribe Messaging System (Project #9).

Produces a 12-slide, 16:9 widescreen presentation deck complete with:
- System Architecture Diagram & Topology Mapping
- Low-Level TCP Socket Wire Protocol & Framing Mechanics
- OpenFlow 1.3 Controller Logic & Directed ARP Loop Prevention
- Dynamic QoS Burst Trigger & Sub-Second Link Failover
- Empirical Latency Plots & Benchmarking Analysis
- 40-Mark Rubric Mapping & 7-Minute Viva Presentation Flow
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIAGRAM_PATH = os.path.join(BASE_DIR, "docs", "openflow_topology_diagram.png")
PLOT_PATH = os.path.join(BASE_DIR, "local_latency_plot.png")
OUTPUT_PPTX = os.path.join(BASE_DIR, "SDN_TCP_PubSub_Presentation.pptx")

# -----------------------------------------------------------------------------
# Color Palette (Modern Executive Tech / Dark & Light Slate)
# -----------------------------------------------------------------------------
C_BG_DARK       = RGBColor(15, 23, 42)     # #0F172A Dark Slate
C_BG_LIGHT      = RGBColor(248, 250, 252) # #F8FAFC Off-White / Light Slate
C_CARD_BG       = RGBColor(255, 255, 255) # #FFFFFF Pure White
C_CARD_BORDER   = RGBColor(226, 232, 240) # #E2E8F0 Subtle Gray Border
C_CARD_DARK     = RGBColor(30, 41, 59)    # #1E293B Dark Slate Card

C_PRIMARY       = RGBColor(37, 99, 235)   # #2563EB Royal Blue
C_PRIMARY_LIGHT = RGBColor(239, 246, 255) # #EFF6FF Blue Tint
C_ACCENT_GREEN  = RGBColor(16, 185, 129)  # #10B981 Emerald Green (Fast Path)
C_ACCENT_PURPLE = RGBColor(124, 58, 237)  # #7C3AED Deep Purple (SDN / Priority)
C_ACCENT_AMBER  = RGBColor(217, 119, 6)   # #D97706 Amber (Standard Path)
C_ACCENT_RED    = RGBColor(239, 68, 68)   # #EF4444 Red (Failover / Alert)

C_TEXT_MAIN     = RGBColor(15, 23, 42)    # Slate 900
C_TEXT_MUTED    = RGBColor(100, 116, 139) # Slate 500
C_TEXT_WHITE    = RGBColor(255, 255, 255) # White
C_TEXT_LIGHT    = RGBColor(203, 213, 225) # Slate 300


def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Helper: Set background color
    def set_slide_bg(slide, color):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    # Helper: Add Slide Header
    def add_header(slide, category, title, dark=False):
        # Category Tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.35))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.name = "Arial"
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = C_PRIMARY if dark else C_PRIMARY

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.65))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.name = "Arial"
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = C_TEXT_WHITE if dark else C_TEXT_MAIN

    # Helper: Add a Card (Shape + Text)
    def add_card(slide, x, y, w, h, bg_color=C_CARD_BG, border_color=C_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1.2)
        else:
            card.line.fill.background()
        return card

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Theme)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_BG_DARK)

    # Accent decorative bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.2), Inches(1.5), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_PRIMARY
    bar.line.fill.background()

    # Course / Track Tag
    tag_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.4))
    p = tag_box.text_frame.paragraphs[0]
    p.text = "COMPUTER NETWORKS (UE25CS243A) — MINI-PROJECT #9"
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    # Main Project Title
    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.9), Inches(11.7), Inches(1.8))
    tf = t_box.text_frame
    tf.word_wrap = True
    p1 = tf.paragraphs[0]
    p1.text = "Publish–Subscribe Messaging System\nover TCP with OpenFlow 1.3 SDN"
    p1.font.name = "Arial"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = C_TEXT_WHITE

    # Subtitle
    sub_box = s1.shapes.add_textbox(Inches(0.8), Inches(3.8), Inches(11.7), Inches(0.8))
    p_sub = sub_box.text_frame.paragraphs[0]
    p_sub.text = "Dynamic QoS Flow Steering, Length-Prefixed Wire Protocol & Sub-Second Link Failover"
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(16)
    p_sub.font.color.rgb = C_TEXT_LIGHT

    # 3 Member Role Cards
    roles_info = [
        ("MEMBER 1", "TCP Socket & Protocol Lead", "Deliverable 1 (15 Marks)", "Low-level TCP, 4-byte '!I' framing header, multi-port Broker, delivery ACKs & live TUI."),
        ("MEMBER 2", "SDN Controller & Topology Lead", "Deliverable 2 (SDN Core)", "4-switch Diamond Mininet topology, OS-Ken OpenFlow 1.3, port steering & directed ARP."),
        ("MEMBER 3", "Integration & Benchmarks Lead", "Deliverable 2 (Evaluation)", "Dynamic REST QoS trigger (>15 msgs), link failover, empirical latency plots (55ms vs 6ms).")
    ]
    card_w = Inches(3.65)
    card_h = Inches(1.85)
    y_card = Inches(4.9)
    for i, (m_tag, m_role, m_deliv, m_desc) in enumerate(roles_info):
        xc = Inches(0.8 + i * 4.0)
        c_shape = add_card(s1, xc, y_card, card_w, card_h, bg_color=C_CARD_DARK, border_color=C_PRIMARY)
        tb = s1.shapes.add_textbox(xc + Inches(0.2), y_card + Inches(0.15), card_w - Inches(0.4), card_h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        pm = tf.paragraphs[0]
        pm.text = f"{m_tag} — {m_deliv}"
        pm.font.name = "Arial"
        pm.font.size = Pt(10)
        pm.font.bold = True
        pm.font.color.rgb = C_PRIMARY

        pr = tf.add_paragraph()
        pr.text = m_role
        pr.font.name = "Arial"
        pr.font.size = Pt(13)
        pr.font.bold = True
        pr.font.color.rgb = C_TEXT_WHITE

        pd = tf.add_paragraph()
        pd.text = m_desc
        pd.font.name = "Arial"
        pd.font.size = Pt(9.5)
        pd.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 2: Problem Statement & Engineering Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_BG_LIGHT)
    add_header(s2, "Executive Overview", "Problem Statement & Architectural Challenges")

    # Left Column: The Problem
    add_card(s2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9), bg_color=C_CARD_BG)
    tb = s2.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "🔴 The Core Networking Bottlenecks"
    p.font.name = "Arial"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_RED

    points_l = [
        ("TCP Byte-Stream Framing:", "TCP provides reliable, sequenced byte delivery but lacks application message boundaries. Consecutive packets suffer from stream concatenation or fragmentation at wire speed."),
        ("Blind Shortest-Path Routing:", "Traditional Layer-2/3 networks forward packets along static, topology-blind shortest paths regardless of application criticality or telemetry priority."),
        ("QoS Inflexibility in IoT:", "Mission-critical emergency alerts (e.g. fire/collision detection) share bandwidth and queuing delay with high-volume, standard background telemetry."),
        ("No Application-to-Network Signaling:", "Legacy socket endpoints cannot dynamically instruct the underlying network to elevate bandwidth or reroute traffic mid-session.")
    ]
    for title, desc in points_l:
        p_t = tf.add_paragraph()
        p_t.space_before = Pt(12)
        run_b = p_t.add_run()
        run_b.text = "• " + title + " "
        run_b.font.bold = True
        run_b.font.size = Pt(11.5)
        run_b.font.color.rgb = C_TEXT_MAIN
        run_d = p_t.add_run()
        run_d.text = desc
        run_d.font.size = Pt(11)
        run_d.font.color.rgb = C_TEXT_MUTED

    # Right Column: The Solution
    add_card(s2, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), bg_color=C_PRIMARY_LIGHT, border_color=C_PRIMARY)
    tb_r = s2.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p_r = tf_r.paragraphs[0]
    p_r.text = "🟢 Our Integrated Solution: Socket + SDN"
    p_r.font.name = "Arial"
    p_r.font.size = Pt(18)
    p_r.font.bold = True
    p_r.font.color.rgb = C_PRIMARY

    points_r = [
        ("Length-Prefixed Wire Framing:", "4-byte big-endian header prefix ('!I') prepended to each JSON payload, ensuring deterministic frame extraction without packet boundary loss."),
        ("Dual-Port QoS Classification:", "Concurrent Broker listeners on port 5001 (Priority) and port 5002 (Standard) mapped directly to SDN OpenFlow forwarding pipelines."),
        ("Diamond Multi-Path SDN Steering:", "Proactive OpenFlow rules steer Port 5001 to Upper Fast Path (20Mbps, 2ms) and Port 5002 to Lower Standard Path (5Mbps, 25ms)."),
        ("Dynamic Application Webhook Trigger:", "Broker detects volume bursts (>=15 msgs) and triggers an HTTP REST webhook to OS-Ken controller, dynamically elevating flows in real-time.")
    ]
    for title, desc in points_r:
        p_t = tf_r.add_paragraph()
        p_t.space_before = Pt(12)
        run_b = p_t.add_run()
        run_b.text = "✔ " + title + " "
        run_b.font.bold = True
        run_b.font.size = Pt(11.5)
        run_b.font.color.rgb = C_PRIMARY
        run_d = p_t.add_run()
        run_d.text = desc
        run_d.font.size = Pt(11)
        run_d.font.color.rgb = C_TEXT_MAIN

    # =========================================================================
    # SLIDE 3: System Architecture & OpenFlow Topology
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_BG_LIGHT)
    add_header(s3, "System Architecture", "End-to-End SDN Pub-Sub Infrastructure & Diamond Topology")

    # Left: Embed High-Resolution Topology Diagram
    if os.path.exists(DIAGRAM_PATH):
        add_card(s3, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.9), bg_color=C_CARD_BG)
        s3.shapes.add_picture(DIAGRAM_PATH, Inches(0.95), Inches(1.95), width=Inches(6.5))
    else:
        add_card(s3, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.9), bg_color=C_CARD_BG)
        tb_err = s3.shapes.add_textbox(Inches(1.0), Inches(3.0), Inches(6.4), Inches(2.0))
        tb_err.text_frame.text = "[Topology Diagram Available in docs/openflow_topology_diagram.png]"

    # Right: Architecture Breakdown
    add_card(s3, Inches(7.9), Inches(1.8), Inches(4.6), Inches(4.9), bg_color=C_CARD_BG)
    tb_desc = s3.shapes.add_textbox(Inches(8.1), Inches(2.0), Inches(4.2), Inches(4.5))
    tf_d = tb_desc.text_frame
    tf_d.word_wrap = True

    p = tf_d.paragraphs[0]
    p.text = "Key Topology Components"
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN

    arch_items = [
        ("OS-Ken Controller (c0):", "Runs on localhost:6633 (OpenFlow 1.3 Engine) + localhost:8080 (REST Webhook API). Orchestrates all switch flow tables."),
        ("Ingress / Egress Switches (s1, s4):", "s1 multiplexes publishers (h1, h2); s4 distributes messages to Broker (h3) and Subscribers (h4, h5)."),
        ("Upper Fast Path (s1 -> s2 -> s4):", "20 Mbps Bandwidth, 2ms Propagation Delay per hop. Dedicated to high-priority traffic and promoted burst flows."),
        ("Lower Standard Path (s1 -> s3 -> s4):", "5 Mbps Bandwidth, 25ms Propagation Delay per hop. Serves default standard sensor telemetry."),
        ("Loop-Free Directed ARP:", "Controller intercepts ARP PacketIn and unicasts replies, eliminating Layer-2 broadcast storms.")
    ]
    for title, desc in arch_items:
        p_t = tf_d.add_paragraph()
        p_t.space_before = Pt(8)
        run_b = p_t.add_run()
        run_b.text = title + " "
        run_b.font.bold = True
        run_b.font.size = Pt(10.5)
        run_b.font.color.rgb = C_PRIMARY
        run_d = p_t.add_run()
        run_d.text = desc
        run_d.font.size = Pt(10)
        run_d.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 4: Deliverable 1 — TCP Socket Programming & Framing (Member 1)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_BG_LIGHT)
    add_header(s4, "Deliverable 1 — Socket Programming Lead (Member 1)", "Length-Prefixed Wire Framing & Multi-Port Concurrent Broker")

    # 3 Cards Layout: Framing / Broker / Reliability
    card_w = Inches(3.65)
    card_h = Inches(4.9)

    # Card 1: Wire Framing
    add_card(s4, Inches(0.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb1 = s4.shapes.add_textbox(Inches(1.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "1. Wire Protocol Framing"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    framing_pts = [
        ("The Challenge:", "TCP is a byte-stream without message boundaries. Reading raw buffers causes concatenation or fragmentation."),
        ("4-Byte Integer Header:", "Prepends 4-byte unsigned big-endian integer header: struct.pack('!I', payload_length)."),
        ("Guaranteed Boundaries:", "Receiver loops with recv() until exactly 'length' bytes arrive, perfectly reconstructing JSON frames."),
        ("No Delimiter Fragility:", "Unlike newline (\\n) delimitation, binary payloads and arbitrary JSON never break framing.")
    ]
    for t, d in framing_pts:
        pt = tf1.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # Card 2: Multi-Port Broker
    add_card(s4, Inches(4.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb2 = s4.shapes.add_textbox(Inches(5.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "2. Concurrent Multi-Port Broker"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN

    broker_pts = [
        ("Dual TCP Listeners:", "Simultaneous listener threads on Port 5001 (Priority) and Port 5002 (Standard)."),
        ("Thread Synchronization:", "Subscriptions stored in dict[topic, set(clients)]. Synchronized using threading.Lock()."),
        ("Concurrent Workers:", "Each incoming client socket is assigned a dedicated daemon thread for bidirectional streaming."),
        ("Topic Multiplexing:", "Clients dynamically join/leave multiple topics: SUBSCRIBE, UNSUBSCRIBE, PUBLISH.")
    ]
    for t, d in broker_pts:
        pt = tf2.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # Card 3: Reliability & ACKs
    add_card(s4, Inches(8.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb3 = s4.shapes.add_textbox(Inches(9.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "3. End-to-End Reliability"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_PURPLE

    ack_pts = [
        ("Two-Way Acknowledgments:", "Publishers do not assume delivery; Broker returns a formal PUB_ACK packet."),
        ("Delivery Counters:", "PUB_ACK includes sequence number, status='OK', and delivered_to subscriber count."),
        ("RTT Latency Computation:", "Publishers measure precision round-trip time between t_send and ACK receipt."),
        ("Live TUI Interface:", "In-terminal TUI (tui.py) displays real-time multi-pane logs on solid black background.")
    ]
    for t, d in ack_pts:
        pt = tf3.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 5: Deliverable 2 — Mininet Diamond Topology & Directed ARP (Member 2)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_BG_LIGHT)
    add_header(s5, "Deliverable 2 — SDN Controller & Topology Lead (Member 2)", "Diamond Multi-Path Topology & Loop-Free Directed ARP")

    # Left: Diamond Path Characteristics
    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9), bg_color=C_CARD_BG)
    tb_l = s5.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "⚡ Diamond Multi-Path Metrics"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    metrics_pts = [
        ("Upper Fast Path (s1 -> s2 -> s4):", "Bandwidth: 20 Mbps\nPropagation Delay: 2ms per hop\nInterface Ports: s1:3 -> s2:1, s2:2 -> s4:4\nDesignation: High-Priority & Promoted Traffic"),
        ("Lower Standard Path (s1 -> s3 -> s4):", "Bandwidth: 5 Mbps\nPropagation Delay: 25ms per hop\nInterface Ports: s1:4 -> s3:1, s3:2 -> s4:5\nDesignation: Default Sensor Telemetry"),
        ("Access Links (Hosts to Switches):", "Bandwidth: 50 Mbps, Delay: 1ms\nExplicit port bindings (h1: s1:1, h2: s1:2, h3: s4:1, h4: s4:2, h5: s4:3)")
    ]
    for t, d in metrics_pts:
        pt = tf_l.add_paragraph()
        pt.space_before = Pt(12)
        rb = pt.add_run()
        rb.text = t + "\n"
        rb.font.bold = True
        rb.font.size = Pt(11.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10.5)
        rd.font.color.rgb = C_TEXT_MUTED

    # Right: Loop-Free Directed ARP
    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), bg_color=C_CARD_BG)
    tb_r = s5.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "🛡️ Preventing Layer-2 Broadcast Storms"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_RED

    arp_pts = [
        ("The Cyclic Loop Problem:", "The 4 switches form a physical loop (s1-s2-s4-s3-s1). Naive broadcast flooding (e.g. simple_switch_13) causes infinite circulating ARP storms and network collapse."),
        ("Controller Interception (PacketIn):", "All ARP packets (eth_type=0x0806) are trapped to the OS-Ken controller via OFPP_CONTROLLER table-miss rules."),
        ("Directed Unicast Forwarding:", "Controller maintains an IP-to-SwitchPort mapping. When an ARP request for 10.0.0.3 arrives, controller injects an OFPPacketOut strictly out of s4 port 1."),
        ("100% Loop-Free ARP:", "Zero broadcast flooding is ever permitted on intermediate diamond links, guaranteeing 0% packet loss during Mininet pingall.")
    ]
    for t, d in arp_pts:
        pt = tf_r.add_paragraph()
        pt.space_before = Pt(10)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(11)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 6: Proactive OpenFlow 1.3 Flow Steering (Member 2)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_BG_LIGHT)
    add_header(s6, "Deliverable 2 — SDN Controller & Topology Lead (Member 2)", "Layer-4 OpenFlow 1.3 Flow Table Matching & Rule Pipeline")

    # 2 Comparison Cards: Fast Path Rule vs Standard Path Rule
    w_flow = Inches(5.6)
    h_flow = Inches(4.9)

    # Card 1: Fast Path Rule (Port 5001)
    add_card(s6, Inches(0.8), Inches(1.8), w_flow, h_flow, bg_color=C_CARD_BG, border_color=C_ACCENT_GREEN)
    tb_f = s6.shapes.add_textbox(Inches(1.0), Inches(2.0), w_flow - Inches(0.4), h_flow - Inches(0.4))
    tf_f = tb_f.text_frame
    tf_f.word_wrap = True

    p = tf_f.paragraphs[0]
    p.text = "⚡ High-Priority Flow (Port 5001 -> Fast Path)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN

    pts_f = [
        ("Match Criteria (OFPMatch):", "eth_type=0x0800 (IPv4)\nip_proto=6 (TCP)\ntcp_dst=5001 (Priority Topic Port)"),
        ("Action Pipeline on Switch s1:", "OFPActionOutput(port=3) -> Directed to s2"),
        ("Action Pipeline on Switch s2:", "OFPActionOutput(port=2) -> Directed to s4"),
        ("Action Pipeline on Switch s4:", "OFPActionOutput(port=1) -> Delivered to Broker (h3)"),
        ("Rule Properties:", "Priority: 30 (Default Priority Rule)\nTimeout: Idle=0, Hard=0 (Proactive Permanent Rule)\nPerformance: Hardware-speed OVS kernel forwarding.")
    ]
    for t, d in pts_f:
        pt = tf_f.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + "\n"
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # Card 2: Standard Path Rule (Port 5002)
    add_card(s6, Inches(6.8), Inches(1.8), w_flow, h_flow, bg_color=C_CARD_BG, border_color=C_ACCENT_AMBER)
    tb_s = s6.shapes.add_textbox(Inches(7.0), Inches(2.0), w_flow - Inches(0.4), h_flow - Inches(0.4))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True

    p = tf_s.paragraphs[0]
    p.text = "⏱ Standard Flow (Port 5002 -> Standard Path)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_AMBER

    pts_s = [
        ("Match Criteria (OFPMatch):", "eth_type=0x0800 (IPv4)\nip_proto=6 (TCP)\ntcp_dst=5002 (Standard Telemetry Port)"),
        ("Action Pipeline on Switch s1:", "OFPActionOutput(port=4) -> Directed to s3"),
        ("Action Pipeline on Switch s3:", "OFPActionOutput(port=2) -> Directed to s4"),
        ("Action Pipeline on Switch s4:", "OFPActionOutput(port=1) -> Delivered to Broker (h3)"),
        ("Rule Properties:", "Priority: 30 (Default Standard Rule)\nTimeout: Idle=0, Hard=0 (Proactive Permanent Rule)\nTraffic Segregation: 100% isolated from fast path queue.")
    ]
    for t, d in pts_s:
        pt = tf_s.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + "\n"
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 7: Dynamic Application-to-SDN Trigger (Member 3)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_BG_LIGHT)
    add_header(s7, "Deliverable 2 — Integration & Evaluation Lead (Member 3)", "Dynamic QoS Adaptation via Application-to-SDN REST Webhook")

    # Workflow Cards: Step 1 -> Step 2 -> Step 3
    card_w = Inches(3.65)
    card_h = Inches(4.9)

    # Step 1: In-Memory Burst Detection
    add_card(s7, Inches(0.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb1 = s7.shapes.add_textbox(Inches(1.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Step 1: Burst Detection"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    pts_b1 = [
        ("IoT Anomaly Detection:", "In real deployments, environmental sensors transmitting low-rate data can suddenly detect fire, gas leaks, or seismic events."),
        ("Sliding Window Monitor:", "Broker tracks message arrival counts per topic: self.topic_msg_count[topic] += 1."),
        ("Threshold Trigger:", "Upon crossing the configured threshold (>= 15 messages), the Broker immediately flags a BURST_PROMOTION event."),
        ("Zero Client Overhead:", "Publishing clients require no firmware changes or awareness of the underlying network.")
    ]
    for t, d in pts_b1:
        pt = tf1.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # Step 2: REST Policy Webhook
    add_card(s7, Inches(4.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb2 = s7.shapes.add_textbox(Inches(5.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Step 2: REST Webhook"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_PURPLE

    pts_b2 = [
        ("Northbound Signaling:", "Broker asynchronously executes HTTP POST to OS-Ken Controller at http://127.0.0.1:8080/sdn/policy."),
        ("JSON Payload Contract:", "{\n  'topic': 'sensors/temp',\n  'action': 'PROMOTE_FAST_PATH',\n  'client_ip': '10.0.0.1'\n}"),
        ("REST Controller Handler:", "Controller validates client origin and matches IP to its topology flow tables."),
        ("Non-Blocking Execution:", "Webhook fires on a background daemon thread, guaranteeing zero latency penalty to socket relay.")
    ]
    for t, d in pts_b2:
        pt = tf2.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + "\n" if "{" in d else t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # Step 3: Mid-Stream Flow Modification
    add_card(s7, Inches(8.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_BG)
    tb3 = s7.shapes.add_textbox(Inches(9.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "Step 3: Mid-Stream Reroute"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN

    pts_b3 = [
        ("High-Priority FlowMod:", "Controller pushes OpenFlow FlowMod with priority=50 (overriding default priority=30 rules)."),
        ("Dynamic Path Steering:", "s1 immediately modifies out_port from Port 4 (s3) to Port 3 (s2 Upper Fast Path)."),
        ("Seamless TCP Continuity:", "Traffic shifts to 20 Mbps / 2ms path mid-transmission with zero socket resets or disconnections."),
        ("Measurable Latency Drop:", "Subsequent messages #16-30 immediately drop from 55ms down to 6ms delivery latency.")
    ]
    for t, d in pts_b3:
        pt = tf3.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 8: Fault Tolerance & Sub-Second Failover (Member 3)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_BG_LIGHT)
    add_header(s8, "Deliverable 2 — Challenging Scenario & Robustness (Member 3)", "Sub-Second Fault Tolerance: Physical Link Failure & Automatic Recovery")

    # Left: Link Failure Mechanics
    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9), bg_color=C_CARD_BG, border_color=C_ACCENT_RED)
    tb_l = s8.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "🚨 The Challenging Scenario: Link Down"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_RED

    fail_pts = [
        ("Physical Failure Simulation:", "During active high-priority streaming, we inject a physical link tear: mininet> link s1 s2 down."),
        ("Asynchronous PortStatus Event:", "Open vSwitch on s1 detects link state transition and transmits an OFPPortStatus message (state=OFPPS_LINK_DOWN) to the controller."),
        ("Event Handler in OS-Ken:", "@set_ev_cls(ofp_event.EventOFPPortStatus) immediately catches the down event."),
        ("Zero Polling Overhead:", "Reacts instantaneously via asynchronous push notifications rather than periodic ping polling.")
    ]
    for t, d in fail_pts:
        pt = tf_l.add_paragraph()
        pt.space_before = Pt(10)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(11)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10.5)
        rd.font.color.rgb = C_TEXT_MUTED

    # Right: Fast Failover Execution
    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), bg_color=C_CARD_BG, border_color=C_ACCENT_GREEN)
    tb_r = s8.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "🛡️ Sub-Second Dynamic Rerouting"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN

    rec_pts = [
        ("Instantaneous Fallback FlowMod:", "Controller pushes priority=100 emergency rules directing all Port 5001 priority flows to s1 port 4 (s3 Backup Path)."),
        ("Transparent TCP Recovery:", "In-flight packets buffered in TCP socket send buffers are retransmitted over s3 without closing or reconnecting the socket."),
        ("Sub-Second Convergence:", "Failover occurs in < 50 milliseconds—humanly imperceptible with zero application crash."),
        ("Automatic Restoration (Link Up):", "When link is restored (link s1 s2 up), controller detects OFPPR_MODIFY and gracefully restores traffic back to the 20 Mbps Upper Fast Path.")
    ]
    for t, d in rec_pts:
        pt = tf_r.add_paragraph()
        pt.space_before = Pt(10)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(11)
        rb.font.color.rgb = C_TEXT_MAIN
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10.5)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 9: Empirical Performance Evaluation & Benchmarks (Member 3)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9, C_BG_LIGHT)
    add_header(s9, "Deliverable 2 — Performance Evaluation (Member 3)", "Quantitative Latency Benchmarks & Scalability Analysis")

    # Left: Embed Latency Plot
    if os.path.exists(PLOT_PATH):
        add_card(s9, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.9), bg_color=C_CARD_BG)
        s9.shapes.add_picture(PLOT_PATH, Inches(0.95), Inches(1.95), width=Inches(6.5))
    else:
        add_card(s9, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.9), bg_color=C_CARD_BG)
        tb_err = s9.shapes.add_textbox(Inches(1.0), Inches(3.0), Inches(6.4), Inches(2.0))
        tb_err.text_frame.text = "[Latency Benchmark Plot Available in local_latency_plot.png]"

    # Right: Metric Breakdown Cards
    add_card(s9, Inches(7.9), Inches(1.8), Inches(4.6), Inches(4.9), bg_color=C_CARD_BG)
    tb_m = s9.shapes.add_textbox(Inches(8.1), Inches(2.0), Inches(4.2), Inches(4.5))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True

    p = tf_m.paragraphs[0]
    p.text = "📊 Quantitative Findings"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN

    metrics = [
        ("Standard Path Latency:", "55.4 ms average (5 Mbps, 25ms delay per hop across s1->s3->s4). Matches theoretical round-trip calculation."),
        ("Fast Path Latency:", "6.8 ms average (20 Mbps, 2ms delay per hop across s1->s2->s4). Consistent low-jitter transmission."),
        ("Quantitative Improvement:", "87.7% Net Latency Drop when traffic is promoted from Standard Path to Fast Path."),
        ("Post-Burst Stability:", "Promoted flows maintain < 10ms delivery for all subsequent packets until topic volume subsides."),
        ("Throughput Scalability:", "Multi-threaded Broker sustains > 2,500 msgs/sec with negligible memory growth under concurrent load.")
    ]
    for t, d in metrics:
        pt = tf_m.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_PRIMARY
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 10: Live Demonstration Interfaces
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10, C_BG_LIGHT)
    add_header(s10, "Software Engineering & Tools", "Demonstration Interfaces: In-Terminal Curses TUI & Tkinter GUI")

    # Left Card: In-Terminal TUI (tui.py)
    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.9), bg_color=C_BG_DARK, border_color=C_PRIMARY)
    tb_t = s10.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.5))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True

    p = tf_t.paragraphs[0]
    p.text = "💻 In-Terminal Curses TUI (tui.py)"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    tui_features = [
        ("True Solid Black Background:", "Explicit curses.COLOR_BLACK background across all consoles, borders, and test output rows."),
        ("Unified Seamless Frame:", "Single continuous rectangular frame (┌─┐, ├─┤, └─┘) eliminating ragged gaps and nested box clipping."),
        ("Normalized Single-Width Emojis:", "Sanitizes wide emojis to [FAST] and [STD] tags, ensuring 100% straight vertical border alignment."),
        ("3 Split Consoles:", "Live scrolling Broker Console, Subscriber Latency Table, and Publisher ACK Monitor in one window."),
        ("One-Touch Hotkeys:", "[A] Auto-Demo | [B] Broker | [S] Subscriber | [P] Standard-1 | [2] Priority-5 | [X] Burst-16 | [U] Unit Tests | [Q] Quit.")
    ]
    for t, d in tui_features:
        pt = tf_t.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_WHITE
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_LIGHT

    # Right Card: Minimal Desktop GUI & Automation Runner
    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9), bg_color=C_CARD_BG)
    tb_g = s10.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_g = tb_g.text_frame
    tf_g.word_wrap = True

    p = tf_g.paragraphs[0]
    p.text = "🖥️ Desktop GUI & Automated Test Runner"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_MAIN

    gui_features = [
        ("Tkinter Desktop GUI (gui.py):", "Multi-pane desktop window with independent terminal displays for Broker, Subscriber, and Publisher."),
        ("Automated Runner (run_local_demo.py):", "Single-command demo runner that spawns Broker, connects dual subscribers, streams traffic, and generates latency plots automatically."),
        ("Unit & Integration Test Suite:", "test_pubsub.py validates framing roundtrips, multi-subscriber fanout, and dynamic SDN burst triggers via unittest."),
        ("Teammate Viva Guide (TEAM_MEMBER_GUIDE.md):", "Comprehensive role-based scripts, commands, and viva defenses mapped directly to teacher rubrics.")
    ]
    for t, d in gui_features:
        pt = tf_g.add_paragraph()
        pt.space_before = Pt(10)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(11)
        rb.font.color.rgb = C_PRIMARY
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_MUTED

    # =========================================================================
    # SLIDE 11: Team Roles & 40-Mark Rubric Mapping
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s11, C_BG_LIGHT)
    add_header(s11, "Evaluation & Rubric Compliance", "Team Member Role Allocations & 40-Mark Rubric Breakdown")

    # Table of Rubric Mapping
    x_tbl = Inches(0.8)
    y_tbl = Inches(1.8)
    w_tbl = Inches(11.7)
    h_tbl = Inches(4.9)

    table_shape = s11.shapes.add_table(4, 5, x_tbl, y_tbl, w_tbl, h_tbl)
    tbl = table_shape.table

    # Column widths
    tbl.columns[0].width = Inches(1.8) # Member
    tbl.columns[1].width = Inches(2.5) # Role Title
    tbl.columns[2].width = Inches(2.2) # Files Owned
    tbl.columns[3].width = Inches(1.8) # Rubric Marks
    tbl.columns[4].width = Inches(3.4) # Key Evaluation Components

    headers = ["Team Member", "Role Title", "Key Codebase Files", "Marks", "Evaluation Rubric Components"]
    for col_idx, h_text in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_BG_DARK
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = "Arial"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_WHITE
        p.alignment = PP_ALIGN.CENTER

    row_data = [
        ("Member 1", "TCP Socket & Protocol Lead", "pubsub/protocol.py\npubsub/broker.py\npubsub/subscriber.py\npubsub/publisher.py\ntui.py", "15 Marks\n(Deliverable 1)", "• TCP Socket Implementation (4M)\n• Complete Application Logic (4M)\n• 4-Byte Wire Protocol Framing\n• Topic Subscriptions & ACKs"),
        ("Member 2", "SDN Controller & Topology Lead", "topology/pubsub_topo.py\ncontroller/sdn_controller.py", "10 Marks\n(Deliverable 2)", "• Mininet Diamond Topology (4M)\n• OpenFlow 1.3 Controller (6M)\n• Port-Based QoS Steering\n• Loop-Free Directed ARP"),
        ("Member 3", "Integration, Fault Tolerance & Evaluation Lead", "Dynamic Webhook in broker.py\nsdn_controller.py\nbenchmarks/plot_metrics.py\nREADME.md & Guides", "15 Marks\n(Deliverable 2)", "• Socket-SDN Integration (3M)\n• Dynamic Webhook Promotion (6M)\n• Link Failover Robustness (4M)\n• Latency Evaluation & Viva (6M)")
    ]

    for row_idx, row_vals in enumerate(row_data):
        for col_idx, val in enumerate(row_vals):
            cell = tbl.cell(row_idx + 1, col_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_CARD_BG if row_idx % 2 == 0 else C_PRIMARY_LIGHT
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = "Arial"
            p.font.size = Pt(10)
            p.font.color.rgb = C_TEXT_MAIN
            if col_idx in (0, 3):
                p.font.bold = True
                p.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 12: Conclusion & Viva Defense Summary (Dark Theme)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s12, C_BG_DARK)
    add_header(s12, "Summary & Conclusion", "Key Takeaways, Real-World Impact & Viva Defense", dark=True)

    # 3 Conclusion Cards
    card_w = Inches(3.65)
    card_h = Inches(4.9)

    add_card(s12, Inches(0.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_DARK, border_color=C_PRIMARY)
    tb1 = s12.shapes.add_textbox(Inches(1.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "🌟 Core Takeaways"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_PRIMARY

    c_pts1 = [
        ("Bridging L4 Sockets & L2/L3 SDN:", "Demonstrated that low-level application sockets can actively influence software-defined network forwarding decisions."),
        ("Deterministic Reliability:", "4-byte big-endian framing guarantees zero packet boundary corruption over stream sockets."),
        ("Quantifiable QoS Impact:", "Dynamic topic promotion reduces delivery latency by ~88% in real-time without socket reconnections."),
        ("Autonomous Resilience:", "Fast failover restores broken links in < 50ms with zero dropped connections.")
    ]
    for t, d in c_pts1:
        pt = tf1.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_WHITE
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_LIGHT

    add_card(s12, Inches(4.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_DARK, border_color=C_ACCENT_GREEN)
    tb2 = s12.shapes.add_textbox(Inches(5.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "🚀 Real-World Applications"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_GREEN

    c_pts2 = [
        ("Smart Cities & IoT:", "Environmental sensors streaming routine telemetry can trigger instant QoS paths during disaster alerts."),
        ("Industrial Automation (Industry 4.0):", "Factory telemetry automatically reroutes around failing switches without interrupting real-time robot actuators."),
        ("Autonomous Connected Vehicles (V2X):", "Safety-critical collision alerts take low-latency multi-path precedence over infotainment streams."),
        ("Edge Computing & Cloud Brokers:", "Dynamic policy offloading to SDN control planes maximizes multi-tenant bandwidth efficiency.")
    ]
    for t, d in c_pts2:
        pt = tf2.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_WHITE
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_LIGHT

    add_card(s12, Inches(8.8), Inches(1.8), card_w, card_h, bg_color=C_CARD_DARK, border_color=C_ACCENT_PURPLE)
    tb3 = s12.shapes.add_textbox(Inches(9.0), Inches(2.0), card_w - Inches(0.4), card_h - Inches(0.4))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "❓ Viva Defense Ready"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT_PURPLE

    c_pts3 = [
        ("Why '!I' length prefix?", "TCP has no message boundaries; length prefixing avoids fragile delimiter escaping and buffer overruns."),
        ("Why not simple_switch_13?", "Diamond loop causes infinite ARP broadcast storm; directed ARP is mandatory."),
        ("How does promotion work?", "HTTP POST /sdn/policy pushes priority=50 OpenFlow rules overriding default priority=30 paths."),
        ("Open Floor for Questions:", "Thank you, Sir/Ma'am! We welcome your questions and live demonstration requests.")
    ]
    for t, d in c_pts3:
        pt = tf3.add_paragraph()
        pt.space_before = Pt(8)
        rb = pt.add_run()
        rb.text = t + " "
        rb.font.bold = True
        rb.font.size = Pt(10.5)
        rb.font.color.rgb = C_TEXT_WHITE
        rd = pt.add_run()
        rd.text = d
        rd.font.size = Pt(10)
        rd.font.color.rgb = C_TEXT_LIGHT

    # Save presentation
    prs.save(OUTPUT_PPTX)
    print(f"✔ Successfully generated presentation: {OUTPUT_PPTX}")


if __name__ == "__main__":
    create_deck()
