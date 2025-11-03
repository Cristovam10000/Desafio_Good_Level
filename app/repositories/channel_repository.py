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
        Ordenados por canal (alfabético) e depois por loja (alfabético).
        Isso agrupa os mesmos canais juntos, facilitando a navegação.
        
        Returns:
            Lista de canais com id, nome, tipo e loja associada.
        """
        base_query = """
            SELECT DISTINCT
                c.id AS channel_id,
                c.name AS channel_name,
                c.type AS channel_type,
                s.id AS store_id,
                s.name AS store_name,
                (c.id::text || ':' || s.id::text) AS channel_store_key
            FROM sales sa
            JOIN channels c ON c.id = sa.channel_id
            JOIN stores s ON s.id = sa.store_id
        """
        params: dict | None = None
        if store_ids:
            base_query += " WHERE sa.store_id = ANY(:store_ids)"
            params = {"store_ids": list(store_ids)}
        # Ordenar por canal primeiro (agrupa canais iguais), depois por loja
        base_query += " ORDER BY c.name, s.name"
        return fetch_all(base_query, params, timeout_ms=2000)
    
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
