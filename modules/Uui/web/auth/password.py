"""Password hashing using pbkdf2_sha256 (stdlib only, no external deps)."""
import base64
import hashlib
import hmac
import os
import secrets


ALGO = 'pbkdf2_sha256'
ITERATIONS = 320_000
SALT_LEN = 16
HASH_LEN = 32


def make_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """Hash a password and return a string in the format ``pbkdf2_sha256$iters$salt$hash``."""
    if password is None:
        raise ValueError('password must not be None')
    salt = secrets.token_bytes(SALT_LEN)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=HASH_LEN)
    return f'{ALGO}${iterations}${_b64(salt)}${_b64(dk)}'


def check_password(password: str, encoded: str) -> bool:
    """Constant-time comparison. Returns False on any parse error."""
    if not password or not encoded:
        return False
    try:
        algo, iters_s, salt_b64, hash_b64 = encoded.split('$', 3)
    except ValueError:
        return False
    if algo != ALGO:
        return False
    try:
        iterations = int(iters_s)
        salt = _b64d(salt_b64)
        expected = _b64d(hash_b64)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=len(expected))
    return hmac.compare_digest(dk, expected)


def needs_rehash(encoded: str) -> bool:
    """Return True if the encoded hash uses outdated parameters."""
    if not encoded:
        return True
    parts = encoded.split('$', 3)
    if len(parts) != 4 or parts[0] != ALGO:
        return True
    try:
        return int(parts[1]) < ITERATIONS
    except ValueError:
        return True


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode('ascii').rstrip('=')


def _b64d(s: str) -> bytes:
    pad = '=' * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s + pad)
