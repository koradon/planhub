from __future__ import annotations

import re


def slugify(value: str, *, fallback: str) -> str:
    """Convert a string to a stable slug with a caller-defined fallback."""
    slug: list[str] = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif char in {" ", "-", "_"}:
            slug.append("-")
    normalized = "".join(slug).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or fallback
