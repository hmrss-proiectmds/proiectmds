"""
Global slowapi rate-limiter instance and key function.

Key strategy: use the client IP from X-Forwarded-For (when behind a proxy)
falling back to the direct connection IP. This prevents a single IP from
burning through limits across multiple user accounts.
"""

from fastapi import Request
from slowapi import Limiter


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=_get_client_ip)
