"""Cryptography module — ECDH key exchange and AES-256-GCM encryption."""
from __future__ import annotations

import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization


class CryptoManager:
    """Handles ECDH key exchange and AES-256-GCM encryption for FlashGrid sessions."""

    def __init__(self):
        self._private_key = ec.generate_private_key(ec.SECP256K1())
        self._public_key = self._private_key.public_key()
        self._shared_secret: bytes | None = None
        self._session_key: bytes | None = None

    @property
    def public_key(self) -> bytes:
        """Get the raw public key bytes for key exchange."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

    def derive_shared_secret(self, peer_pubkey_bytes: bytes) -> None:
        """Derive shared secret from peer's public key using ECDH."""
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        from cryptography.hazmat.backends import default_backend

        peer_pub = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(), peer_pubkey_bytes
        )
        shared_bytes = self._private_key.exchange(ec.ECDH(), peer_pub)
        self._shared_secret = hashlib.sha256(shared_bytes).digest()

    def init_session_key(self, salt: bytes | None = None) -> bytes:
        """Initialize the session encryption key. Returns the salt."""
        if self._shared_secret is None:
            raise RuntimeError("Shared secret not established")
        if salt is None:
            salt = os.urandom(16)
        self._session_key = hashlib.pbkdf2_hmac(
            "sha256", self._shared_secret, salt, iterations=100_000, dklen=32
        )
        return salt

    def encrypt_chunk(self, chunk: bytes) -> bytes:
        """Encrypt a data chunk with AES-256-GCM. Returns: nonce(12) + ciphertext + tag(16)."""
        if self._session_key is None:
            raise RuntimeError("Session key not initialized")
        aesgcm = AESGCM(self._session_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, chunk, None)
        return nonce + ciphertext

    def decrypt_chunk(self, encrypted: bytes) -> bytes:
        """Decrypt an encrypted chunk. Input: nonce(12) + ciphertext + tag(16)."""
        if self._session_key is None:
            raise RuntimeError("Session key not initialized")
        aesgcm = AESGCM(self._session_key)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)

    @staticmethod
    def hash_file(path: str, chunk_size: int = 1024 * 1024) -> str:
        """Compute SHA-256 hash of a file."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha.update(chunk)
        return sha.hexdigest()