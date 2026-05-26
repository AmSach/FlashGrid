"""UDP peer discovery service for FlashGrid."""
from __future__ import annotations

import socket
import asyncio
import os
import struct
from dataclasses import dataclass, field
from typing import Callable


BROADCAST_PORT = 42069
BROADCAST_ADDR = "<broadcast>"


@dataclass
class Peer:
    """Represents a discovered peer on the LAN."""
    hostname: str
    ip: str
    port: int
    available_space: int  # bytes
    last_seen: float = field(default_factory=time.time)


import time


class DiscoveryService:
    """UDP broadcast peer discovery for FlashGrid."""

    def __init__(self, port: int = BROADCAST_PORT):
        self.port = port
        self._sock: socket.socket | None = None
        self._running = False
        self._peers: dict[str, Peer] = {}
        self._callbacks: list[Callable[[Peer], None]] = []

    def add_peer_callback(self, cb: Callable[[Peer], None]) -> None:
        self._callbacks.append(cb)

    async def start_discovery(self, hostname: str, port: int, available_space: int) -> None:
        """Broadcast presence as a peer, discovering others in the process."""
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setblocking(False)

        payload = struct.pack("!HH", len(hostname), port)
        payload += hostname.encode() + b":" + str(available_space).encode()

        while self._running:
            try:
                self._sock.sendto(payload, (BROADCAST_ADDR, self.port))
            except Exception:
                pass
            await asyncio.sleep(2)

    async def listen(self) -> None:
        """Listen for peer announcements."""
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setblocking(False)
        try:
            self._sock.bind(("", self.port))
        except Exception:
            self._sock.bind(("", 0))
            self.port = self._sock.getsockname()[1]

        while self._running:
            await asyncio.sleep(0.1)
            try:
                data, addr = self._sock.recvfrom(4096)
                self._handle_announce(data, addr)
            except BlockingIOError:
                continue
            except Exception:
                pass

    def _handle_announce(self, data: bytes, addr: tuple) -> None:
        try:
            if len(data) < 4:
                return
            hostname_len = struct.unpack("!H", data[:2])[0]
            port = struct.unpack("!H", data[2:4])[0]
            rest = data[4:].decode(errors="ignore")
            parts = rest.split(":", 1)
            hostname = parts[0][:hostname_len] if len(parts[0]) >= hostname_len else parts[0]
            space_str = parts[1] if len(parts) > 1 else "0"

            peer = Peer(hostname, addr[0], port, int(space_str))
            self._peers[addr[0]] = peer

            for cb in self._callbacks:
                try:
                    cb(peer)
                except Exception:
                    pass
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
        if self._sock:
            self._sock.close()
            self._sock = None

    @property
    def peers(self) -> dict[str, Peer]:
        return self._peers