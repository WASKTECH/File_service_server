"""
Security and authentication helper functions.

Provides API key hashing and timing-attack resistant comparison routines.
"""

import hashlib
import secrets


def hash_api_key(api_key: str) -> str:
    """
    Generate a deterministic SHA-256 hash of an API key for safe database storage.

    Args:
        api_key: Plaintext API key.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Compare a plaintext API key against a stored hash in constant time to prevent timing attacks.

    Args:
        plain_key:  The API key sent in request headers.
        hashed_key: The SHA-256 hash stored in the database.

    Returns:
        True if matching, False otherwise.
    """
    computed_hash = hash_api_key(plain_key)
    return secrets.compare_digest(computed_hash, hashed_key)
