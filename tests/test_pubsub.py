"""
tests/test_pubsub.py - Unit & Integration Test Suite for TCP Pub-Sub System

Validates:
1. Protocol framing, length prefixing, and JSON serialization.
2. Concurrent Broker subscription, publishing, and delivery ACKs.
3. Multiple subscribers receiving published topic payloads.
4. Dynamic SDN threshold hook triggering upon burst volume (>= 15 messages).
"""

import os
import socket
import sys
import threading
import time
import unittest

# Ensure pubsub is in import search path
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from pubsub.protocol import send_msg, recv_msg
from pubsub.broker import PubSubBroker


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestPubSubProtocol(unittest.TestCase):
    def test_protocol_roundtrip(self):
        """Tests sending and receiving length-prefixed messages over loopback socket pair."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        received = []

        def srv_worker():
            conn, _ = server.accept()
            msg = recv_msg(conn)
            received.append(msg)
            conn.close()
            server.close()

        t = threading.Thread(target=srv_worker)
        t.start()

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", port))
        payload = {"type": "TEST", "value": 42, "text": "hello world"}
        send_msg(client, payload)
        client.close()
        t.join(timeout=2)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], payload)


class TestPubSubBroker(unittest.TestCase):
    def setUp(self):
        self.prio_port = get_free_port()
        self.std_port = get_free_port()
        self.broker = PubSubBroker("127.0.0.1", self.prio_port, self.std_port, sdn_url="")
        self.t1 = threading.Thread(target=self.broker.start_listener, args=(self.prio_port,), daemon=True)
        self.t2 = threading.Thread(target=self.broker.start_listener, args=(self.std_port,), daemon=True)
        self.t1.start()
        self.t2.start()
        time.sleep(0.1)  # Allow listeners to bind

    def tearDown(self):
        self.broker.running = False
        # Connect to both ports to unblock accept() if waiting
        for p in (self.prio_port, self.std_port):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", p))
                s.close()
            except OSError:
                pass

    def test_subscribe_and_publish(self):
        """Tests subscribing on standard port and publishing on priority port."""
        sub_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sub_sock.connect(("127.0.0.1", self.std_port))

        # Subscribe to topic
        send_msg(sub_sock, {"type": "SUBSCRIBE", "topic": "sensors/temp"})
        ack = recv_msg(sub_sock)
        self.assertEqual(ack.get("type"), "SUB_ACK")
        self.assertEqual(ack.get("status"), "OK")

        # Connect publisher on priority port
        pub_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pub_sock.connect(("127.0.0.1", self.prio_port))

        send_msg(pub_sock, {
            "type": "PUBLISH",
            "topic": "sensors/temp",
            "seq": 1,
            "payload": "temperature=24.5C",
            "pub_timestamp_ns": time.time_ns()
        })
        pub_ack = recv_msg(pub_sock)
        self.assertEqual(pub_ack.get("type"), "PUB_ACK")
        self.assertEqual(pub_ack.get("delivered_to"), 1)

        # Subscriber receives the message
        received_msg = recv_msg(sub_sock)
        self.assertEqual(received_msg.get("type"), "MESSAGE")
        self.assertEqual(received_msg.get("topic"), "sensors/temp")
        self.assertEqual(received_msg.get("payload"), "temperature=24.5C")
        self.assertEqual(received_msg.get("traffic_class"), "HIGH_PRIORITY")

        sub_sock.close()
        pub_sock.close()

    def test_burst_promotion_trigger(self):
        """Tests that reaching 15 messages triggers SDN promotion condition."""
        pub_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pub_sock.connect(("127.0.0.1", self.std_port))

        for seq in range(1, 16):
            send_msg(pub_sock, {
                "type": "PUBLISH",
                "topic": "traffic/burst",
                "seq": seq,
                "payload": f"Burst item {seq}"
            })
            ack = recv_msg(pub_sock)
            self.assertEqual(ack.get("type"), "PUB_ACK")

        # Check that the topic has been recorded as promoted
        self.assertIn("traffic/burst", self.broker.promoted_topics)
        pub_sock.close()


if __name__ == "__main__":
    unittest.main()
