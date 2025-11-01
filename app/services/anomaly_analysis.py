"""
Anomaly detection analysis components.
Refactored from monolithic _prepare_anomaly_prompt function.
"""

from __future__ import annotations

import pandas as pd
from typing import List


class AnomalyAnalysisSection:
    """Base class for anomaly analysis sections."""

    def __init__(self, title: str):
        self.title = title

    def analyze(self, data: dict) -> str:
        """Analyze data and return formatted section."""
        raise NotImplementedError

    def _format_section(self, content: str) -> str:
        """Format content as a section."""
        return f"## {self.title}\n{content}"


class DailyPeaksAnalysis(AnomalyAnalysisSection):
    """Analysis of daily sales peaks."""

    def __init__(self):
        super().__init__("1. ANÁLISE DE PICOS DIÁRIOS")

    def analyze(self, data: dict) -> str:
        df_daily = data["daily"]

        if df_daily.empty:
            return self._format_section("Sem dados diários disponíveis")

        daily_agg = df_daily.groupby("day").agg({"revenue": "sum", "orders": "sum"}).reset_index()
        daily_agg["day"] = pd.to_datetime(daily_agg["day"])
        daily_agg = daily_agg.sort_values("day")

        # Calculate statistics
        mean_revenue = daily_agg["revenue"].mean()
        std_revenue = daily_agg["revenue"].std()

        # Detect outliers
        daily_agg["z_score"] = (daily_agg["revenue"] - mean_revenue) / std_revenue
        daily_agg["multiple"] = daily_agg["revenue"] / mean_revenue

        # Significant peaks (2x or more)
        picos = daily_agg[daily_agg["multiple"] >= 2.0]

        lines = []
        lines.append(f"Média diária: R$ {mean_revenue:,.2f} | Desvio: R$ {std_revenue:,.2f}")

        if not picos.empty:
            lines.append(f"\n⚠️ PICOS DETECTADOS ({len(picos)} dias com 2x+ a média):")
            for _, row in picos.iterrows():
                lines.append(f"  - {row['day'].strftime('%Y-%m-%d')}: R$ {row['revenue']:,.2f} ({row['multiple']:.1f}x a média)")
        else:
            lines.append("Nenhum pico significativo (2x+) detectado")

        return self._format_section("\n".join(lines))


class WeeklyDropsAnalysis(AnomalyAnalysisSection):
    """Analysis of weekly sales drops."""

    def __init__(self):
        super().__init__("2. ANÁLISE DE QUEDAS SEMANAIS")

    def analyze(self, data: dict) -> str:
        df_daily = data["daily"]

        if df_daily.empty:
            return self._format_section("Sem dados diários disponíveis")

        weekly_agg = df_daily.copy()
        weekly_agg["week"] = pd.to_datetime(weekly_agg["day"]).dt.to_period("W").dt.to_timestamp()
        weekly_revenue = weekly_agg.groupby("week").agg({"revenue": "sum"}).reset_index()
        weekly_revenue = weekly_revenue.sort_values("week")

        # Calculate weekly change
        weekly_revenue["prev_revenue"] = weekly_revenue["revenue"].shift(1)
        weekly_revenue["change_pct"] = ((weekly_revenue["revenue"] - weekly_revenue["prev_revenue"]) / weekly_revenue["prev_revenue"] * 100)

        quedas = weekly_revenue[weekly_revenue["change_pct"] <= -20]

        lines = []
        lines.append(f"Total de semanas analisadas: {len(weekly_revenue)}")

        if not quedas.empty:
            lines.append(f"\n⚠️ QUEDAS DETECTADAS ({len(quedas)} semanas com -20% ou mais):")
            for _, row in quedas.iterrows():
                lines.append(f"  - Semana {row['week'].strftime('%Y-%m-%d')}: Queda de {row['change_pct']:.1f}% (de R$ {row['prev_revenue']:,.2f} para R$ {row['revenue']:,.2f})")
        else:
            lines.append("Nenhuma queda significativa (-20%+) detectada")

        return self._format_section("\n".join(lines))


