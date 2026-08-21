import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple


BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "local",
    "broadcasthost",
    "metadata.google.internal",
}


def is_ssrf_safe(url: str) -> Tuple[bool, str]:
    """
    Validates a URL against Server-Side Request Forgery (SSRF) risks.
    Blocks private subnets, loopback addresses, link-local IPs, cloud metadata,
    and non-http(s) schemes.
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or invalid"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Failed to parse URL: {str(e)}"

    # 1. Scheme Check
    if parsed.scheme not in ("http", "https"):
        return False, f"Unsupported protocol scheme '{parsed.scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL lacks a valid hostname."

    hostname_lower = hostname.lower()

    # 2. Blocked Hostnames
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, f"Access to internal/private hostname '{hostname}' is forbidden."

    # 3. Direct IP Address Check or DNS Resolution
    try:
        # Check if direct IP literal
        ip_obj = ipaddress.ip_address(hostname_lower)
        ips_to_check = [ip_obj]
    except ValueError:
        # Resolve hostname via DNS
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ips_to_check = []
            for item in addr_info:
                ip_str = item[4][0]
                try:
                    ips_to_check.append(ipaddress.ip_address(ip_str))
                except ValueError:
                    continue
        except socket.gaierror:
            # If domain cannot be resolved by DNS, reject for safety
            return False, f"Could not resolve domain name '{hostname}'."

    if not ips_to_check:
        return False, f"No IP addresses resolved for domain '{hostname}'."

    for ip in ips_to_check:
        # Check for Private, Loopback, Link-Local, Reserved, Multicast, Unspecified
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False, f"Target IP address '{ip}' is in a private, loopback, or reserved network range."

        # Explicit Cloud Metadata check (e.g. AWS 169.254.169.254, GCP metadata)
        if str(ip) == "169.254.169.254" or str(ip) == "169.254.169.253":
            return False, f"Access to cloud metadata IP '{ip}' is forbidden."

    return True, ""
