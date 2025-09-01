from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import FileResponse
from datetime import date
from app.schemas.tipos import RegimeTributario
from typing import List
import os

from app.core.database import SessionLocal
from app.services import charts as charts_service
from app.crud import dados_fiscais as crud_dados_fiscais

router = APIRouter(
    prefix="/charts",
    tags=["Charts"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/faturamento",
    summary="Gera e retorna um gráfico de faturamento para um CNPJ num período",
    response_class=FileResponse
)
def obter_kpis_por_periodo(
    # Parâmetros de consulta que o utilizador irá fornecer
    cnpj: str,
    # ALTERADO: 'regime' agora usa o Enum, o que cria o menu suspenso
    regime: RegimeTributario, 
    data_inicio: date,
    data_fim: date,
    db: Session = Depends(get_db)
):
    """
    Busca os dados de faturamento para o CNPJ e período especificados,
    gera um gráfico de barras e retorna a imagem PNG.
    """
    # Busca os dados de faturamento (de documentos PGDAS, por exemplo)
    dados_db = crud_dados_fiscais.obter_dados_por_periodo(
        db, cnpj=cnpj, data_inicio=data_inicio, data_fim=data_fim
    )

    if not dados_db:
        raise HTTPException(status_code=404, detail="Nenhum dado de faturamento encontrado para o CNPJ e período fornecidos.")

    # Formata os dados para o serviço de gráficos
    dados_faturamento = [
        {"data_competencia": registro.data_competencia, "valor_total": registro.valor_total}
        for registro in dados_db if registro.valor_total is not None and registro.data_competencia is not None
    ]
    
    if not dados_faturamento:
        raise HTTPException(status_code=404, detail="Dados de faturamento encontrados, mas sem valores totais ou datas válidas.")

    try:
        # Chama o serviço para gerar o gráfico
        caminho_grafico = charts_service.gerar_grafico_faturamento(
            dados_faturamento=dados_faturamento,
            cnpj=cnpj
        )
        # Retorna o arquivo de imagem diretamente
        return FileResponse(caminho_grafico, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar o gráfico: {e}")