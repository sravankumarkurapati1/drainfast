"""Split a 311 closure_reason into the crew's own note and the system status phrase."""
import html
import re

_PREFIX = re.compile(
    r"^\s*case\s+closed\.?\s*"
    r"(?:fixing\s+technical\s+issue\s+)?"
    r"(?:(?:original\s+)?closed\s+date\s*:\s*"
    r"(?:\d{4}-\d{2}-\d{2}[ t]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?"
    r"|[a-z]{3}\s+[a-z]{3}\s+\d{1,2}\s+\d{1,2}:\d{2}:\d{2}\s+[a-z]{2,5}\s+\d{4})"
    r")?\s*",
    re.IGNORECASE,
)

# Longest phrases first so "Case Resolved" wins over "Resolved".
STATUS_PHRASES: tuple[str, ...] = (
    "Case Referred to External Agency",
    "Duplicate of Existing Case",
    "Case Resolved",
    "Case Invalid",
    "Case Noted",
    "Resolved",
    "Noted",
)
_STATUS = re.compile(
    r"^(" + "|".join(re.escape(p) for p in STATUS_PHRASES) + r")(?=$|[\s.,:;!-])[\s.,:;!-]*",
    re.IGNORECASE,
)
_EXCLUDE = re.compile(
    r"\btest\b|\binvalid\b|\berror|\bwrong\s*e\s*-?\s*form|\bduplicate", re.IGNORECASE
)


def normalize_text(text: object) -> str:
    """Unescape HTML entities, straighten curly quotes and collapse whitespace."""
    if text is None or (isinstance(text, float) and text != text):
        return ""
    s = html.unescape(str(text))
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


def split_closure(closure_reason: object) -> tuple[str, str]:
    """Return (crew_note, status_phrase) from a raw closure_reason.

    Removes the "Case Closed[. Closed date : <timestamp>]" prefix, then one leading
    status phrase. Either part may be "".
    """
    s = normalize_text(closure_reason)
    status = ""
    # Re-closed cases repeat the system text ("... Case Resolved Case Closed. Fixing
    # Technical Issue Original Closed date : ..."), so strip until nothing changes.
    for _ in range(5):
        before = s
        s = _PREFIX.sub("", s, count=1)
        m = _STATUS.match(s)
        if m:
            status = status or m.group(1)
            s = s[m.end():]
        if s == before:
            break
    return s.strip(), status


def is_excluded(note: str, status: str) -> bool:
    """True when the note or status mentions test, invalid, error, wrong e-form or duplicate."""
    return bool(_EXCLUDE.search(f"{note} {status}"))
