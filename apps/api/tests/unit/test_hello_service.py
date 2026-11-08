from __future__ import annotations

import pytest

from canasta_api.schemas.hello import validate_name
from canasta_api.services.hello import build_welcome_message

pytestmark = pytest.mark.unit


def test_welcome_message_includes_name():
    # Given / When
    message = build_welcome_message("Ana")

    # Then
    assert message == "Welcome to Canasta, Ana!"


@pytest.mark.parametrize("name", ["a", "José Núñez", "O'Brien-Smith_2", "x" * 40])
def test_validate_name_accepts_allowed_names(name: str):
    # Given / When / Then
    assert validate_name(name) == name


@pytest.mark.parametrize("name", ["   ", "<script>", "a;b", "a/b", "x²"])
def test_validate_name_rejects_invalid_names(name: str):
    # Given / When / Then
    with pytest.raises(ValueError):
        validate_name(name)
