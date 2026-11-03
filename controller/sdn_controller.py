"""
controller/sdn_controller.py - Dynamic OpenFlow 1.3 SDN Controller (Member 2 & 3)

Features:
- Layer-4 TCP Topic Traffic Classification (Port 5001 -> Fast Path, Port 5002 -> Standard Path)
- Built-in HTTP REST API (:8080 /sdn/policy) for dynamic application-level topic promotion
- Loop-free directed ARP forwarding preventing broadcast storms in diamond topology
- Real-time link failure detection (port_status_handler) with sub-second failover to backup path
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet, ipv4, tcp, arp, ether_types


class SDNRestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the SDN Controller REST API."""
    sdn_app = None

    def do_POST(self):
        if self.path == "/sdn/policy":
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            try:
                body = json.loads(body_bytes.decode("utf-8"))
                client_ip = body.get("client_ip")
                topic = body.get("topic", "unknown")
                action = body.get("action")
                if action == "PROMOTE_FAST_PATH" and client_ip and self.sdn_app:
                    self.sdn_app.install_dynamic_promotion(client_ip, topic)
                    resp = json.dumps({"status": "PROMOTED"}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(resp)))
                    self.end_headers()
                    self.wfile.write(resp)
                    return
            except Exception as e:
                print(f"[SDN-API-ERR] Invalid policy request: {e}")
            self.send_response(400)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default request logging to keep console clean
        return


