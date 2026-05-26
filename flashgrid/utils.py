"""Utility functions for FlashGrid."""
from __future__ import annotations

import hashlib


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def compute_checksum(data: bytes) -> int:
    """Compute CRC32 checksum."""
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF