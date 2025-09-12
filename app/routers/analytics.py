from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date 
# Importa o módulo da  aplicação
from app.core.database import SessionLocal # Assume que get_db está aqui
from app.services import analytics_service # Importa o serviço de analytics
from app.schemas import analytics_schema as schemas_analytics # Importa os schemas de analytics
from app.services.analytics_service import _formatar_monetario, _formatar_percentual
from app.schemas.tipos import RegimeTributario 

# Cria o roteador
router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)
def get_db():
    """
    Função de dependência para obter uma sessão da base de dados.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@router.get(
    "/kpis", 
    response_model=schemas_analytics.KpiResponse,
    summary="Calcula um conjunto de KPIs para um CNPJ e período."
)
def obter_kpis_por_periodo(
    cnpj: str,
    regime: RegimeTributario, 
    data_inicio: date,
    data_fim: date,
    db: Session = Depends(get_db)
):
    """
    Calcula e retorna os principais indicadores de performance (KPIs)
    com base nos documentos fiscais processados para um CNPJ num
    determinado intervalo de datas.
    """
    # Chama cada uma das nossas funções de serviço para calcular os KPIs
   # carga_tributaria = analytics_service.calcular_carga_tributaria(
   #     db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim
   # )
    carga_tributaria_projetada = analytics_service.projetar_carga_tributaria(
       db, cnpj=cnpj, regime=regime.value, data_inicio=data_inicio, data_fim=data_fim
    )
    
    # 2. As outras chamadas continuam como estavam
    ticket_medio = analytics_service.calcular_ticket_medio(
        db, cnpj=cnpj, regime=regime.value, data_inicio=data_inicio, data_fim=data_fim
    )
    impostos_agregados = analytics_service.calcular_impostos_por_tipo(
        db, cnpj=cnpj, regime=regime.value, data_inicio=data_inicio, data_fim=data_fim
    )
    crescimento = analytics_service.calcular_crescimento_faturamento(
        db, cnpj=cnpj, regime=regime.value, data_inicio_atual=data_inicio, data_fim_atual=data_fim
    )

    # 3. Montar a resposta com o novo formato para a carga tributária
    resposta = schemas_analytics.KpiResponse(
        cnpj_consultado=cnpj,
        regime_consultado=regime.value,
        periodo_inicio=data_inicio,
        periodo_fim=data_fim,
        carga_tributaria_percentual=carga_tributaria_projetada, # Agora é um dicionário
        ticket_medio=_formatar_monetario(ticket_medio),
        crescimento_faturamento_percentual=_formatar_percentual(crescimento),
        total_impostos_por_tipo=impostos_agregados,
    )
    
    return resposta