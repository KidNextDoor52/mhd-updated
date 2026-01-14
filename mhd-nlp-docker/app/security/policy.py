# app/security/policy.py
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class SharePolicy:
    """
    Central policy knobs for share links and shared downloads.
    Keep this small and explicit so it can be referenced in docs.
    """
    require_recipient_email_match: bool = True
    max_hours: int = int(os.getenv("SHARE_MAX_HOURS", "168"))  # default 7 days
    min_hours: int = int(os.getenv("SHARE_MIN_HOURS", "1"))

    def clamp_expiry_hours(self, hours: int) -> int:
        try:
            h = int(hours)
        except Exception:
            h = 24
        if h < self.min_hours:
            return self.min_hours
        if h > self.max_hours:
            return self.max_hours
        return h

    def validate_recipient(self, email: str) -> Tuple[bool, Optional[str]]:
        e = (email or "").strip().lower()
        if not e:
            return False, "recipient_email required"
        if not _EMAIL_RE.match(e):
            return False, "recipient_email invalid"
        return True, None


policy = SharePolicy()
