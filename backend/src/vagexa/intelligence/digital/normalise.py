"""Normalise investigator-supplied infrastructure indicators. Nothing is fetched."""

import ipaddress
from dataclasses import dataclass

OVERLAP_LIMITATION = (
    "Shared hosting, a shared address, or shared DNS does not establish "
    "common ownership, common control, or a common operator."
)


class IndicatorRejected(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalise_domain(raw: str) -> str:
    text = raw.strip().lower()
    if text.endswith("."):
        text = text[:-1]
    if not text or any(char.isspace() for char in text) or "/" in text or "\\" in text or "://" in text:
        raise IndicatorRejected("invalid_domain", "The domain is empty, spaced, or a URL.")
    try:
        text = text.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise IndicatorRejected("invalid_domain", "The domain is not valid internationalised text.") from exc
    if ".." in text or text.startswith(".") or text.endswith("."):
        raise IndicatorRejected("invalid_domain", "The domain has an empty label.")
    return text


def normalise_ip(raw: str) -> str:
    text = raw.strip()
    if text.count(".") == 3 and ":" not in text:
        parts = text.split(".")
        if all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            text = ".".join(str(int(part)) for part in parts)
    try:
        address = ipaddress.ip_address(text)
    except ValueError as exc:
        raise IndicatorRejected("invalid_ip", "The value is not an IP address.") from exc
    return str(address)


def ip_version(value: str) -> int:
    return ipaddress.ip_address(value).version


@dataclass(frozen=True)
class LookupRefusal:
    code: str
    message: str


def refuse_lookup_target(raw: str) -> LookupRefusal | None:
    """Reject destinations a lookup must not contact. This function opens no socket."""
    text = raw.strip()
    lowered = text.lower()
    if "://" in lowered or "/" in text or "\\" in text or "@" in text:
        return LookupRefusal("url_rejected", "A lookup accepts a domain or address, not a URL.")
    blocked_name = lowered in {"localhost", "metadata.google.internal"}
    blocked_suffix = lowered.endswith(".local") or lowered.endswith(".internal")
    if blocked_name or blocked_suffix:
        return LookupRefusal("name_rejected", "That name is not a public lookup target.")
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return None
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return LookupRefusal("address_rejected", "That address is not a public lookup target.")
    return None
