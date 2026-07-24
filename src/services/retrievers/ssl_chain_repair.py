"""SSL chain-repair helpers for PageFetcher.

Some third-party HTTPS servers are misconfigured to send only their leaf
certificate during the TLS handshake, omitting the intermediate CA
certificate needed to build a path to a trusted root. Root certificate
stores intentionally do not ship intermediates (that is the server's job to
provide), so a fully compliant, verification-enabled TLS client cannot build
a trust chain in that case — OpenSSL reports this as
``CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate``.

Browsers and Windows' CryptoAPI silently repair this via "AIA chasing":
they read the missing intermediate's download URL from the leaf
certificate's Authority Information Access (CA Issuers) extension — a
standard part of the certificate itself, RFC 5280 section 4.2.2.1 — fetch it
from the issuing CA's own distribution endpoint, and add it to the trust
chain for that connection. This is *not* a verification bypass: the fetched
certificate must still chain to an already-trusted root, or the handshake
still fails. httpx/OpenSSL do not do this by default on Linux/macOS, which is
why the same misconfigured server can work in a browser (or on Windows, where
CryptoAPI does AIA chasing at the OS level) but fail in a strict Python HTTP
client.

This module implements the same technique. Certificate verification is never
disabled; we only supply the certificate the server should have sent in the
first place, and we still validate that the supplemented chain actually
resolves to a trusted root before using it.
"""

from __future__ import annotations

import logging
import socket
import ssl
import threading

import certifi
import httpx
from cryptography import x509
from cryptography.x509.oid import AuthorityInformationAccessOID

from ...shared.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# X.509 store verification codes that specifically indicate a broken/incomplete
# certificate *chain* (missing intermediate), as opposed to a genuinely
# untrustworthy certificate (expired, revoked, wrong host, self-signed).
# Only these are eligible for repair — anything else must still fail loudly.
_INCOMPLETE_CHAIN_VERIFY_CODES: frozenset[int] = frozenset({
    2,   # X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT
    20,  # X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY
    21,  # X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE
})

_HANDSHAKE_TIMEOUT: float = 10.0
_AIA_FETCH_TIMEOUT: float = 10.0
_MAX_AIA_RESPONSE_BYTES: int = 65_536

