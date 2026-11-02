import threading
import time
from typing import Optional


class TokenBlocklist:
    """
    Thread-safe in-memory JWT blocklist manager.
    Tracks revoked JTIs with their expiration timestamps and provides automatic TTL cleanup.
    """

    def __init__(self):
        self._revoked_tokens = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: Optional[float] = None) -> None:
        if not jti:
            return
        exp = float(expires_at) if expires_at is not None else (time.time() + 7 * 86400)
        with self._lock:
            self._cleanup_expired()
            self._revoked_tokens[jti] = exp

    def is_revoked(self, jti: str) -> bool:
        if not jti:
            return False
        with self._lock:
            exp = self._revoked_tokens.get(jti)
            if exp is None:
                return False
            if time.time() > exp:
                del self._revoked_tokens[jti]
                return False
            return True

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, exp in self._revoked_tokens.items() if exp < now]
        for k in expired_keys:
            del self._revoked_tokens[k]

    def clear(self) -> None:
        """Utility for testing."""
        with self._lock:
            self._revoked_tokens.clear()


token_blocklist = TokenBlocklist()
