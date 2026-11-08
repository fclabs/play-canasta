"""Hello business logic. Must not import HTTP frameworks (BR-005)."""

from __future__ import annotations


def build_welcome_message(name: str) -> str:
    """Return the welcome message for an already validated player name."""
    return f"Welcome to Canasta, {name}!"