_cache_lock = threading.Lock()
_context_cache: dict[str, ssl.SSLContext | None] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_ssl_verification_error(exc: BaseException) -> ssl.SSLCertVerificationError | None:
    """Walk *exc*'s ``__cause__``/``__context__`` chain for an ``SSLCertVerificationError``.

    httpx wraps httpcore's ``ConnectError``, which wraps the underlying
    ``ssl.SSLCertVerificationError`` — this unwinds that chain regardless of
    how many layers are in between.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ssl.SSLCertVerificationError):
            return current
        current = current.__cause__ or current.__context__
    return None


def is_incomplete_chain_error(exc: ssl.SSLCertVerificationError) -> bool:
    """True if *exc* specifically indicates a missing intermediate certificate."""
    return getattr(exc, "verify_code", None) in _INCOMPLETE_CHAIN_VERIFY_CODES


def build_repaired_ssl_context(
    hostname: str,
    *,
    port: int = 443,
    cafile: str | None = None,
) -> ssl.SSLContext | None:
    """Build an SSL context that supplements *cafile* with the intermediate
    certificate fetched from the leaf certificate's AIA "CA Issuers" URL.

    Verification remains fully enabled throughout. This never raises —
    callers should treat ``None`` as "repair not possible" and surface the
    original certificate error. Results are cached per hostname for the
    process lifetime so repeated fetches don't repeat the AIA round-trip.

    Args:
        hostname: The server hostname to diagnose and repair.
        port:     TLS port to connect to for reading the leaf certificate.
        cafile:   Trusted root CA bundle path. Defaults to ``certifi.where()``.

    Returns:
        A configured, verified :class:`ssl.SSLContext`, or ``None`` if the
        chain could not be repaired.
    """
    with _cache_lock:
        if hostname in _context_cache:
            return _context_cache[hostname]

    context = _build_repaired_ssl_context_uncached(hostname, port=port, cafile=cafile)

    with _cache_lock:
        _context_cache[hostname] = context
    return context


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_repaired_ssl_context_uncached(
    hostname: str,
    *,
    port: int,
    cafile: str | None,
) -> ssl.SSLContext | None:
    trusted_cafile = cafile or certifi.where()

    leaf_der = _fetch_leaf_certificate_der(hostname, port)
    if leaf_der is None:
        return None

    try:
        leaf_cert = x509.load_der_x509_certificate(leaf_der)
    except Exception as exc:
        logger.warning(
            "SSL chain repair: could not parse leaf certificate for %r — %s.", hostname, exc
        )
        return None

    issuer_urls = _extract_ca_issuer_urls(leaf_cert)
    if not issuer_urls:
        logger.warning(
            "SSL chain repair: %r has no CA Issuers (AIA) URL — cannot repair chain.",
            hostname,
        )
        return None

    for issuer_url in issuer_urls:
        pem = _fetch_and_validate_intermediate(issuer_url)
        if pem is None:
            continue

        try:
            context = ssl.create_default_context(cafile=trusted_cafile)
            context.load_verify_locations(cadata=pem)
        except ssl.SSLError as exc:
            logger.warning(
                "SSL chain repair: fetched intermediate from %r was rejected — %s.",
                issuer_url,
                exc,
            )
            continue

        if _verify_repaired_context(hostname, port, context):
            logger.info(
                "SSL chain repair: repaired trust chain for %r using intermediate "
                "from %r (verification re-confirmed against %s).",
                hostname,
                issuer_url,
                trusted_cafile,
            )
            return context

        logger.warning(
            "SSL chain repair: intermediate from %r did not resolve verification for %r.",
            issuer_url,
            hostname,
        )

    return None


def _fetch_leaf_certificate_der(hostname: str, port: int) -> bytes | None:
    """Read the certificate the server presents, without trusting it.

    This connection is diagnostic only — verification is intentionally
    disabled here purely to *read* the leaf certificate bytes so its AIA
    extension can be parsed. No data is exchanged beyond the TLS handshake,
    nothing from this connection is trusted, and it is never used to serve
    the actual page fetch.
    """
    try:
        diagnostic_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        diagnostic_context.check_hostname = False
        diagnostic_context.verify_mode = ssl.CERT_NONE
        with socket.create_connection((hostname, port), timeout=_HANDSHAKE_TIMEOUT) as sock:
            with diagnostic_context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                return tls_sock.getpeercert(binary_form=True)
    except Exception as exc:
        logger.warning(
            "SSL chain repair: could not read leaf certificate for %r — %s.", hostname, exc
        )
        return None


def _extract_ca_issuer_urls(cert: x509.Certificate) -> list[str]:
    """Return HTTP(S) "CA Issuers" URLs from the certificate's AIA extension."""
    try:
        aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
    except x509.ExtensionNotFound:
        return []

    return [
        desc.access_location.value
        for desc in aia
        if desc.access_method == AuthorityInformationAccessOID.CA_ISSUERS
        and desc.access_location.value.startswith(("http://", "https://"))
    ]


def _fetch_and_validate_intermediate(url: str) -> str | None:
    """Fetch a CA Issuers URL and return the certificate as PEM, if valid."""
    try:
        response = httpx.get(url, timeout=_AIA_FETCH_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("SSL chain repair: failed to fetch intermediate from %r — %s.", url, exc)
        return None

    body = response.content[:_MAX_AIA_RESPONSE_BYTES]

    # CA Issuers endpoints typically serve DER; some serve PEM directly.
    try:
        if b"BEGIN CERTIFICATE" in body:
            pem = body.decode("ascii")
            x509.load_pem_x509_certificate(pem.encode("ascii"))
        else:
            pem = ssl.DER_cert_to_PEM_cert(body)
            x509.load_der_x509_certificate(body)
    except Exception as exc:
        logger.warning(
            "SSL chain repair: intermediate from %r is not a valid certificate — %s.", url, exc
        )
        return None

    return pem


def _verify_repaired_context(hostname: str, port: int, context: ssl.SSLContext) -> bool:
    """Confirm the repaired context actually completes a trusted handshake."""
    try:
        with socket.create_connection((hostname, port), timeout=_HANDSHAKE_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=hostname):
                return True
    except Exception:
        return False
