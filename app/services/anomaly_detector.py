"""
Serviço especializado em detecção de anomalias em dados de vendas.
Usa IA com prompt otimizado para identificar padrões anormais rapidamente.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Optional, Sequence
from datetime import datetime, timedelta
import pandas as pd

from app.core.config import settings
from app.infra.db import fetch_all
from app.services.anomaly_analysis import AnomalyPromptBuilder


class AnomalyDetectorError(RuntimeError):
    """Erro relacionado à detecção de anomalias."""


def _load_ai_dependencies() -> tuple:
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise AnomalyDetectorError(
            "Dependências de IA não encontradas. Instale-as com "
            "`pip install langchain langchain-google-genai google-generativeai`."
        ) from exc
    return ChatPromptTemplate, ChatGoogleGenerativeAI


@lru_cache(maxsize=1)
def _get_anomaly_chain():
    """Chain LangChain otimizada para detecção rápida de anomalias."""
    if not settings.GOOGLE_API_KEY:
        raise AnomalyDetectorError(
            "GOOGLE_API_KEY não configurada. Defina a chave do Gemini para habilitar detecção de anomalias."
        )

    ChatPromptTemplate, ChatGoogleGenerativeAI = _load_ai_dependencies()

    prompt = ChatPromptTemplate.from_template(
        "Você é um detector de anomalias especializado em dados de restaurantes.\n\n"
        "MISSÃO: Identificar TODAS as 4 anomalias a seguir nos dados:\n"
        "1. QUEDA SEMANAL: Semana com queda significativa nas vendas (~20-30% ou mais)\n"
        "2. PICO PROMOCIONAL: Dia com vendas muito acima da média (2x ou mais, eventos especiais)\n"
        "3. CRESCIMENTO LINEAR: Loja com crescimento consistente (~4-5% ao mês ou mais)\n"
        "4. SAZONALIDADE: Produtos com variação temporal significativa (80%+ entre períodos)\n\n"
        "DADOS:\n{data}\n\n"
        "INSTRUÇÕES:\n"
        "- Analise TODOS os dados fornecidos buscando padrões anormais\n"
        "- Para cada tipo de anomalia, identifique se existe algum exemplo nos dados\n"
        "- Seja ESPECÍFICO com datas, valores e percentuais REAIS dos dados\n"
        "- Se encontrar uma anomalia, descreva com detalhes: quando, onde, magnitude\n"
        "- Use os dados estatísticos (média, desvio padrão, z-scores) para validar\n"
        "- Se não encontrar uma anomalia específica, diga 'NÃO DETECTADA'\n\n"
        "FORMATO DE RESPOSTA (uma linha por anomalia):\n"
        "QUEDA_SEMANAL: [descrição detalhada com semana e % exato] OU NÃO DETECTADA\n"
        "PICO_PROMOCIONAL: [descrição detalhada com dia e múltiplo exato] OU NÃO DETECTADA\n"
        "CRESCIMENTO_LINEAR: [descrição detalhada com loja/canal e % mensal] OU NÃO DETECTADA\n"
        "SAZONALIDADE: [descrição detalhada com produto e % de variação] OU NÃO DETECTADA"
    )

    # Modelo otimizado para velocidade (usando as mesmas configs do insights)
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.1,  # Baixa temperatura para respostas mais determinísticas
        max_output_tokens=2000,  # Aumentar para permitir resposta completa
    )

    return prompt | llm


def _fetch_anomaly_data(
    start_dt: datetime,
    end_dt: datetime,
    store_ids: Optional[list[int]],
    channel_ids: Optional[Sequence[int]],
) -> dict:
    """Busca dados otimizados para detecção de anomalias."""
    
    # Query 1: Vendas diárias com detalhamento
    sql_daily = """
    SELECT 
        DATE(s.created_at) AS day,
        s.store_id,
        s.channel_id,
        SUM(s.total_amount)::float AS revenue,
        COUNT(*)::int AS orders
    FROM sales s
    WHERE s.sale_status_desc = 'COMPLETED'
        AND s.created_at >= :start_dt
        AND s.created_at < :end_dt
    """
    params_daily = {"start_dt": start_dt, "end_dt": end_dt}
    
    if store_ids:
        sql_daily += " AND s.store_id = ANY(:store_ids)"
        params_daily["store_ids"] = list(store_ids) if not isinstance(store_ids, list) else store_ids
    if channel_ids:
        sql_daily += " AND s.channel_id = ANY(:channel_ids)"
        params_daily["channel_ids"] = list(channel_ids) if not isinstance(channel_ids, list) else channel_ids
    
    sql_daily += " GROUP BY DATE(s.created_at), s.store_id, s.channel_id ORDER BY day, store_id, channel_id"
    
    try:
        daily_data = fetch_all(sql_daily, params_daily, timeout_ms=3000)
    except Exception as exc:
        raise AnomalyDetectorError(f"Erro ao buscar dados diários: {exc}") from exc
    df_daily = pd.DataFrame(daily_data)
    
    # Query 2: Top produtos com tendência temporal (OTIMIZADA)
    sql_products = """
    SELECT 
        p.id AS product_id,
        p.name AS product_name,
        DATE_TRUNC('month', s.created_at) AS month,
        SUM(ps.total_price)::float AS revenue,
        SUM(ps.quantity)::float AS qty
    FROM product_sales ps
    JOIN sales s ON s.id = ps.sale_id
    JOIN products p ON p.id = ps.product_id
    WHERE s.sale_status_desc = 'COMPLETED'
        AND s.created_at >= :start_dt
        AND s.created_at < :end_dt
    """
    params_products = {"start_dt": start_dt, "end_dt": end_dt}
    
    if store_ids:
        sql_products += " AND s.store_id = ANY(:store_ids)"
        params_products["store_ids"] = list(store_ids) if not isinstance(store_ids, list) else store_ids
    if channel_ids:
        sql_products += " AND s.channel_id = ANY(:channel_ids)"
        params_products["channel_ids"] = list(channel_ids) if not isinstance(channel_ids, list) else channel_ids
    
    # Agrupar por mês ao invés de semana e limitar aos produtos mais vendidos
    sql_products += """
    GROUP BY p.id, p.name, DATE_TRUNC('month', s.created_at)
    HAVING SUM(ps.quantity) >= 100
    ORDER BY SUM(ps.quantity) DESC
    LIMIT 500
    """
    
    try:
        products_data = fetch_all(sql_products, params_products, timeout_ms=10000)  # Aumentar timeout
    except Exception as exc:
        raise AnomalyDetectorError(f"Erro ao buscar dados de produtos: {exc}") from exc
    df_products = pd.DataFrame(products_data)
    
    return {
        "daily": df_daily,
        "products": df_products
    }


def _prepare_anomaly_prompt(data: dict) -> str:
    """Prepara dados em formato otimizado para detecção de anomalias."""
    builder = AnomalyPromptBuilder()
    return builder.build_prompt(data)


async def detect_anomalies(
    start: str,
    end: str,
    *,
    store_ids: Optional[list[int]] = None,
    channel_ids: Optional[Sequence[int]] = None,
) -> dict:
    """
    Detecta anomalias nos dados de vendas usando IA.
    Retorna estrutura com anomalias identificadas.
    """
    # Validar datas
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnomalyDetectorError(f"Datas inválidas: {exc}") from exc
    
    # Buscar dados
    data = _fetch_anomaly_data(start_dt, end_dt, store_ids, channel_ids)
    
    if data["daily"].empty and data["products"].empty:
        return {
            "anomalies_found": 0,
            "results": {
                "queda_semanal": "NÃO DETECTADA - Sem dados",
                "pico_promocional": "NÃO DETECTADA - Sem dados",
                "crescimento_linear": "NÃO DETECTADA - Sem dados",
                "sazonalidade": "NÃO DETECTADA - Sem dados",
            },
            "raw_response": None,
            "period": {"start": start, "end": end},
        }
    
    # Preparar prompt
    prompt_data = _prepare_anomaly_prompt(data)
    
    # Executar IA
    try:
        chain = _get_anomaly_chain()
    except AnomalyDetectorError as exc:
        # Se a IA não estiver configurada, retornar resultado vazio
        return {
            "anomalies_found": 0,
            "results": {
                "queda_semanal": f"NÃO DETECTADA - IA não configurada: {exc}",
                "pico_promocional": f"NÃO DETECTADA - IA não configurada: {exc}",
                "crescimento_linear": f"NÃO DETECTADA - IA não configurada: {exc}",
                "sazonalidade": f"NÃO DETECTADA - IA não configurada: {exc}",
            },
            "raw_response": None,
            "period": {"start": start, "end": end},
        }
    
    def _runner() -> str:
        result = chain.invoke({"data": prompt_data})
        return result.content.strip() if hasattr(result, "content") else str(result)
    
    loop = asyncio.get_running_loop()
    try:
        raw_response = await loop.run_in_executor(None, _runner)
    except Exception as exc:
        raise AnomalyDetectorError(f"Falha ao consultar o Gemini: {exc}") from exc
    
    # Parsear resposta
    results = {
        "queda_semanal": "NÃO DETECTADA",
        "pico_promocional": "NÃO DETECTADA",
        "crescimento_linear": "NÃO DETECTADA",
        "sazonalidade": "NÃO DETECTADA",
    }
    anomalies_count = 0
    
    for line in raw_response.split("\n"):
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            
            if key in ["queda_semanal", "pico_promocional", "crescimento_linear", "sazonalidade"]:
                results[key] = value
                if "NÃO DETECTADA" not in value.upper():
                    anomalies_count += 1
    
    return {
        "anomalies_found": anomalies_count,
        "results": results,
        "raw_response": raw_response,
        "period": {"start": start, "end": end},
    }


__all__ = ["detect_anomalies", "AnomalyDetectorError"]
