from __future__ import annotations

import asyncio
from functools import lru_cache

from app.core.config import settings


class AIIntegrationError(RuntimeError):
    """Erro relacionado à configuração ou execução da camada de IA."""


def _load_dependencies() -> tuple:
    try:
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    except ImportError as exc:  # pragma: no cover - feedback direto
        raise AIIntegrationError(
            "Dependências de IA não encontradas. Instale-as com "
            "`pip install langchain langchain-google-genai google-generativeai`."
        ) from exc
    return ChatPromptTemplate, ChatGoogleGenerativeAI


@lru_cache(maxsize=1)
def _get_chain():
    if not settings.GOOGLE_API_KEY:
        raise AIIntegrationError(
            "GOOGLE_API_KEY não configurada. Defina a chave do Gemini para habilitar os insights."
        )

    ChatPromptTemplate, ChatGoogleGenerativeAI = _load_dependencies()

    prompt = ChatPromptTemplate.from_template(
        "Você é um analista de dados para restaurantes.\n"
        "Analise os dados abaixo e gere EXATAMENTE 3 insights curtos (máximo 2 frases cada).\n"
        "Formato: numeração simples (1., 2., 3.) seguida do insight.\n"
        "Seja direto, objetivo e cite números relevantes.\n\n"
        "Dados:\n{data}\n\n"
        "Responda APENAS com os 3 insights numerados, SEM introduções ou conclusões."
    )

    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.GEMINI_TEMPERATURE,
        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
    )

    return prompt | llm


async def generate_insights_text(data: str) -> str:
    """
    Executa a cadeia LangChain de forma assíncrona retornando o texto bruto.
    """
    if not data.strip():
        raise AIIntegrationError("Não há dados suficientes para gerar insights.")

    chain = _get_chain()

    def _runner() -> str:
        result = chain.invoke({"data": data})
        return result.content.strip() if hasattr(result, 'content') else ""

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _runner)
    except Exception as exc:  # pragma: no cover - feedback direto
        raise AIIntegrationError(f"Falha ao consultar o Gemini: {exc}") from exc


__all__ = ["AIIntegrationError", "generate_insights_text"]
