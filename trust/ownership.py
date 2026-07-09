"""
trust/ownership.py — richer ownership checks for metric/model owners.

check_owner(owner, approved_domains) -> list[Issue]

Rule names emitted:
  owner_missing         — owner is None, empty string, or whitespace-only
  owner_placeholder     — owner matches a known placeholder word (anchored, case-insensitive)
                          e.g. "owner", "placeholder", "tbd", "todo", "unknown", "test"
                          NOTE: does NOT reject valid emails like cp-da-1@example.com
  owner_invalid_email   — owner is a non-empty string but not a valid email address
  owner_domain          — email domain not in the approved allowlist
                          (only fired when approved_domains is non-empty)
"""
from __future__ import annotations

import re
from trust.report import Issue

# Anchored placeholder pattern — exact word match only.
# Must NOT reject valid emails like cp-da-1@example.com.
_PLACEHOLDER_RE = re.compile(
    r"^(owner|placeholder|tbd|todo|unknown|test)$",
    re.IGNORECASE,
)

# Simple but sufficient email validator: local@domain.tld
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_LOCATION = "<ownership>"


def check_owner(owner: str | None, approved_domains: list[str]) -> list[Issue]:
    """
    Validate an owner field against the approved domain allowlist.

    Parameters
    ----------
    owner:            raw value from config.meta.owner (str or None)
    approved_domains: list of allowed email domains from load_config(); may be empty

    Returns a (possibly empty) list of Issue objects.
    An empty list means the owner is valid.
    """
    issues: list[Issue] = []

    # 1. Missing / blank
    if not owner or not str(owner).strip():
        issues.append(Issue(
            severity="warning",
            dimension="ownership",
            rule="owner_missing",
            message="owner is missing or blank",
            location=_LOCATION,
        ))
        return issues  # no further checks possible without a value

    owner = str(owner).strip()

    # 2. Placeholder word — anchored match; cp-da-1@example.com is NOT a match
    if _PLACEHOLDER_RE.fullmatch(owner):
        issues.append(Issue(
            severity="warning",
            dimension="ownership",
            rule="owner_placeholder",
            message=f"owner '{owner}' looks like a placeholder",
            location=_LOCATION,
        ))
        return issues  # treat placeholder as terminal — no email checks

    # 3. Email format check
    if not _EMAIL_RE.match(owner):
        issues.append(Issue(
            severity="warning",
            dimension="ownership",
            rule="owner_invalid_email",
            message=f"owner '{owner}' is not a valid email address",
            location=_LOCATION,
        ))
        return issues  # domain check requires a valid email

    # 4. Domain allowlist — only fires when approved_domains is non-empty
    if approved_domains:
        domain = owner.split("@", 1)[1]
        if domain not in approved_domains:
            issues.append(Issue(
                severity="warning",
                dimension="ownership",
                rule="owner_domain",
                message=(
                    f"owner '{owner}' domain '{domain}' is not in the approved list "
                    f"{approved_domains}"
                ),
                location=_LOCATION,
            ))

    return issues
