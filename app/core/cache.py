from __future__ import annotations
import hashlib
import json
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import settings

# ---------------------------------------------------------------------------
# Helpers de ETag
# ---------------------------------------------------------------------------

def make_etag_from_bytes(body: bytes) -> str:
    return hashlib.md5(body).hexdigest()


def dumps_deterministic(obj: Any) -> bytes:
    return json.dumps(
        obj,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Aplicação de headers (Cache-Control, ETag, Vary)
# ---------------------------------------------------------------------------

def _cache_control_value(max_age: Optional[int], swr: Optional[int]) -> str:

    max_age = settings.CACHE_MAX_AGE if max_age is None else max_age
    swr = settings.CACHE_SWR if swr is None else swr
    return f"max-age={int(max_age)}, stale-while-revalidate={int(swr)}"


def apply_cache_headers(
    response: Response,
    etag: str,
    *,
    max_age: Optional[int] = None,
    swr: Optional[int] = None,
    vary_authorization: bool = True,
) -> None:
    """
    Aplica ETag e Cache-Control na resposta. Opcionalmente adiciona Vary: Authorization.
    """
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = _cache_control_value(max_age, swr)
    if vary_authorization:
        # Importante quando o conteúdo depende do usuário (ex.: permissões, escopo de lojas)
        response.headers["Vary"] = "Authorization"


# ---------------------------------------------------------------------------
# Resposta JSON com ETag (+ 304 se bater If-None-Match)
# ---------------------------------------------------------------------------

def etag_json(
    request: Request,
    payload: Any,
    *,
    status_code: int = 200,
    max_age: Optional[int] = None,
    swr: Optional[int] = None,
    vary_authorization: bool = True,
) -> Response:
    
    body = dumps_deterministic(payload)
    etag = make_etag_from_bytes(body)

    # Revalidação condicional
    inm = request.headers.get("If-None-Match")
    if inm and inm == etag:
        resp = Response(status_code=304)
        apply_cache_headers(resp, etag, max_age=max_age, swr=swr, vary_authorization=vary_authorization)
        return resp

    # Resposta normal
    resp = JSONResponse(status_code=status_code, content=payload)
    apply_cache_headers(resp, etag, max_age=max_age, swr=swr, vary_authorization=vary_authorization)
    return resp
