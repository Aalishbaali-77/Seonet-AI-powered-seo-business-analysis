from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from apps.common.exceptions import APIError

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "metadata.google.internal",
    "metadata.goog",
    "host.docker.internal",
    "kubernetes",
    "kubernetes.default",
    "kubernetes.default.svc",
}

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443, None}


class SSRFBlocked(APIError):
    status_code = 400
    default_code = "SSRF_BLOCKED"
    default_detail = "This URL is not allowed."


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    # is_global catches ranges the named checks below miss, e.g. the RFC 6598
    # CGNAT block 100.64.0.0/10 that several cloud metadata services (such as
    # Alibaba Cloud's 100.100.100.200) live in.
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or not address.is_global
    )


def resolve_and_validate_host(hostname: str) -> list[str]:
    host = hostname.strip(".").lower()
    if not host or host in BLOCKED_HOSTNAMES or host.endswith(".local") or host.endswith(".internal"):
        raise SSRFBlocked("Internal hostnames are not allowed.")
    try:
        parsed_ip = ipaddress.ip_address(host)
    except ValueError:
        parsed_ip = None
    if parsed_ip is not None:
        if _is_blocked_ip(parsed_ip):
            raise SSRFBlocked("Private or reserved IP addresses are not allowed.")
        return [str(parsed_ip)]

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFBlocked("The hostname could not be resolved.") from exc

    addresses: list[str] = []
    for info in infos:
        ip = info[4][0]
        addr = ipaddress.ip_address(ip)
        if addr.version == 6 and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        if _is_blocked_ip(addr):
            raise SSRFBlocked("The hostname resolves to a private or reserved address.")
        addresses.append(str(addr))
    if not addresses:
        raise SSRFBlocked("The hostname could not be resolved.")
    return addresses


def validate_public_http_url(raw_url: str) -> str:
    if not raw_url or not isinstance(raw_url, str):
        raise SSRFBlocked("A valid website URL is required.")
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFBlocked("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise SSRFBlocked("A valid website URL is required.")
    if parsed.username or parsed.password:
        raise SSRFBlocked("URLs with credentials are not allowed.")
    port = parsed.port
    if port not in ALLOWED_PORTS:
        raise SSRFBlocked("Only ports 80 and 443 are allowed.")
    resolve_and_validate_host(parsed.hostname)
    return parsed.geturl()


def resolve_pinned_target(raw_url: str) -> tuple[str, str, str]:
    """Validate raw_url and return a connection target pinned to a checked IP.

    DNS is resolved and validated here, then the caller must connect to the
    returned pinned_url (an IP literal) rather than the original hostname.
    Otherwise the HTTP client would re-resolve the hostname itself at connect
    time, leaving a window for DNS rebinding: a public IP returned during
    validation, then a private one moments later for the real connection.

    Returns (pinned_url, host_header, sni_hostname). Send host_header as the
    Host header and sni_hostname as the TLS SNI value so virtual hosting and
    certificate validation still match the original hostname.
    """
    validated = validate_public_http_url(raw_url)
    parsed = urlparse(validated)
    addresses = resolve_and_validate_host(parsed.hostname)
    ip = addresses[0]
    netloc_host = f"[{ip}]" if ":" in ip else ip
    netloc = f"{netloc_host}:{parsed.port}" if parsed.port else netloc_host
    pinned_url = parsed._replace(netloc=netloc).geturl()
    return pinned_url, parsed.netloc, parsed.hostname
