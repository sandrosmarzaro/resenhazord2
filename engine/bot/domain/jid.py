"""JID (Jabber ID) utilities for WhatsApp identifiers."""

import re

_JID_SUFFIX_RE = re.compile(r'@lid|@s\.whatsapp\.net', re.IGNORECASE)


def strip_jid(jid: str) -> str:
    """Remove the @lid or @s.whatsapp.net suffix from a JID."""
    return _JID_SUFFIX_RE.sub('', jid)
