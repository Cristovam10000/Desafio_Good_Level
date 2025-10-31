from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class DemoUser:
    """Simple in-memory representation of demo users for the challenge."""

    id: str
    email: str
    name: str
    password: str
    roles: List[str]
    stores: List[int]


_DEMO_USERS: List[DemoUser] = [
    DemoUser(
        id="user-maria",
        email="maria@restaurantbi.com",
        name="Maria Ferreira",
        password="123456",
        roles=["manager"],
        stores=[1, 2, 3],
    ),
    DemoUser(
        id="user-joao",
        email="joao@restaurantbi.com",
        name="Joao Lima",
        password="654321",
        roles=["analyst"],
        stores=[2],
    ),
]

_BY_EMAIL: Dict[str, DemoUser] = {user.email.lower(): user for user in _DEMO_USERS}
_BY_ID: Dict[str, DemoUser] = {user.id: user for user in _DEMO_USERS}


def get_demo_user_by_email(email: str) -> Optional[DemoUser]:
    return _BY_EMAIL.get(email.lower())


def get_demo_user_by_id(user_id: str) -> Optional[DemoUser]:
    return _BY_ID.get(user_id)


def list_demo_users() -> Iterable[DemoUser]:
    return tuple(_DEMO_USERS)
