"""Peer state and connection management for FlashGrid."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional
from .crypto import CryptoManager


@dataclass
class Peer:
    """Represents a discovered FlashGrid peer."""
    hostname: str
    ip: str
    port: int
    available_space: int
    last_seen: float = field(default_factory=time.time)
    crypto: Optional[CryptoManager] = None
    connected: bool = False

    def touch(self) -> None:
        self.last_seen = time.time()

    def is_stale(self, max_age: float = 30.0) -> bool:
        return (time.time() - self.last_seen) > max_age