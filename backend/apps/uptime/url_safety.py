"""URL safety checks to mitigate SSRF.

Used in two places:
1. Serializer validation — reject obvious internal targets at create/edit time.
2. `perform_check` — re-resolve right before the HTTP call to catch DNS games.

Defense in depth, not airtight. A determined attacker with DNS-rebinding could
still slip through the TOCTOU window between resolution and the actual request.
For most internal monitoring use cases this is good enough.
"""

import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse


# Hostnames we always reject regardless of resolution.
BLOCKED_HOSTNAMES = {"localhost", "ip6-localhost", "ip6-loopback"}

# Explicit SSRF-relevant networks instead of Python's `is_private`/`is_reserved`,
# which also cover benchmark (198.18.0.0/15) and documentation ranges. Local
# proxies (Clash, Surge, etc.) hand out 198.18.0.0/15 fake IPs for public
# hostnames they tunnel — treating those as "internal" produces false positives
# against legitimate public sites.
_BLOCKED_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",       # this network
        "10.0.0.0/8",      # RFC 1918
        "127.0.0.0/8",     # loopback
        "169.254.0.0/16",  # link-local (incl. cloud metadata)
        "172.16.0.0/12",   # RFC 1918
        "192.168.0.0/16",  # RFC 1918
        "224.0.0.0/4",     # multicast
        "::/128",          # IPv6 unspecified
        "::1/128",         # IPv6 loopback
        "fc00::/7",        # IPv6 ULA
        "fe80::/10",       # IPv6 link-local
        "ff00::/8",        # IPv6 multicast
    )
)


def _ip_is_blocked(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return any(ip in net for net in _BLOCKED_NETWORKS)


def check_url_safety(url: str) -> Tuple[bool, str]:
    """Return (is_safe, reason). reason is empty when safe."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 解析失败"

    if parsed.scheme not in ("http", "https"):
        return False, f"不支持的协议: {parsed.scheme}"

    host = (parsed.hostname or "").lower()
    if not host:
        return False, "URL 缺少主机名"

    if host in BLOCKED_HOSTNAMES:
        return False, f"禁止访问内部地址: {host}"

    # If the host is itself a literal IP, check it directly without DNS.
    if _ip_is_blocked(host):
        return False, f"禁止访问内部地址: {host}"

    # Otherwise resolve via DNS and reject if any record is private/loopback.
    # If the host cannot be resolved we let it pass — the subsequent HTTP request
    # will fail with a ConnectionError on its own, no SSRF risk to gate against.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True, ""

    for info in infos:
        ip = info[4][0]
        if _ip_is_blocked(ip):
            return False, f"主机名解析到内部地址: {host} → {ip}"

    return True, ""
