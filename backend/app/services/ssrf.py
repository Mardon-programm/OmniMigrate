"""SSRF hardening — validates URLs and resolves IPs before git clone operations."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.services.git_sandbox import GitOperationError

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url_for_clone(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http", "git"):
        raise GitOperationError(f"URL scheme '{parsed.scheme}' is not allowed")
    hostname = parsed.hostname
    if not hostname:
        raise GitOperationError("URL has no hostname")
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise GitOperationError(f"DNS resolution failed for '{hostname}': {exc}") from exc
    if not infos:
        raise GitOperationError(f"DNS resolution returned no results for '{hostname}'")
    seen = set()
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip in seen:
            continue
        seen.add(ip)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise GitOperationError(
                    f"Hostname '{hostname}' resolves to private/internal IP {ip} ({net})"
                )
    return url
