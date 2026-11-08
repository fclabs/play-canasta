"""Hello request (query) validation and response schema."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import AfterValidator, BaseModel

from canasta_api.settings import (
    DEFAULT_NAME,
    NAME_ALLOWED_PUNCTUATION,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)


def validate_name(value: str) -> str:
    """FR-012: letters (isalpha), digits (isdecimal), space, ' - _; not blank.

    The value is returned unchanged (no trimming or normalisation).
    """
    if not value.strip(" "):
        raise ValueError("name must not consist only of spaces")
    for char in value:
        if not (char.isalpha() or char.isdecimal() or char in NAME_ALLOWED_PUNCTUATION):
            raise ValueError(
                "name may only contain letters, digits, spaces, apostrophes, "
                "hyphens and underscores"
            )
    return value


PlayerName = Annotated[
    str,
    Query(
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
        description="Player name (1-40 letters, digits, spaces, ' - _).",
    ),
    AfterValidator(validate_name),
]

DEFAULT_PLAYER_NAME: str = DEFAULT_NAME


class HelloResponse(BaseModel):
    message: str
