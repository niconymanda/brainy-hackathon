import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit


def debug_log(message, secrets=()):
    for value in (*secrets, *(value for key, value in os.environ.items()
                              if any(word in key.upper() for word in ("KEY", "TOKEN", "PASSWORD", "SECRET")))):
        if isinstance(value, str) and value:
            message = message.replace(value, "[redacted]")
    message = re.sub(r"https?://[^\s'\"<>]+", _safe_url, message)
    message = re.sub(r"(?im)^.*\b(?:headers?|authorization|cookie|bearer|api[_-]?key)\b.*$",
                     "[redacted header or credential detail]", message)
    print(message, file=sys.stderr, flush=True)


def _safe_url(match):
    try:
        url = urlsplit(match.group())
        host = url.netloc.rsplit("@", 1)[-1]
        return urlunsplit((url.scheme, host, url.path, "[redacted]" if url.query else "", ""))
    except ValueError:
        return "[redacted URL]"
