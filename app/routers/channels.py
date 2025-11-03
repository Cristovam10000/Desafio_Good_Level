"""Channels domain endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.dependencies import get_channel_service
from app.services.channel_service import ChannelService


router = APIRouter(prefix="/channels", tags=["channels"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class ChannelRow(BaseModel):
    """Channel list response model."""
    channel_id: int
    channel_name: str
    store_id: int
    store_name: str
    channel_store_key: str


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("", response_model=list[ChannelRow])
def get_channels(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
    service: ChannelService = Depends(get_channel_service),
):
    """Lista todos os canais de venda disponíveis."""
    allowed_store_ids = user.stores or []
    
    channels = service.get_all(allowed_store_ids)

    return [
        ChannelRow(
            channel_id=c["channel_id"],
            channel_name=c["channel_name"],
            store_id=c["store_id"],
            store_name=c["store_name"],
            channel_store_key=c["channel_store_key"],
        )
        for c in channels
    ]
