"""Pure-Python self-signed cert generator (fallback for when openssl is missing).

Produces a minimal X.509v3 self-signed certificate with a 2048-bit RSA
key. Not optimised for speed or memory — for development use only.

Format produced:
* ``cert.pem``   — PEM-encoded X.509 certificate
* ``key.pem``    — PEM-encoded PKCS#1 RSAPrivateKey

References:
* RFC 5280 (X.509v3)
* RFC 8017 (PKCS#1 v2.2 — RSA cryptography)
* RFC 3279 (AlgorithmIdentifiers for RSA)
"""

import base64
import datetime
import random
from pathlib import Path


def _b64(n: int) -> bytes:
    """Encode a positive integer as a DER INTEGER."""
    if n == 0:
        return b"\x00"
    length = max(1, (n.bit_length() + 7) // 8)
    body = n.to_bytes(length, "big")
    if body[0] & 0x80:
        body = b"\x00" + body
    return b"\x02" + _encode_length(len(body)) + body


def _seq(*parts: bytes) -> bytes:
    body = b"".join(parts)
    return b"\x30" + _encode_length(len(body)) + body


def _set(*parts: bytes) -> bytes:
    body = b"".join(parts)
    return b"\x31" + _encode_length(len(body)) + body


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    if n < 0x100:
        return b"\x81" + bytes([n])
    if n < 0x10000:
        return b"\x82" + n.to_bytes(2, "big")
    return b"\x83" + n.to_bytes(3, "big")


def _is_probable_prime(n: int, rounds: int = 16) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    rng = random.SystemRandom()
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    rng = random.SystemRandom()
    while True:
        candidate = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


def _rsa_keypair(bits: int = 2048) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    """Return ``((e, n), (d, n, p, q))``."""
    e = 65537
    while True:
        p = _generate_prime(bits // 2)
        q = _generate_prime(bits // 2)
        if p == q:
            continue
        n = p * q
        phi = (p - 1) * (q - 1)
        if phi % e != 0:
            d = pow(e, -1, phi)
            return (e, n), (d, n, p, q)


_OID_SIG_SHA256_RSA = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b"
_OID_RSA_ENCRYPTION = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"
_OID_COMMON_NAME = b"\x06\x03\x55\x04\x03"
_OID_SAN = b"\x06\x03\x55\x1d\x11"


def _name(cn: str) -> bytes:
    atv = _seq(_OID_COMMON_NAME + b"\x0c" + bytes([len(cn.encode("utf-8"))]) + cn.encode("utf-8"))
    rdn = b"\x31" + _encode_length(len(atv)) + atv
    return _seq(rdn)


def _spki(e: int, n: int) -> bytes:
    rsa_pub = _seq(_b64(n), _b64(e))
    bit_string_value = b"\x00" + rsa_pub
    algorithm = _seq(_OID_RSA_ENCRYPTION)
    return _seq(algorithm + b"\x03" + _encode_length(len(bit_string_value)) + bit_string_value)


def _validity(not_before: datetime.datetime, not_after: datetime.datetime) -> bytes:
    def _time(t: datetime.datetime) -> bytes:
        s = t.strftime("%y%m%d%H%M%SZ").encode("ascii")
        return b"\x17" + bytes([len(s)]) + s

    return _seq(_time(not_before) + _time(not_after))


def _extension_san(dns: str) -> bytes:
    san = b"\x82" + bytes([len(dns)]) + dns.encode("utf-8")
    san_seq = b"\x30" + _encode_length(len(san)) + san
    octets = b"\x04" + _encode_length(len(san_seq)) + san_seq
    return _seq(_OID_SAN + octets)


def _tbs(
    cn: str, e: int, n: int, not_before: datetime.datetime, not_after: datetime.datetime
) -> bytes:
    body = (
        b"\xa0\x03\x02\x01\x02"  # version v3
        + _b64(1)  # serial
        + _seq(_OID_SIG_SHA256_RSA + b"\x05\x00")  # signature algorithm
        + _name(cn)  # issuer
        + _validity(not_before, not_after)  # validity
        + _name(cn)  # subject
        + _spki(e, n)  # subjectPublicKeyInfo
        + _seq(_extension_san(cn))  # extensions
    )
    return _seq(body)


def _sign(tbs: bytes, d: int, n: int) -> bytes:
    import hashlib

    digest = hashlib.sha256(tbs).digest()
    alg_id = _seq(_OID_SIG_SHA256_RSA + b"\x05\x00")
    digest_info = _seq(alg_id + b"\x04" + bytes([len(digest)]) + digest)
    sig_int = pow(int.from_bytes(digest_info, "big"), d, n)
    body = sig_int.to_bytes((sig_int.bit_length() + 7) // 8, "big")
    return b"\x03" + _encode_length(len(body) + 1) + b"\x00" + body


def generate_self_signed_cert(
    cn: str = "localhost", cert_path: str = "cert.pem", key_path: str = "key.pem"
) -> tuple[str, str]:
    """Write a self-signed RSA-2048 cert + key pair to disk and return the paths."""
    (e, n), (d, n2, p, q) = _rsa_keypair(2048)
    not_before = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    not_after = datetime.datetime(2099, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)

    tbs = _tbs(cn, e, n, not_before, not_after)
    sig_value = _sign(tbs, d, n)
    signature_algorithm = _seq(_OID_SIG_SHA256_RSA + b"\x05\x00")
    cert_der = _seq(tbs + signature_algorithm + sig_value)

    cert_pem = b"-----BEGIN CERTIFICATE-----\n"
    cert_pem += base64.encodebytes(cert_der)
    cert_pem += b"-----END CERTIFICATE-----\n"

    pkcs1 = _seq(
        b"\x02\x01\x00"
        + _b64(n2)
        + _b64(e)
        + _b64(d)
        + _b64(p)
        + _b64(q)
        + _b64(d % (p - 1))
        + _b64(d % (q - 1))
        + _b64(pow(q, -1, p))
    )
    key_pem = b"-----BEGIN RSA PRIVATE KEY-----\n"
    key_pem += base64.encodebytes(pkcs1)
    key_pem += b"-----END RSA PRIVATE KEY-----\n"

    Path(cert_path).write_bytes(cert_pem)
    Path(key_path).write_bytes(key_pem)
    return cert_path, key_path
