"""Channels domain endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import AccessClaims, require_roles
from app.services.channel_service import ChannelService


router = APIRouter(prefix="/channels", tags=["channels"])


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class ChannelRow(BaseModel):
    """Channel list response model."""
    channel_id: int
    channel_name: str


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.get("", response_model=list[ChannelRow])
def get_channels(
    user: AccessClaims = Depends(require_roles("viewer", "analyst", "manager", "admin")),
):
    """Lista todos os canais de venda disponíveis."""
    allowed_store_ids = user.stores or []
    
    service = ChannelService()
    channels = service.get_all(allowed_store_ids)

    return [
        ChannelRow(
            channel_id=c["id"],
            channel_name=c["name"],
        )
        for c in channels
    ]
