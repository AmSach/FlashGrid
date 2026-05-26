"""Chunked parallel file transfer for FlashGrid."""
from __future__ import annotations

import asyncio
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import BinaryIO, Callable

CHUNK_SIZE = 1024 * 1024  # 1MB chunks
MAX_PARALLEL = 8


class TransferManager:
    """Manages chunked parallel file transfers."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, max_parallel: int = MAX_PARALLEL):
        self.chunk_size = chunk_size
        self.max_parallel = max_parallel
        self._executor = ThreadPoolExecutor(max_workers=max_parallel * 2)

    async def send_file(
        self,
        path: str,
        writer: asyncio.StreamWriter,
        progress_callback: "Callable[[int, int], None] | None" = None
    ) -> str:
        """Send a file in chunks. Returns SHA-256 hash of the file."""
        file_size = os.path.getsize(path)
        sha = hashlib.sha256()
        chunk_futures = []

        with open(path, "rb") as f:
            chunk_idx = 0
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break

                sha.update(chunk)
                future = self._executor.submit(self._send_chunk, writer, chunk_idx, chunk)
                chunk_futures.append(future)
                chunk_idx += 1

                if len(chunk_futures) >= self.max_parallel:
                    await asyncio.gather(*chunk_futures)
                    if progress_callback:
                        progress_callback(chunk_idx, file_size)
                    chunk_futures = []

            if chunk_futures:
                await asyncio.gather(*chunk_futures)

        return sha.hexdigest()

    def _send_chunk(
        self,
        writer: asyncio.StreamWriter,
        idx: int,
        data: bytes
    ) -> None:
        """Send a single chunk (blocking, runs in thread pool)."""
        header = struct.pack("!II", idx, len(data))
        writer.write(header + data)

    async def receive_file(
        self,
        reader: asyncio.StreamReader,
        output_path: str,
        expected_size: int,
        progress_callback: "Callable[[int, int], None] | None" = None
    ) -> str:
        """Receive a file in chunks. Returns SHA-256 hash for verification."""
        sha = hashlib.sha256()
        received = 0
        chunks: dict[int, bytes] = {}
        chunk_count = (expected_size + self.chunk_size - 1) // self.chunk_size

        while received < chunk_count:
            header = await reader.readexactly(8)
            idx, length = struct.unpack("!II", header)
            data = await reader.readexactly(length)

            sha.update(data)
            chunks[idx] = data
            received += 1

            if progress_callback:
                progress_callback(received, chunk_count)

        # Reassemble in order
        with open(output_path, "wb") as f:
            for i in range(chunk_count):
                f.write(chunks[i])

        return sha.hexdigest()

    @staticmethod
    def compute_file_hash(path: str) -> str:
        """Compute SHA-256 hash of a file."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                sha.update(chunk)
        return sha.hexdigest()


import struct