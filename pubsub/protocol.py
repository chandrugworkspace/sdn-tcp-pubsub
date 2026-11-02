"""
pubsub/protocol.py - Wire Protocol Helper (Member 1)

Implements length-prefixed TCP socket framing using a 4-byte unsigned
big-endian integer header, ensuring reliable JSON message framing over
raw TCP byte streams without concatenation or fragmentation issues.
"""

import json
import socket
import struct
from typing import Dict, Any, Optional

# 4-byte unsigned int length prefix (! = network byte order / big-endian)
HEADER_STRUCT = struct.Struct("!I")


def send_msg(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Serializes a dictionary to JSON and sends it with a 4-byte length prefix."""
    raw_bytes = json.dumps(payload).encode("utf-8")
    sock.sendall(HEADER_STRUCT.pack(len(raw_bytes)) + raw_bytes)


def recv_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """Reads exactly num_bytes from a TCP socket or returns None on EOF."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def recv_msg(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """Receives a length-prefixed JSON message from a TCP socket."""
    header = recv_exact(sock, HEADER_STRUCT.size)
    if not header:
        return None
    (msg_len,) = HEADER_STRUCT.unpack(header)
    body = recv_exact(sock, msg_len)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))
