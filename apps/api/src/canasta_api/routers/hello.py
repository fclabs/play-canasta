"""Hello router."""

from __future__ import annotations

from fastapi import APIRouter

from canasta_api.schemas.hello import DEFAULT_PLAYER_NAME, HelloResponse, PlayerName
from canasta_api.services.hello import build_welcome_message
from canasta_api.settings import API_V1_PREFIX

router = APIRouter(prefix=API_V1_PREFIX, tags=["hello"])


@router.get("/hello")
def get_hello(name: PlayerName = DEFAULT_PLAYER_NAME) -> HelloResponse:
    return HelloResponse(message=build_welcome_message(name))
