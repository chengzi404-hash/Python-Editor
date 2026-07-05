"""TLS helper — generate a self-signed cert via the ``openssl`` binary.

The openssl command is used directly (rather than re-implementing ASN.1
or X.509 by hand) so the resulting cert is interoperable with browsers,
``curl``, ``h2`` clients, and any standard library. This keeps the
Uui.web dependency surface small — no new third-party packages.

If openssl is not on PATH, falls back to a stdlib-only generator (which
emits a slightly less polished certificate, or to ``cryptography`` if
installed).
"""
import os
import shutil
import subprocess
import sys
from typing import Optional, Tuple


def openssl_available() -> bool:
    return shutil.which('openssl') is not None


def _generate_via_cryptography(cn: str, cert_path: str, key_path: str,
                               days: int = 3650) -> Tuple[str, str]:
    """Use the optional ``cryptography`` library to issue a real cert."""
    import datetime
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048,
                                    backend=default_backend())
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(cn)]),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(cert_path, 'wb') as f:
        f.write(cert_pem)
    with open(key_path, 'wb') as f:
        f.write(key_pem)
    return cert_path, key_path


def generate_self_signed_cert(cn: str = 'localhost',
                              days: int = 3650,
                              cert_path: str = 'cert.pem',
                              key_path: str = 'key.pem') -> Tuple[str, str]:
    """Generate a self-signed RSA-2048 cert + key pair.

    Preference order:
      1. ``openssl`` CLI (most interoperable)
      2. ``cryptography`` library if installed
      3. Pure-stdlib fallback (best effort, may be rejected by some clients)
    """
    if openssl_available():
        cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-nodes', '-days', str(days),
            '-subj', f'/CN={cn}',
            '-addext', f'subjectAltName=DNS:{cn}',
            '-keyout', key_path,
            '-out', cert_path,
        ]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return cert_path, key_path

    try:
        return _generate_via_cryptography(cn, cert_path, key_path, days)
    except ImportError:
        pass

    # Last-ditch: try the pure-Python generator
    from .tls_pyfallback import generate_self_signed_cert as _gen
    return _gen(cn=cn, cert_path=cert_path, key_path=key_path)


def ensure_dev_cert(cn: str = 'localhost',
                    cert_path: str = 'cert.pem',
                    key_path: str = 'key.pem',
                    regenerate: bool = False) -> Tuple[str, str]:
    """Return existing cert paths, or generate a fresh self-signed pair."""
    if not regenerate and os.path.isfile(cert_path) and os.path.isfile(key_path):
        return cert_path, key_path
    return generate_self_signed_cert(cn=cn, cert_path=cert_path, key_path=key_path)
