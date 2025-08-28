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

    carga_tributaria_percentual: str | None # De Decimal para str
    ticket_medio: str | None                 # De Decimal para str
    crescimento_faturamento_percentual: str | None # De Decimal para str também, para consistência
    total_impostos_por_tipo: Dict[str, Any] 

    class Config:
        from_attributes = True