class PubSubSDNController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(PubSubSDNController, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.fast_path_alive = True
        self.promoted_ips = set()

        # Host IP -> (dpid, port)
        self.host_PortMap = {
            "10.0.0.1": (1, 1),
            "10.0.0.2": (1, 2),
            "10.0.0.3": (4, 1),
            "10.0.0.4": (4, 2),
            "10.0.0.5": (4, 3),
        }

        # Start built-in REST API server on port 8080
        self._start_rest_server(port=8080)

    def _start_rest_server(self, port=8080):
        SDNRestHandler.sdn_app = self
        try:
            server = HTTPServer(("0.0.0.0", port), SDNRestHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            self.logger.info(f"[SDN-API] REST API listening on http://0.0.0.0:{port}/sdn/policy")
        except Exception as e:
            self.logger.warning(f"[SDN-API] Could not bind REST API on port {port}: {e}")

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            idle_timeout=idle_timeout,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        self.datapaths[dpid] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry (priority 0)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # Transit switches s2 and s3 simply forward between port 1 and port 2
        if dpid in (2, 3):
            self.add_flow(datapath, 10, parser.OFPMatch(in_port=1), [parser.OFPActionOutput(2)])
            self.add_flow(datapath, 10, parser.OFPMatch(in_port=2), [parser.OFPActionOutput(1)])

        self.logger.info(f"[SDN] Switch s{dpid} connected and initialized.")

    def get_inter_switch_port(self, dpid: int, use_fast_path: bool) -> int:
        """Returns the correct egress port on s1 or s4 for the chosen path."""
        if not self.fast_path_alive:
            use_fast_path = False  # Failover to s3 if s2 path is down
        if dpid == 1:
            return 3 if use_fast_path else 4
        if dpid == 4:
            return 4 if use_fast_path else 5
        return 1

    def install_dynamic_promotion(self, client_ip: str, topic: str):
        """Called via REST webhook by Broker to promote a host's standard traffic to the Fast Path."""
        self.promoted_ips.add(client_ip)
        if 1 in self.datapaths and 4 in self.datapaths:
            s1 = self.datapaths[1]
            s4 = self.datapaths[4]
            p1 = s1.ofproto_parser
            p4 = s4.ofproto_parser

            # Forward client_ip <-> Broker (10.0.0.3) via Fast Path (s1:3, s4:4)
            match_up = p1.OFPMatch(eth_type=0x0800, ipv4_src=client_ip, ipv4_dst="10.0.0.3")
            self.add_flow(s1, 50, match_up, [p1.OFPActionOutput(3)], idle_timeout=60)

            match_down = p4.OFPMatch(eth_type=0x0800, ipv4_src="10.0.0.3", ipv4_dst=client_ip)
            self.add_flow(s4, 50, match_down, [p4.OFPActionOutput(4)], idle_timeout=60)
            self.logger.info(f"[SDN-POLICY] Promoted host {client_ip} (topic '{topic}') to FAST PATH (s1->s2->s4)")

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        """Detects link failure and dynamically reroutes traffic to backup path."""
        msg = ev.msg
        dpid = msg.datapath.id
        port_no = msg.desc.port_no
        ofproto = msg.datapath.ofproto

        is_down = (msg.desc.state & ofproto.OFPPS_LINK_DOWN) != 0
        if dpid == 1 and port_no == 3:
            if is_down:
                self.fast_path_alive = False
                self.logger.warning("[SDN-FAILOVER] Fast Path Link (s1-s2) DOWN! Rerouting all flows via s3.")
                self.reroute_all_to_backup()
            else:
                self.fast_path_alive = True
                self.logger.info("[SDN-RECOVERY] Fast Path Link (s1-s2) UP! Restoring priority routing.")

    def reroute_all_to_backup(self):
        """Installs high-priority override rules on s1 and s4 to force traffic onto s3."""
        if 1 in self.datapaths and 4 in self.datapaths:
            s1, s4 = self.datapaths[1], self.datapaths[4]
            p1, p4 = s1.ofproto_parser, s4.ofproto_parser
            # Send all s1 -> s4 traffic out port 4 (via s3)
            for dst_ip in ("10.0.0.3", "10.0.0.4", "10.0.0.5"):
                m1 = p1.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
                self.add_flow(s1, 60, m1, [p1.OFPActionOutput(4)], idle_timeout=30)
            # Send all s4 -> s1 traffic out port 5 (via s3)
            for dst_ip in ("10.0.0.1", "10.0.0.2"):
                m4 = p4.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)
                self.add_flow(s4, 60, m4, [p4.OFPActionOutput(5)], idle_timeout=30)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        in_port = msg.match["in_port"]
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Handle ARP without loops
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            dst_ip = arp_pkt.dst_ip
            if dst_ip in self.host_PortMap:
                target_dpid, target_port = self.host_PortMap[dst_ip]
                out_port = target_port if dpid == target_dpid else self.get_inter_switch_port(dpid, True)
                out = parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=msg.buffer_id,
                    in_port=in_port,
                    actions=[parser.OFPActionOutput(out_port)],
                    data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
                )
                datapath.send_msg(out)
            return

        # Handle IPv4 & TCP Topic Classification
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return

        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        if dst_ip not in self.host_PortMap:
            return

        target_dpid, target_port = self.host_PortMap[dst_ip]
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        # Determine if flow belongs on Fast Path (TCP port 5001 or promoted host)
        use_fast = False
        if src_ip in self.promoted_ips or dst_ip in self.promoted_ips:
            use_fast = True
        elif tcp_pkt and (tcp_pkt.dst_port == 5001 or tcp_pkt.src_port == 5001):
            use_fast = True

        if dpid == target_dpid:
            out_port = target_port
        else:
            out_port = self.get_inter_switch_port(dpid, use_fast)

        actions = [parser.OFPActionOutput(out_port)]

        # Install specific OpenFlow rule for TCP or ICMP flow
        if tcp_pkt:
            match = parser.OFPMatch(
                eth_type=0x0800,
                ip_proto=6,
                ipv4_src=src_ip,
                ipv4_dst=dst_ip,
                tcp_src=tcp_pkt.src_port,
                tcp_dst=tcp_pkt.dst_port
            )
            path_name = "FAST_PATH(s2)" if (use_fast and self.fast_path_alive) else "STD_PATH(s3)"
            self.logger.info(f"[FLOW-INSTALL] s{dpid}: {src_ip}:{tcp_pkt.src_port} -> {dst_ip}:{tcp_pkt.dst_port} via {path_name} (port {out_port})")
            self.add_flow(datapath, 30, match, actions, idle_timeout=30)
        else:
            match = parser.OFPMatch(eth_type=0x0800, ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.add_flow(datapath, 20, match, actions, idle_timeout=30)

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        )
        datapath.send_msg(out)
