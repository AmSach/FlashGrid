"""Packet definitions and serialization for FlashGrid protocol."""
from __future__ import annotations

import struct
import enum
from dataclasses import dataclass
from typing import Optional


class PacketType(enum.IntEnum):
    DISCOVER = 0x01
    ANNOUNCE = 0x02
    HANDSHAKE_OFFER = 0x03
    HANDSHAKE_RESPONSE = 0x04
    KEY_EXCHANGE = 0x05
    TRANSFER_REQUEST = 0x06
    TRANSFER_ACK = 0x07
    CHUNK = 0x08
    CHUNK_ACK = 0x09
    COMPLETE = 0x0A
    ERROR = 0xFF


@dataclass
class Packet:
    """FlashGrid protocol packet."""
    type: PacketType
    seq: int
    payload: bytes
    checksum: int

    HEADER_FORMAT = "!BBHI"  # type(1), version(1), seq(2), payload_len(4)
    HEADER_SIZE = 8

    @classmethod
    def from_bytes(cls, data: bytes) -> Packet:
        """Deserialize a packet from bytes."""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} < {cls.HEADER_SIZE}")

        ptype, _, seq, payload_len = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        if len(data) < cls.HEADER_SIZE + payload_len + 4:
            raise ValueError("Invalid packet: truncated")

        payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_len]
        checksum = struct.unpack("!I", data[cls.HEADER_SIZE + payload_len:cls.HEADER_SIZE + payload_len + 4])[0]

        return cls(PacketType(ptype), seq, payload, checksum)

    def to_bytes(self) -> bytes:
        """Serialize the packet to bytes."""
        header = struct.pack(self.HEADER_FORMAT, self.type.value, 1, self.seq, len(self.payload))
        return header + self.payload + struct.pack("!I", self.checksum)

    @staticmethod
    def compute_checksum(data: bytes) -> int:
        """Compute a simple checksum for data integrity."""
        import zlib
        return zlib.crc32(data) & 0xFFFFFFFF

    def verify(self) -> bool:
        """Verify packet integrity."""
        return self.checksum == self.compute_checksum(self.payload)


@dataclass
class DiscoverPacket:
    """UDP discovery packet — broadcast to find peers."""
    hostname: str
    port: int
    available_space: int  # bytes

    def to_bytes(self) -> bytes:
        payload = f"{self.hostname}:{self.port}:{self.available_space}".encode()
        return struct.pack("!HH", len(payload), 0) + payload

    @classmethod
    def from_bytes(cls, data: bytes) -> DiscoverPacket:
        """Parse a discover packet from raw UDP data."""
        if len(data) < 4:
            raise ValueError("Discover packet too short")
        payload_len = struct.unpack("!H", data[:2])[0]
        payload = data[4:4 + payload_len].decode()
        parts = payload.split(":")
        return cls(parts[0], int(parts[1]), int(parts[2]))


@dataclass
class HandshakePacket:
    """ECDH key exchange packet."""
    pubkey: bytes
    capabilities: list[str]

    def to_bytes(self) -> bytes:
        cap_bytes = "|".join(self.capabilities).encode()
        return struct.pack("!H", len(self.pubkey)) + self.pubkey + cap_bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> HandshakePacket:
        key_len = struct.unpack("!H", data[:2])[0]
        pubkey = data[2:2 + key_len]
        cap_str = data[2 + key_len:].decode()
        capabilities = cap_str.split("|") if cap_str else []
        return cls(pubkey, capabilities)