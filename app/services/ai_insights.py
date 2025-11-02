"""
AI-powered insights and anomaly detection service using Google Gemini API.
"""
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal

GEMINI_API_KEY = "AIzaSyBztS5Cgz_b9T1BvCfhLwM3OXJECn6soRk"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"


def serialize_data(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


async def generate_insights(
    section: str,
    data: Dict[str, Any],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate insights for a specific dashboard section using AI.
    
    Args:
        section: Section name (entregas, vendas, operacoes, produtos, lojas)
        data: Aggregated data for the section
        context: Additional context or specific questions
    
    Returns:
        Dictionary with insights, improvements, and attention points
    """
    
    prompts = {
        "entregas": f"""
Você é um especialista em logística e operações de delivery. Analise os seguintes dados de entregas:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: tempo de entrega, P90, cidades problemáticas, oportunidades de otimização de rotas.
""",
        
        "vendas": f"""
Você é um especialista em análise de vendas e comportamento do consumidor. Analise os seguintes dados de vendas:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: tendências de vendas, dias da semana mais lucrativos, estratégias de desconto, padrões sazonais.
""",
        
        "operacoes": f"""
Você é um especialista em operações e eficiência operacional. Analise os seguintes dados operacionais:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: tempo de preparo, cancelamentos, eficiência por loja, gargalos operacionais.
""",
        
        "produtos": f"""
Você é um especialista em gestão de produtos e análise de portfólio. Analise os seguintes dados de produtos:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: produtos mais vendidos, customizações populares, combinações de produtos, oportunidades de cross-sell.
""",
        
        "lojas": f"""
Você é um especialista em gestão de múltiplas unidades e performance de lojas. Analise os seguintes dados de lojas:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: performance relativa, lojas com baixo desempenho, oportunidades de replicação de boas práticas, taxas de cancelamento.
""",
        
        "financeiro": f"""
Você é um especialista em análise financeira e fluxo de caixa. Analise os seguintes dados financeiros:

{json.dumps(data, indent=2, ensure_ascii=False, default=serialize_data)}

Forneça insights acionáveis no formato JSON:
{{
  "summary": "Resumo executivo em 2-3 frases",
  "improvements": [
    {{"title": "Título da melhoria", "description": "Descrição detalhada", "priority": "high/medium/low", "impact": "Impacto esperado"}}
  ],
  "attention_points": [
    {{"title": "Ponto de atenção", "description": "Descrição do problema", "severity": "critical/warning/info"}}
  ],
  "recommendations": [
    "Recomendação específica 1",
    "Recomendação específica 2"
  ]
}}

Foque em: mix de pagamentos, receita líquida vs bruta, taxas e comissões, oportunidades de otimização financeira.
"""
    }
    
    prompt = prompts.get(section, "")
    if context:
        prompt += f"\n\nContexto adicional: {context}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:  # Aumentado para 60s
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,  # Mais focado
                        "topK": 20,
                        "topP": 0.8,
                        "maxOutputTokens": 2048
                    }
                }
            )
            
            if response.status_code != 200:
                return {
                    "error": f"API Error: {response.status_code}",
                    "summary": "Erro ao gerar insights",
                    "improvements": [],
                    "attention_points": [],
                    "recommendations": []
                }
            
            result = response.json()
            
            # Extract text from Gemini response
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Try to parse as JSON
                # Remove markdown code blocks if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                try:
                    insights = json.loads(content)
                    return insights
                except json.JSONDecodeError:
                    # If not valid JSON, return structured error
                    return {
                        "summary": content[:200] + "..." if len(content) > 200 else content,
                        "improvements": [],
                        "attention_points": [],
                        "recommendations": [],
                        "raw_response": content
                    }
            
            return {
                "error": "No valid response from AI",
                "summary": "Erro ao processar resposta",
                "improvements": [],
                "attention_points": [],
                "recommendations": []
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "summary": f"Erro ao gerar insights: {str(e)}",
            "improvements": [],
            "attention_points": [],
            "recommendations": []
        }


async def detect_anomalies(
    all_data: Dict[str, Any],
    date_range: Dict[str, str]
) -> Dict[str, Any]:
    """
    Detect anomalies across all business data using AI.
    
    The dataset intentionally includes:
    - Problematic week: 30% sales drop (simulates operational issue)
    - Promotional day: 3x spike (Black Friday, promotion)
    - Growing store: Specific store with 5%/month linear growth
    - Seasonal product: Some products sell 80% more in certain months
    
    Args:
        all_data: Combined data from all sections
        date_range: Start and end dates for analysis
    
    Returns:
        Dictionary with detected anomalies and patterns
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[detect_anomalies] Iniciando detecção de anomalias - período: {date_range}")
    
    prompt = f"""
Você é um especialista em detecção de anomalias e análise de padrões em dados de negócios.

IMPORTANTE: Este dataset foi propositalmente injetado com as seguintes anomalias para teste:
1. **Semana problemática**: Queda de 30% em vendas (simula problema operacional)
2. **Dia promocional**: Pico de 3x nas vendas (Black Friday ou promoção)
3. **Loja crescendo**: Uma loja específica com crescimento linear de 5%/mês
4. **Produto sazonal**: Alguns produtos vendem 80% mais em determinados meses

Analise os dados abaixo e identifique ESSAS anomalias conhecidas, além de OUTRAS anomalias ou padrões que você detectar:

Período: {date_range.get('start', 'N/A')} até {date_range.get('end', 'N/A')}

{json.dumps(all_data, indent=2, ensure_ascii=False, default=serialize_data)}

Retorne um JSON no seguinte formato:
{{
  "summary": "Resumo executivo das principais anomalias encontradas",
  "known_anomalies": [
    {{
      "type": "sales_drop|promotional_spike|store_growth|seasonal_product",
      "title": "Título da anomalia",
      "description": "Descrição detalhada",
      "detected": true|false,
      "confidence": 0.0-1.0,
      "data_points": ["Evidências específicas encontradas"],
      "impact": "high|medium|low",
      "recommendation": "O que fazer sobre isso"
    }}
  ],
  "other_anomalies": [
    {{
      "type": "Tipo da anomalia",
      "title": "Título",
      "description": "Descrição",
      "confidence": 0.0-1.0,
      "severity": "critical|warning|info",
      "affected_areas": ["vendas", "entregas", etc],
      "recommendation": "Recomendação"
    }}
  ],
  "patterns": [
    {{
      "type": "Tipo do padrão",
      "description": "Descrição do padrão identificado",
      "frequency": "daily|weekly|monthly|seasonal",
      "strength": "strong|moderate|weak"
    }}
  ],
  "insights": [
    "Insight importante 1",
    "Insight importante 2"
  ]
}}

Seja específico com datas, valores e percentuais. Use os dados reais para fundamentar suas conclusões.
"""
    
    logger.info(f"[detect_anomalies] Tamanho do prompt: {len(prompt)} caracteres")
    
    try:
        logger.info("[detect_anomalies] Chamando API Gemini...")
        async with httpx.AsyncClient(timeout=90.0) as client:  # Mais tempo para anomalias
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.4,
                        "topK": 20,
                        "topP": 0.8,
                        "maxOutputTokens": 4096
                    }
                }
            )
            
            logger.info(f"[detect_anomalies] Resposta da API: status={response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"[detect_anomalies] Erro na API: {response.status_code} - {response.text}")
                return {
                    "error": f"API Error: {response.status_code}",
                    "summary": "Erro ao detectar anomalias",
                    "known_anomalies": [],
                    "other_anomalies": [],
                    "patterns": [],
                    "insights": []
                }
            
            result = response.json()
            
            logger.info(f"[detect_anomalies] Resultado parseado - tem candidates: {'candidates' in result}")
            
            if "candidates" in result and len(result["candidates"]) > 0:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                
                logger.info(f"[detect_anomalies] Conteúdo recebido - tamanho: {len(content)} caracteres")
                
                # Clean markdown
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                try:
                    anomalies = json.loads(content)
                    logger.info(f"[detect_anomalies] JSON parseado com sucesso - anomalias conhecidas: {len(anomalies.get('known_anomalies', []))}")
                    return anomalies
                except json.JSONDecodeError as e:
                    logger.error(f"[detect_anomalies] Erro ao parsear JSON: {e}")
                    logger.error(f"[detect_anomalies] Conteúdo que falhou: {content[:500]}")
                    return {
                        "summary": content[:300] + "..." if len(content) > 300 else content,
                        "known_anomalies": [],
                        "other_anomalies": [],
                        "patterns": [],
                        "insights": [],
                        "raw_response": content
                    }
            
            logger.warning("[detect_anomalies] Nenhum candidate válido na resposta")
            return {
                "error": "No valid response from AI",
                "summary": "Erro ao processar resposta",
                "known_anomalies": [],
                "other_anomalies": [],
                "patterns": [],
                "insights": []
            }
            
    except Exception as e:
        logger.error(f"[detect_anomalies] Exceção: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Erro ao detectar anomalias: {str(e)}",
            "known_anomalies": [],
            "other_anomalies": [],
            "patterns": [],
            "insights": []
        }
