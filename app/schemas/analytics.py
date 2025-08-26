from pydantic import BaseModel
from typing import Dict, Any
from datetime import date
from decimal import Decimal

class KpiResponse(BaseModel):
    """Schema para a resposta consolidada dos KPIs."""
    
    # Adicionamos os parâmetros de entrada para referência na resposta
    cnpj_consultado: str
    regime_consultado: str 
    periodo_inicio: date
    periodo_fim: date

    # Resultados dos KPIs
    carga_tributaria_percentual: Decimal | None
    ticket_medio: Decimal | None
    crescimento_faturamento_percentual: Decimal | None
    total_impostos_por_tipo: Dict[str, str]

    class Config:
        from_attributes = True