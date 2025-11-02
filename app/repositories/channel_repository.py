"""
Repositório de canais.
Centraliza todo acesso a dados relacionados a canais de venda.
"""

from typing import Optional, Sequence

from app.infra.db import fetch_all, fetch_one


class ChannelRepository:
    """
    Repositório para acesso a dados de canais de venda.
    Encapsula toda lógica SQL relacionada a canais.
    """
    
    @staticmethod
    def get_all(store_ids: Optional[Sequence[int]] = None) -> list[dict]:
        """
        Obtém lista de todos os canais de venda.
        Retorna todos os canais independente do filtro de lojas para melhor performance.
        
        Returns:
            Lista de canais com id e nome
        """
        # Simplificado: retorna todos os canais sem JOIN com sales (muito mais rápido)
        query = "SELECT id, name FROM channels ORDER BY name"
        return fetch_all(query, None, timeout_ms=2000)
    
    @staticmethod
    def get_by_name(name: str) -> dict | None:
        """
        Busca canal por nome.
        
        Args:
            name: Nome do canal
            
        Returns:
            Dados do canal ou None se não encontrado
        """
        query = "SELECT id, name FROM channels WHERE LOWER(name) = LOWER(:name)"
        return fetch_one(query, {"name": name}, timeout_ms=2000)
