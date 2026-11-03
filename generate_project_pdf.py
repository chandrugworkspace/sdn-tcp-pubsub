"""
generate_project_pdf.py - Generates a publication-grade PDF guide for teammates.

Uses ReportLab to produce a comprehensive, beautifully styled document covering:
- Architecture & Diamond Topology
- Team member role allocations & 40-mark rubric mapping
- Environment setup across Arch, Ubuntu VM, and macOS
- Step-by-step execution instructions for Member 1, 2, and 3
- Viva preparation questions and answers
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically and adds running headers & footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Publish–Subscribe Messaging System over TCP with SDN — Team Handbook")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "UE25CS243A: Computer Networks Mini Project | Project #9")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom palette
    PRIMARY = colors.HexColor("#1E3A8A")     # Deep Blue
    SECONDARY = colors.HexColor("#0284C7")   # Sky Blue
    DARK_TEXT = colors.HexColor("#0F172A")   # Slate 900
    MUTED_TEXT = colors.HexColor("#475569")  # Slate 600
    BG_LIGHT = colors.HexColor("#F8FAFC")    # Slate 50
    ACCENT_GREEN = colors.HexColor("#16A34A")# Emerald Green
    ACCENT_AMBER = colors.HexColor("#D97706")# Amber
    BORDER_COLOR = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=PRIMARY,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=MUTED_TEXT,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=DARK_TEXT,
        spaceAfter=6
    )

    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=14,
        bulletIndent=4,
        spaceAfter=3
    )

    story = []

    # Title Block
    story.append(Paragraph("Publish–Subscribe Messaging System over TCP with SDN", title_style))
    story.append(Paragraph("Comprehensive Project Architecture, Role Allocation & Execution Guide for Team Members", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=14))

    # Meta Info Card
    meta_data = [
        [
            Paragraph("<b>Course:</b> UE25CS243A — Computer Networks", body_style),
            Paragraph("<b>Track:</b> Project #9 (Socket + SDN)", body_style)
        ],
        [
            Paragraph("<b>Total Marks:</b> 40 (D1: 15M | D2: 25M)", body_style),
            Paragraph("<b>Team Size:</b> 3 Members", body_style)
        ],
        [
            Paragraph("<b>GitHub Repo:</b> github.com/chandrugworkspace/sdn-tcp-pubsub", body_style),
            Paragraph("<b>Architecture:</b> 4-Switch Diamond Multi-Path Topology", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Section 1: Executive Overview
    story.append(Paragraph("1. Project Overview & Architecture", h1_style))
    story.append(Paragraph(
        "This project implements an intelligent, reliable publish–subscribe messaging infrastructure combining "
        "<b>raw TCP socket programming</b> with an <b>OpenFlow 1.3 Software-Defined Networking (SDN) controller</b>. "
        "The centralized Broker handles multi-threaded client connections, topic subscriptions, and ACKs, while the SDN "
        "controller dynamically classifies topic traffic at wire speed and steers packets along distinct physical paths.",
        body_style
    ))

    # Topology Visual Table
    topo_data = [
        [Paragraph("<b>Path Component</b>", body_style), Paragraph("<b>Switch Route</b>", body_style), Paragraph("<b>Bandwidth & Latency</b>", body_style), Paragraph("<b>Traffic Assignment</b>", body_style)],
        [
            Paragraph("<b>Upper Fast Path</b>", body_style),
            Paragraph("s1 ➔ s2 ➔ s4", body_style),
            Paragraph("<b>20 Mbps</b> | 2 ms / hop (~8 ms end-to-end)", body_style),
            Paragraph("Port 5001 (Priority topics) & Dynamically Promoted bursts", body_style)
        ],
        [
            Paragraph("<b>Lower Standard Path</b>", body_style),
            Paragraph("s1 ➔ s3 ➔ s4", body_style),
            Paragraph("<b>5 Mbps</b> | 25 ms / hop (~58 ms end-to-end)", body_style),
            Paragraph("Port 5002 (Standard topics: sensors/temp)", body_style)
        ],
        [
            Paragraph("<b>Automatic Failover</b>", body_style),
            Paragraph("s1 ➔ s3 ➔ s4 (Backup)", body_style),
            Paragraph("Sub-second redirect via Priority 60 OpenFlow rules", body_style),
            Paragraph("Active whenever link s1–s2 goes DOWN (Zero dropped conns)", body_style)
        ]
    ]
    t_topo = Table(topo_data, colWidths=[110, 85, 155, 154])
    t_topo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_topo)
    story.append(Spacer(1, 10))

    # Section 2: Team Member Roles & Rubrics
    story.append(Paragraph("2. Team Member Ownership & Rubric Mapping (40 Marks)", h1_style))
    story.append(Paragraph(
        "Each team member owns specific codebase modules and covers dedicated components of the lab evaluation rubric:",
        body_style
    ))

    roles_data = [
        [
            Paragraph("<b>Member</b>", body_style),
            Paragraph("<b>Primary Role</b>", body_style),
            Paragraph("<b>Code Owned</b>", body_style),
            Paragraph("<b>Rubric Components Covered</b>", body_style)
        ],
        [
            Paragraph("<b>Member 1</b>", body_style),
            Paragraph("<b>TCP Socket & Pub–Sub Lead</b>", body_style),
            Paragraph("<code>pubsub/protocol.py</code><br/><code>pubsub/broker.py</code><br/><code>pubsub/subscriber.py</code><br/><code>pubsub/publisher.py</code>", code_style),
            Paragraph("• TCP/UDP Socket Implementation (4M)<br/>• Complete Pub-Sub Application (4M)<br/>• Framing, Threading & Reliability ACKs", body_style)
        ],
        [
            Paragraph("<b>Member 2</b>", body_style),
            Paragraph("<b>Mininet & SDN Controller Lead</b>", body_style),
            Paragraph("<code>topology/pubsub_topo.py</code><br/><code>controller/sdn_controller.py</code>", code_style),
            Paragraph("• Mininet Virtual Network Topology (4M)<br/>• OpenFlow 1.3 Controller Steering (6M)<br/>• Loop-Free Directed ARP", body_style)
        ],
        [
            Paragraph("<b>Member 3</b>", body_style),
            Paragraph("<b>Integration, Testing & Benchmarking Lead</b>", body_style),
            Paragraph("<code>benchmarks/plot_metrics.py</code><br/><code>run_local_demo.py</code><br/>Webhook Integration logic<br/><code>README.md</code>", code_style),
            Paragraph("• Problem Understanding & Architecture (2M)<br/>• Socket–SDN Webhook Integration (3M)<br/>• Robustness & Link Failover Demo (4M)<br/>• Quantitative Evaluation & Graphs (5M)<br/>• Documentation & Viva (6M)", body_style)
        ]
    ]
    t_roles = Table(roles_data, colWidths=[65, 115, 140, 184])
    t_roles.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_roles)
    story.append(Spacer(1, 14))

    # Page Break for Setup & Execution Guide
    story.append(PageBreak())

    # Section 3: Environment Setup
    story.append(Paragraph("3. Environment Setup by Operating System", h1_style))
    story.append(Paragraph(
        "All teammates should clone the shared GitHub repository first:<br/>"
        "<code>git clone https://github.com/chandrugworkspace/sdn-tcp-pubsub.git && cd sdn-tcp-pubsub</code>",
        body_style
    ))

    env_data = [
        [
            Paragraph("<b>OS Environment</b>", body_style),
            Paragraph("<b>Setup Steps & Commands</b>", body_style)
        ],
        [
            Paragraph("<b>CachyOS / Arch Linux</b><br/><i>(Native Execution)</i>", body_style),
            Paragraph(
                "<code>sudo pacman -Syu mininet openvswitch iproute2 iperf3 uv</code><br/>"
                "<code>sudo systemctl enable --now ovs-vswitchd</code><br/>"
                "<code>uv venv --python 3.11 .venv && source .venv/bin/activate.fish</code><br/>"
                "<code>VIRTUAL_ENV=.venv uv pip install -r requirements.txt</code>",
                code_style
            )
        ],
        [
            Paragraph("<b>Windows 10/11</b><br/><i>(Ubuntu 22.04 LTS VM)</i>", body_style),
            Paragraph(
                "<i>*Note: Use VirtualBox or VMware (standard WSL2 lacks OVS kernel modules)*</i><br/>"
                "<code>sudo apt update && sudo apt install mininet openvswitch-switch iproute2 git python3-venv -y</code><br/>"
                "<code>python3 -m venv .venv && source .venv/bin/activate</code><br/>"
                "<code>pip install -r requirements.txt</code>",
                code_style
            )
        ],
        [
            Paragraph("<b>macOS (Apple / Intel)</b><br/><i>(UTM / VMware Fusion)</i>", body_style),
            Paragraph(
                "Install an Ubuntu 22.04 LTS VM using UTM (free). Follow the exact same Ubuntu steps above.",
                body_style
            )
        ]
    ]
    t_env = Table(env_data, colWidths=[130, 374])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_env)
    story.append(Spacer(1, 14))

    # Section 4: Execution Guide by Role
    story.append(Paragraph("4. Step-by-Step Execution Guide by Role", h1_style))

    # Member 1 Execution Card
    story.append(Paragraph("A. Member 1: Standalone Socket Pub-Sub Testing (Deliverable 1)", h2_style))
    story.append(Paragraph(
        "Member 1 can test the entire Pub-Sub system without Mininet or root permissions across separate terminal tabs or with the automated runner:",
        body_style
    ))
    m1_box = [
        [Paragraph("<b>Fast 5-Second Automated Test:</b><br/><code>python3 run_local_demo.py</code>", code_style)],
        [Paragraph("<b>Interactive 4-Terminal Workflow:</b><br/>"
                   "• <b>Terminal 1 (Broker):</b> <code>python3 pubsub/broker.py --priority-port 5001 --std-port 5002</code><br/>"
                   "• <b>Terminal 2 (Subscriber 1):</b> <code>python3 pubsub/subscriber.py --port 5002 --topics sensors/temp --csv std.csv</code><br/>"
                   "• <b>Terminal 3 (Subscriber 2):</b> <code>python3 pubsub/subscriber.py --port 5001 --topics alerts/fire --csv prio.csv</code><br/>"
                   "• <b>Terminal 4 (Publisher):</b> <code>python3 pubsub/publisher.py --port 5002 --topic sensors/temp --count 20</code>", code_style)]
    ]
    t_m1 = Table(m1_box, colWidths=[504])
    t_m1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_m1)
    story.append(Spacer(1, 8))

    # Member 2 & 3 Execution Card
    story.append(Paragraph("B. Members 2 & 3: Mininet + SDN Controller Integration (Deliverable 2)", h2_style))
    story.append(Paragraph(
        "Demonstrates wire-speed flow classification, dynamic threshold promotion, and link-down failover:",
        body_style
    ))
    m2_box = [
        [Paragraph(
            "<b>1. Start Controller (Terminal 1):</b><br/>"
            "<code>.venv/bin/osken-manager --ofp-tcp-listen-port 6633 controller/sdn_controller.py</code><br/>"
            "<i>(Starts OpenFlow engine on port 6633 and built-in REST webhook API on port 8080)</i><br/><br/>"
            "<b>2. Launch Mininet Diamond Topology (Terminal 2):</b><br/>"
            "<code>sudo mn -c && sudo python3 topology/pubsub_topo.py</code><br/><br/>"
            "<b>3. Inside Mininet CLI:</b><br/>"
            "<code>mininet> pingall</code><br/>"
            "<code>mininet> h3 python3 pubsub/broker.py --sdn-url http://127.0.0.1:8080 > broker.log 2>&1 &</code><br/>"
            "<code>mininet> h4 python3 pubsub/subscriber.py --broker 10.0.0.3 --port 5002 --topics sensors/temp --csv std_latency.csv > sub.log 2>&1 &</code><br/>"
            "<code>mininet> h1 python3 pubsub/publisher.py --broker 10.0.0.3 --port 5002 --topic sensors/temp --count 25 --interval 0.3</code><br/><br/>"
            "<b>4. Observe Dynamic Promotion (Message #15):</b><br/>"
            "<code>mininet> sh tail -n 25 sub.log</code> ➔ Latency drops from <b>~58 ms</b> down to <b>~8 ms</b>!<br/><br/>"
            "<b>5. Demonstrate Link Failure & Fast Failover:</b><br/>"
            "<code>mininet> link s1 s2 down</code> ➔ Controller instantly switches traffic over s3 without dropping connection!<br/>"
            "<code>mininet> link s1 s2 up</code> ➔ Normal priority paths restored.<br/><br/>"
            "<b>6. Generate Benchmark Comparison Graph:</b><br/>"
            "<code>mininet> exit</code><br/>"
            "<code>python3 benchmarks/plot_metrics.py std_latency.csv prio_latency.csv latency_comparison.png</code>",
            code_style
        )]
    ]
    t_m2 = Table(m2_box, colWidths=[504])
    t_m2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_m2)
    story.append(Spacer(1, 14))

    # Page Break for Viva Preparation
    story.append(PageBreak())

    # Section 5: Viva Preparation
    story.append(Paragraph("5. Viva Examination Preparation & Technical Q&A", h1_style))
    story.append(Paragraph("Use these questions and model answers during Deliverable 1 and Deliverable 2 evaluations:", body_style))

    viva_items = [
        ("Member 1 (Socket Lead)",
         "Why use a 4-byte length prefix (!I) instead of string delimiters like newline (\\n)?",
         "TCP is a continuous byte-stream protocol without built-in message boundaries. A single recv(1024) call can "
         "contain half a message or three concatenated messages. The 4-byte unsigned integer prefix gives the exact byte length, "
         "allowing recv_exact() to reconstruct the JSON object without fragmentation or corruption."),

        ("Member 1 (Socket Lead)",
         "How does the Broker prevent concurrency race conditions when multiple clients connect?",
         "The Broker encapsulates subscription mutations inside a threading.Lock(). During message broadcasting, "
         "it takes a snapshot list copy list(self.subscriptions[topic]) so that new subscribers joining or leaving mid-broadcast "
         "never trigger dictionary mutation runtime errors."),

        ("Member 2 (SDN Lead)",
         "Why does the diamond topology require a custom controller instead of simple_switch_13?",
         "The 4 switches form a physical Layer-2 diamond loop (s1-s2-s4-s3-s1). Standard learning switches flood ARP packets, "
         "causing an infinite broadcast storm that saturates links. Our controller uses directed, loop-free ARP handling and installs "
         "explicit OpenFlow 1.3 flow rules directly."),

        ("Member 2 (SDN Lead)",
         "How are high-priority topics separated from standard topics at wire speed?",
         "Without performing slow deep packet inspection (DPI) on JSON payloads, the switches inspect Layer-4 destination TCP port "
         "numbers in hardware (OFPMatch tcp_dst=5001 vs tcp_dst=5002) and steer packets into egress port 3 (Fast Path) or port 4 (Standard Path)."),

        ("Member 3 (Integration Lead)",
         "How does the application layer dynamically influence the SDN network layer?",
         "The Broker monitors per-topic message volume in real time. When a topic crosses 15 messages, it fires an HTTP POST /sdn/policy "
         "webhook to the SDN Controller. The controller dynamically installs priority 50 flow rules on switches s1 and s4, rerouting "
         "that host onto the Fast Path mid-stream."),

        ("Member 3 (Integration Lead)",
         "What quantitative performance improvement is achieved by dynamic SDN steering?",
         "End-to-end delivery latency drops from ~55–60 ms on the 5 Mbps / 25 ms standard path down to ~6–10 ms on the 20 Mbps / 2 ms "
         "fast path, achieving an ~85% latency reduction.")
    ]

    for role, q, a in viva_items:
        item_data = [
            [Paragraph(f"<b>[{role}] Q:</b> {q}", body_style)],
            [Paragraph(f"<b>Answer:</b> {a}", ParagraphStyle("Ans", parent=body_style, textColor=colors.HexColor("#065F46")))]
        ]
        t_item = Table(item_data, colWidths=[504])
        t_item.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_item)
        story.append(Spacer(1, 6))

    # Section 6: Git Workflow
    story.append(Spacer(1, 8))
    story.append(Paragraph("6. Collaborative Git Workflow", h1_style))
    git_text = (
        "• <b>Clone:</b> <code>git clone https://github.com/chandrugworkspace/sdn-tcp-pubsub.git</code><br/>"
        "• <b>Update:</b> <code>git pull origin main</code> before starting any lab session.<br/>"
        "• <b>Branching:</b> <code>git checkout -b feature/your-name-updates</code><br/>"
        "• <b>Syncing:</b> <code>git add . && git commit -m 'your message' && git push origin main</code>"
    )
    story.append(Paragraph(git_text, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✔ Successfully generated PDF: {filename}")


if __name__ == "__main__":
    out_pdf = "SDN_TCP_PubSub_Teammate_Handbook.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
