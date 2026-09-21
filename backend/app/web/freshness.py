"""Date, freshness, and version tracking engine (sections 20, 21)."""

import re
import time
from datetime import date, datetime
from typing import Optional, Tuple


_DATE_PATTERNS = [
    re.compile(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"),  # 2026-03-15
    re.compile(r"\b(0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](20\d{2})\b"),  # 15/03/2026
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(?:0?[1-9]|[12]\d|3[01]),?\s+(20\d{2})\b", re.I),
]

_VERSION_PATTERN = re.compile(r"\bv?(\d+(?:\.\d+)+(?:-[a-z0-9\.]+)?)", re.I)


def extract_date(text: str) -> Optional[str]:
    """Extract standard YYYY-MM-DD or year string from snippet or metadata."""
    if not text:
        return None
    for p in _DATE_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(0)
    return None


def evaluate_freshness(published_str: Optional[str], current_year: Optional[int] = None) -> str:
    """Classify freshness: CURRENT, RECENT, HISTORICAL, OUTDATED, or UNKNOWN."""
    if not published_str:
        return "UNKNOWN"

    now_year = current_year or date.today().year
    extracted = extract_date(published_str)
    if not extracted:
        return "UNKNOWN"

    year_match = re.search(r"\b(19|20)\d{2}\b", extracted)
    if not year_match:
        return "UNKNOWN"

    pub_year = int(year_match.group(0))

    if pub_year >= now_year:
        return "CURRENT"
    elif pub_year == now_year - 1:
        return "RECENT"
    elif pub_year >= now_year - 4:
        return "HISTORICAL"
    else:
        return "OUTDATED"


def extract_version(text: str) -> Optional[str]:
    """Extract software or model version string (e.g. 'v19.0', '3.5', '5.2')."""
    if not text:
        return None
    m = _VERSION_PATTERN.search(text)
    return m.group(1) if m else None


def check_version_compatibility(query_version: Optional[str], source_text: str) -> Tuple[bool, Optional[str]]:
    """Verify if source version matches requested query version."""
    if not query_version:
        return True, None

    found_ver = extract_version(source_text)
    if not found_ver:
        return True, None

    # Check major version match
    q_major = query_version.split(".")[0]
    f_major = found_ver.split(".")[0]
    if q_major != f_major:
        return False, f"Version mismatch: requested v{query_version} but found v{found_ver}"

    return True, found_ver
