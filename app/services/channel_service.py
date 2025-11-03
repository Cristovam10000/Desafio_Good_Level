"""Channel business logic service."""

from __future__ import annotations

from typing import Optional

from app.repositories.protocols import ChannelRepositoryProtocol


class ChannelService:
    """Service for channel-related business logic."""

    def __init__(self, repository: ChannelRepositoryProtocol):
        """Initialize the service with a repository instance."""
        self.repository = repository

    def get_all(self, user_store_ids: Optional[list[int]] = None) -> list[dict]:
        """Get all channels, optionally filtered by user's accessible stores."""
        return self.repository.get_all(user_store_ids)

    def get_by_name(self, name: str) -> Optional[dict]:
        """Get a specific channel by name."""
        return self.repository.get_by_name(name)
