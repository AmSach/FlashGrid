"""FlashGrid — Serverless encrypted peer-to-peer file transfer."""

__version__ = "0.1.0"
from .protocol import Packet, PacketType
from .peer import Peer
from .discovery import DiscoveryService
from .crypto import CryptoManager
from .transfer import TransferManager

__all__ = [
    "Packet",
    "PacketType",
    "Peer",
    "DiscoveryService",
    "CryptoManager",
    "TransferManager",
]