class LinearGrowthAnalysis(AnomalyAnalysisSection):
    """Analysis of linear growth patterns by store."""

    def __init__(self):
        super().__init__("3. ANÁLISE DE CRESCIMENTO LINEAR (Lojas)")

    def analyze(self, data: dict) -> str:
        df_daily = data["daily"]

        if df_daily.empty or "store_id" not in df_daily.columns:
            return self._format_section("Sem dados diários ou store_id indisponível")

        monthly_store = df_daily.copy()
        monthly_store["month"] = pd.to_datetime(monthly_store["day"]).dt.to_period("M").dt.to_timestamp()
        monthly_revenue = monthly_store.groupby(["store_id", "month"]).agg({"revenue": "sum"}).reset_index()
        monthly_revenue = monthly_revenue.sort_values(["store_id", "month"])

        # Calculate average growth by store
        growth_by_store = []
        for store_id in monthly_revenue["store_id"].unique():
            store_data = monthly_revenue[monthly_revenue["store_id"] == store_id].sort_values("month")
            if len(store_data) >= 3:
                revenues = store_data["revenue"].values
                growths = [(revenues[i] - revenues[i-1]) / revenues[i-1] * 100 for i in range(1, len(revenues)) if revenues[i-1] > 0]
                if growths:
                    avg_growth = sum(growths) / len(growths)
                    if avg_growth >= 4.0:  # 4% or more average growth
                        growth_by_store.append({
                            "store_id": store_id,
                            "avg_growth": avg_growth,
                            "months": len(store_data)
                        })

        if growth_by_store:
            lines = []
            lines.append(f"\n⚠️ CRESCIMENTO DETECTADO ({len(growth_by_store)} lojas com +4% mensal):")
            for store in sorted(growth_by_store, key=lambda x: x["avg_growth"], reverse=True)[:5]:
                lines.append(f"  - Loja {store['store_id']}: Crescimento médio de {store['avg_growth']:.1f}%/mês ({store['months']} meses)")
            return self._format_section("\n".join(lines))
        else:
            return self._format_section("Nenhum crescimento linear significativo (+4%/mês) detectado")


class SeasonalityAnalysis(AnomalyAnalysisSection):
    """Analysis of product seasonality patterns."""

    def __init__(self):
        super().__init__("4. ANÁLISE DE SAZONALIDADE (Produtos)")

    def analyze(self, data: dict) -> str:
        df_products = data["products"]

        if df_products.empty:
            return self._format_section("Sem dados de produtos disponíveis")

        # Already grouped by product and month in query
        # Calculate variation for products with significant volume
        seasonal_products = []
        for product_id in df_products["product_id"].unique():
            prod_data = df_products[df_products["product_id"] == product_id]
            if len(prod_data) >= 3:
                product_name = prod_data.iloc[0]["product_name"]
                quantities = prod_data["qty"].values
                if min(quantities) > 0:
                    variation = (max(quantities) - min(quantities)) / min(quantities) * 100
                    if variation >= 80:
                        seasonal_products.append({
                            "product": product_name,
                            "variation": variation,
                            "min_qty": min(quantities),
                            "max_qty": max(quantities)
                        })

        if seasonal_products:
            lines = []
            lines.append(f"\n⚠️ SAZONALIDADE DETECTADA ({len(seasonal_products)} produtos com +80% variação):")
            for prod in sorted(seasonal_products, key=lambda x: x["variation"], reverse=True)[:5]:
                lines.append(f"  - {prod['product']}: Variação de {prod['variation']:.1f}% (min: {prod['min_qty']:.0f}, max: {prod['max_qty']:.0f} unidades)")
            return self._format_section("\n".join(lines))
        else:
            return self._format_section("Nenhuma sazonalidade significativa (+80%) detectada")


class AnomalyPromptBuilder:
    """Builder for anomaly detection prompts."""

    def __init__(self):
        self.sections = [
            DailyPeaksAnalysis(),
            WeeklyDropsAnalysis(),
            LinearGrowthAnalysis(),
            SeasonalityAnalysis(),
        ]

    def build_prompt(self, data: dict) -> str:
        """Build complete anomaly analysis prompt."""
        sections_content = []
        for section in self.sections:
            sections_content.append(section.analyze(data))

        return "\n\n".join(sections_content)