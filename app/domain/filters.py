"""
Filtros de dados reutilizáveis.
Centraliza a lógica de filtragem para evitar duplicação.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence


@dataclass
class DataFilters:
    """
    Filtros comuns aplicáveis a várias consultas.
    Centraliza a lógica de filtragem para consistência.
    """
    
    start_date: datetime
    end_date: datetime
    store_ids: Optional[Sequence[int]] = None
    channel_ids: Optional[Sequence[int]] = None
    sale_status: str = "COMPLETED"
    
    def to_sql_conditions(self) -> tuple[list[str], dict]:
        """
        Converte os filtros em condições SQL e parâmetros.
        
        Returns:
            Tupla contendo lista de condições WHERE e dicionário de parâmetros
        """
        conditions = [
            "s.sale_status_desc = :sale_status",
            "s.created_at >= :start_date",
            "s.created_at < :end_date",
        ]
        
        params = {
            "sale_status": self.sale_status,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }
        
        if self.store_ids:
            conditions.append("s.store_id = ANY(:store_ids)")
            params["store_ids"] = list(self.store_ids)
        
        if self.channel_ids:
            conditions.append("s.channel_id = ANY(:channel_ids)")
            params["channel_ids"] = list(self.channel_ids)
        
        return conditions, params
    
    def apply_to_query(self, base_query: str, alias: str = "s") -> tuple[str, dict]:
        """
        Aplica os filtros a uma query base.
        
        Args:
            base_query: Query SQL base (sem WHERE)
            alias: Alias da tabela sales na query
            
        Returns:
            Tupla contendo query completa e parâmetros
        """
        conditions, params = self.to_sql_conditions()
        
        # Substitui o alias se necessário
        if alias != "s":
            conditions = [cond.replace("s.", f"{alias}.") for cond in conditions]
        
        where_clause = " AND ".join(conditions)
        query = f"{base_query} WHERE {where_clause}"
        
        return query, params
