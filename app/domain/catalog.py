from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


# -----------------------------------------------------------------------------
# 1) Allow-list: medidas, dimensões e granularidade
# -----------------------------------------------------------------------------

MEASURES: Dict[str, str] = {
    "revenue": "Sales.revenue",
    "orders": "Sales.orders",
    "avg_ticket": "Sales.avgTicket",
    
}


DIMENSIONS: Dict[str, str] = {
    "store": "Sales.store",        
    "channel": "Sales.channel",    
    "product": "ProductSales.product",  
    "city": "Delivery.city",      
    "bucket": "Sales.createdAt",   
}

# Granularidades permitidas
GRAINS = {"hour", "day", "week", "month"}

# Time dimension "padrão" para vendas
TIME_DIMENSION = "Sales.createdAt"


# -----------------------------------------------------------------------------
# 2) Modelos de entrada (vindos do frontend) com validação
# -----------------------------------------------------------------------------

class FilterSpec(BaseModel):
    dimension: str
    operator: Literal["equals", "notEquals", "contains"] = "equals"
    values: List[str] = Field(default_factory=list)

    @field_validator("dimension")
    @classmethod
    def _dimension_must_be_allowed(cls, v: str) -> str:
        if v not in DIMENSIONS:
            raise ValueError(f"Dimensão não permitida: {v}")
        if v == "bucket":
            # bucket não é filtro; ele controla apenas granularidade de tempo
            raise ValueError("Não é possível filtrar por 'bucket'")
        return v

    @field_validator("values")
    @classmethod
    def _values_non_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Filtro precisa ter pelo menos 1 valor")
        # limpeza simples
        return [s.strip() for s in v if s and s.strip()]


class QueryIn(BaseModel):
    measure: str
    dimensions: List[str] = Field(default_factory=list)
    grain: Literal["hour", "day", "week", "month"] = "day"
    date_from: str = Field(..., alias="from")
    date_to: str = Field(..., alias="to")
    filters: List[FilterSpec] = Field(default_factory=list)

    @field_validator("measure")
    @classmethod
    def _measure_must_be_allowed(cls, v: str) -> str:
        if v not in MEASURES:
            raise ValueError(f"Métrica não permitida: {v}")
        return v

    @field_validator("dimensions")
    @classmethod
    def _dimensions_must_be_allowed(cls, dims: List[str]) -> List[str]:
        if not dims:
            return dims
        for d in dims:
            if d not in DIMENSIONS:
                raise ValueError(f"Dimensão não permitida: {d}")
        # opcional: evitar duplicadas e limitar quantidade (legibilidade/perf)
        dedup = []
        for d in dims:
            if d not in dedup:
                dedup.append(d)
        if len(dedup) > 3:
            raise ValueError("No máximo 3 dimensões por consulta")
        return dedup

    @field_validator("date_from", "date_to")
    @classmethod
    def _validate_dates(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("Datas devem estar em formato ISO (ex.: 2024-01-01)")
        return v


# -----------------------------------------------------------------------------
# 3) Montadores/validadores de query para o Cube
# -----------------------------------------------------------------------------

def _to_cube_dimensions(dims: List[str]) -> List[str]:
    res: List[str] = []
    for d in dims:
        if d == "bucket":
            continue
        res.append(DIMENSIONS[d])
    return res


def _time_dimension(grain: str) -> dict:

    return {
        "dimension": TIME_DIMENSION,
        "granularity": grain,
    }


def build_cube_query(
    q: QueryIn,
    *,
    user_store_ids: Optional[List[int]] = None,
    limit: int = 5000,
) -> dict:
    if q.grain not in GRAINS:
        raise ValueError(f"Granularidade inválida: {q.grain}")

    measures = [MEASURES[q.measure]]
    dimensions = _to_cube_dimensions(q.dimensions)

    # timeDimension obrigatório: sempre usamos Sales.createdAt
    time_dim = _time_dimension(q.grain)
    time_dim["dateRange"] = [q.date_from, q.date_to]

    filters: List[dict] = []
    # Filtros vindos do cliente
    for f in q.filters:
        filters.append({
            "dimension": DIMENSIONS[f.dimension],
            "operator": f.operator,
            "values": f.values,
        })

    # Filtro por lojas (multi-tenant): SEMPRE injete se vier do token
    if user_store_ids:
        filters.append({
            "dimension": DIMENSIONS["store"],
            "operator": "equals",
            "values": [str(x) for x in user_store_ids],
        })


    cube_query = {
        "measures": measures,
        "dimensions": dimensions,
        "timeDimensions": [time_dim],
        "filters": filters,
        "limit": limit,
    }
    return cube_query


# -----------------------------------------------------------------------------
# 4) Catálogo para documentação/Swagger (opcional)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogDoc:
    measures: Dict[str, str]
    dimensions: Dict[str, str]
    grains: List[str]
    default_time_dimension: str


def catalog_doc() -> CatalogDoc:
    return CatalogDoc(
        measures=MEASURES,
        dimensions=DIMENSIONS,
        grains=sorted(GRAINS),
        default_time_dimension=TIME_DIMENSION,
    )
