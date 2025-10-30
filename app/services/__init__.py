"""
Serviços de domínio separados das rotas.

Atualmente expõe utilidades para geração de insights (LangChain + Gemini).
"""

from .insights import (  # noqa: F401
    build_dataset,
    generate_dataset_insights,
    InsightsDataset,
)

__all__ = ["build_dataset", "generate_dataset_insights", "InsightsDataset"]
