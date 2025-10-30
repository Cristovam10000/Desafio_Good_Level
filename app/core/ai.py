from __future__ import annotations

import asyncio
from functools import lru_cache

from app.core.config import settings


class AIIntegrationError(RuntimeError):
    """Erro relacionado à configuração ou execução da camada de IA."""


def _load_dependencies() -> tuple:
    try:
        from langchain.prompts import PromptTemplate  # type: ignore
        from langchain.chains import LLMChain  # type: ignore
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    except ImportError as exc:  # pragma: no cover - feedback direto
        raise AIIntegrationError(
            "Dependências de IA não encontradas. Instale-as com "
            "`pip install langchain langchain-google-genai google-generativeai`."
        ) from exc
    return PromptTemplate, LLMChain, ChatGoogleGenerativeAI


@lru_cache(maxsize=1)
def _get_chain() -> "LLMChain":
    if not settings.GOOGLE_API_KEY:
        raise AIIntegrationError(
            "GOOGLE_API_KEY não configurada. Defina a chave do Gemini para habilitar os insights."
        )

    PromptTemplate, LLMChain, ChatGoogleGenerativeAI = _load_dependencies()

    prompt = PromptTemplate(
        input_variables=["data"],
        template=(
            "Você é um analista de dados para uma rede de restaurantes.\n"
            "Receberá dados tabulares sobre vendas, produtos e entregas no formato Markdown.\n"
            "{data}\n\n"
            "Gere exatamente três insights acionáveis (tendências, oportunidades ou anomalias) "
            "e uma recomendação de negócio. Seja objetivo e cite números relevantes."
        ),
    )

    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.GEMINI_TEMPERATURE,
        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
    )

    return LLMChain(llm=llm, prompt=prompt)


async def generate_insights_text(data: str) -> str:
    """
    Executa a cadeia LangChain de forma assíncrona retornando o texto bruto.
    """
    if not data.strip():
        raise AIIntegrationError("Não há dados suficientes para gerar insights.")

    chain = _get_chain()

    def _runner() -> str:
        return chain.run(data=data).strip()

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _runner)
    except Exception as exc:  # pragma: no cover - feedback direto
        raise AIIntegrationError(f"Falha ao consultar o Gemini: {exc}") from exc


__all__ = ["AIIntegrationError", "generate_insights_text"]
