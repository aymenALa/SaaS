"""Optional text privacy helpers kept separate from visual processing."""
import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")


def redact_sensitive_text(text: str, replacement: str = "[REDACTED]") -> str:
    text = EMAIL.sub(replacement, text)
    return PHONE.sub(replacement, text)
