"""
topology/pubsub_topo.py - Multi-Path Diamond Mininet Topology (Member 2)

Builds a 4-switch, 5-host diamond topology in Mininet:
- Upper Fast Path:     s1 -> s2 -> s4 (20 Mbps bandwidth, 2ms delay per hop)
- Lower Standard Path: s1 -> s3 -> s4 (5 Mbps bandwidth, 25ms delay per hop)
- Deterministic port allocations to enable precise SDN OpenFlow steering.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info


class PubSubDiamondTopo(Topo):
    def build(self):
        # Create 4 OpenFlow 1.3 switches
        s1 = self.addSwitch("s1", dpid="0000000000000001", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", dpid="0000000000000002", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", dpid="0000000000000003", protocols="OpenFlow13")
        s4 = self.addSwitch("s4", dpid="0000000000000004", protocols="OpenFlow13")

        # Hosts on s1 (Publishers)
        h1 = self.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = self.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")

        # Hosts on s4 (h3 = Broker, h4 & h5 = Subscribers)
        h3 = self.addHost("h3", ip="10.0.0.3/24", mac="00:00:00:00:00:03")
        h4 = self.addHost("h4", ip="10.0.0.4/24", mac="00:00:00:00:00:04")
        h5 = self.addHost("h5", ip="10.0.0.5/24", mac="00:00:00:00:00:05")

        # Host-to-Switch Links (Explicit port numbering for deterministic SDN control)
        # s1 ports 1, 2 -> h1, h2
        self.addLink(h1, s1, port1=1, port2=1, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h2, s1, port1=1, port2=2, cls=TCLink, bw=50, delay="1ms")

        # s4 ports 1, 2, 3 -> h3 (Broker), h4 (Sub1), h5 (Sub2)
        self.addLink(h3, s4, port1=1, port2=1, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h4, s4, port1=1, port2=2, cls=TCLink, bw=50, delay="1ms")
        self.addLink(h5, s4, port1=1, port2=3, cls=TCLink, bw=50, delay="1ms")

        # Inter-Switch Diamond Links:
        # Upper Fast Path: s1(port 3) <-> s2(port 1) and s2(port 2) <-> s4(port 4)
        self.addLink(s1, s2, port1=3, port2=1, cls=TCLink, bw=20, delay="2ms")
        self.addLink(s2, s4, port1=2, port2=4, cls=TCLink, bw=20, delay="2ms")

        # Lower Standard Path: s1(port 4) <-> s3(port 1) and s3(port 2) <-> s4(port 5)
        self.addLink(s1, s3, port1=4, port2=1, cls=TCLink, bw=5, delay="25ms")
        self.addLink(s3, s4, port1=2, port2=5, cls=TCLink, bw=5, delay="25ms")


def run_network():
    topo = PubSubDiamondTopo()
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=lambda name: RemoteController(name, ip="127.0.0.1", port=6633),
        link=TCLink,
        autoSetMacs=True
    )
    net.start()
    info("\n*** Diamond Pub-Sub Topology Started ***\n")
    info("h1 (10.0.0.1), h2 (10.0.0.2) -> Publishers on s1\n")
    info("h3 (10.0.0.3)                -> Broker on s4\n")
    info("h4 (10.0.0.4), h5 (10.0.0.5) -> Subscribers on s4\n")
    info("Fast Path:     s1 -> s2 -> s4 (20 Mbps, 2ms delay per hop)\n")
    info("Standard Path: s1 -> s3 -> s4 (5 Mbps, 25ms delay per hop)\n\n")
    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_network()
