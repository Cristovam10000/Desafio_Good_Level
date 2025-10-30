from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import httpx
from jose import jwt
from app.core.config import settings


class CubeError(RuntimeError):
    def __init__(self, status_code: int, message: str, details: Optional[dict] = None):
        super().__init__(f"[Cube {status_code}] {message}")
        self.status_code = status_code
        self.message = message
        self.details = details or {}


_TOKEN_CACHE: Tuple[str, float] = ("", 0.0)


def _cube_token() -> str:
    global _TOKEN_CACHE
    token, expires_at = _TOKEN_CACHE
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    # reaproveita token se ainda estiver válido (com 60s de folga)
    if token and now_ts < (expires_at - 60):
        return token

    payload = {
        "iat": int(now_ts),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "scope": "analytics",
    }
    token = jwt.encode(payload, settings.CUBE_API_TOKEN, algorithm="HS256")
    _TOKEN_CACHE = (token, payload["exp"])
    return token


def _default_headers(request_id: Optional[str] = None) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {_cube_token()}"}
    if request_id:
        headers["X-Request-Id"] = request_id
    return headers


async def _request_with_retries(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    retries: int = 2,
    backoff_base: float = 0.25,
) -> httpx.Response:
    last_exc: Optional[Exception] = None
    attempt = 0
    async with httpx.AsyncClient(timeout=timeout) as client:
        while attempt <= retries:
            try:
                resp = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                # 2xx ok
                if 200 <= resp.status_code < 300:
                    return resp
                # 4xx: não adianta tentar de novo
                if 400 <= resp.status_code < 500:
                    return resp
                # 5xx: tenta de novo com backoff
                # cai para o fluxo de retry abaixo
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
            # se chegou aqui, houve 5xx ou exceção de rede/timeout
            attempt += 1
            if attempt > retries:
                break
            await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
        # esgotou tentativas
        if last_exc:
            raise last_exc
        return resp  # type: ignore[misc]


async def cube_load(
    query: Dict[str, Any],
    *,
    request_id: Optional[str] = None,
    timeout: float = 30.0,
    retries: int = 2,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    base = settings.CUBE_API_URL.rstrip("/")
    url = f"{base}/v1/load"

    headers = _default_headers(request_id)
    if extra_headers:
        headers.update(extra_headers)

    params = {"query": json.dumps(query, ensure_ascii=False)}
    resp = await _request_with_retries(
        "POST",
        url,
        params=params,
        headers=headers,
        timeout=timeout,
        retries=retries,
    )

    if not (200 <= resp.status_code < 300):
        try:
            details = resp.json()
        except Exception:
            details = {"raw": resp.text[:500]}
        raise CubeError(resp.status_code, "Erro ao consultar Cube /load", details)

    try:
        return resp.json()
    except Exception as exc:
        raise CubeError(resp.status_code, "Resposta JSON inválida do Cube", {"error": str(exc)})


async def cube_meta(
    *,
    request_id: Optional[str] = None,
    timeout: float = 20.0,
    retries: int = 1,
) -> Dict[str, Any]:

    base = settings.CUBE_API_URL.rstrip("/")
    url = f"{base}/v1/meta"
    headers = _default_headers(request_id)

    resp = await _request_with_retries(
        "GET",
        url,
        headers=headers,
        timeout=timeout,
        retries=retries,
    )

    if not (200 <= resp.status_code < 300):
        try:
            details = resp.json()
        except Exception:
            details = {"raw": resp.text[:500]}
        raise CubeError(resp.status_code, "Erro ao consultar Cube /meta", details)

    try:
        return resp.json()
    except Exception as exc:
        raise CubeError(resp.status_code, "Resposta JSON inválida do Cube", {"error": str(exc)})


# -----------------------------------------------------------------------------
# Helpers opcionais (não obrigatórios, mas úteis)
# -----------------------------------------------------------------------------

def build_time_dimension(dimension: str, *, date_range: Tuple[str, str], granularity: str = "day",) -> Dict[str, Any]:
    if granularity not in {"hour", "day", "week", "month"}:
        raise ValueError("granularity deve ser hour|day|week|month")
    start, end = date_range
    return {
        "dimension": dimension,
        "dateRange": [start, end],
        "granularity": granularity,
    }


def build_filter_equals(dimension: str, values: list[str]) -> Dict[str, Any]:
    return {"dimension": dimension, "operator": "equals", "values": values}


