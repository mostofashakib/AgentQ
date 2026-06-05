import re
from typing import Optional

PII_PATTERNS: list[tuple[str, str]] = [
    # pattern, label
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{3}\s\d{2}\s\d{4}\b", "SSN"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b", "credit_card"),
    (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "email"),
    (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone"),
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "ip_address"),
    (r"\b(?:passport|ssn|dob|date.of.birth|national.id)\s*[:\-=]\s*\S+", "id_document"),
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"forget\s+(everything|all)\s+(?:you|above)",
    r"jailbreak",
    r"dan\s+mode",
    r"system\s*prompt\s*[:=]",
    r"<\s*/?system\s*>",
    r"\[\[.*?override.*?\]\]",
    r"disregard\s+(all\s+)?(?:prior|previous|above)\s+(?:instructions?|context)",
]

EXFILTRATION_PATTERNS = [
    r"https?://[^\s\"'>]+",
    r"webhook",
    r"\bcurl\s+",
    r"requests?\.(get|post|put|delete|patch)",
    r"data:[^;]+;base64,",
    r"base64\.b64encode",
    r"smtp|sendmail|send_email",
]

HIGH_RISK_TOOLS = {
    "send_email", "send_message", "post_tweet", "create_pr",
    "delete_file", "drop_table", "rm_rf", "format_disk",
    "install_package", "exec_command", "eval", "run_subprocess",
    "http_request", "make_request", "fetch_url",
}

ROLE_CONFUSION_MARKERS = [
    "you are now", "pretend to be", "act as if you are",
    "roleplay as", "from now on you are", "your new persona",
    "ignore your training", "override your instructions",
]


def find_injection(text: str) -> Optional[str]:
    for pattern in INJECTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def find_exfiltration(text: str) -> Optional[str]:
    for pattern in EXFILTRATION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def is_high_risk_tool(tool_name: str) -> bool:
    return tool_name.lower() in HIGH_RISK_TOOLS


def find_role_confusion(text: str) -> Optional[str]:
    text_lower = text.lower()
    for marker in ROLE_CONFUSION_MARKERS:
        if marker in text_lower:
            return marker
    return None


def find_pii(text: str) -> Optional[tuple[str, str]]:
    """Return (matched_text, pii_label) for the first PII pattern found."""
    for pattern, label in PII_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0), label
    return None
