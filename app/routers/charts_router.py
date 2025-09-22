# app/routers/charts_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import FileResponse
from datetime import date
from typing import Optional
import pandas as pd
from collections import defaultdict
from app.crud import grafico as crud_grafico
from app.crud import documento as crud_documento
from pathlib import Path 

from app.core.database import SessionLocal
from app.services import charts as charts_service
from app.crud import dados_fiscais as crud_dados_fiscais
from app.services import analytics_service 

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

# =============================================================================
# --- Endpoints - SIMPLES NACIONAL ---
# =============================================================================

@router.get("/simples-nacional/faturamento", summary="[SN] Gera gráfico de Faturamento Mensal", response_class=FileResponse)
def get_grafico_sn_faturamento(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico.")
    caminho_grafico = charts_service.gerar_grafico_sn_faturamento(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/receita-crescimento", summary="[SN] Gera gráfico de Receita vs Crescimento", response_class=FileResponse)
def get_grafico_sn_receita_crescimento(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico de receita e crescimento.")
    caminho_grafico = charts_service.gerar_grafico_sn_receita_crescimento(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/impostos-carga", summary="[SN] Gera gráfico de Impostos vs Carga Tributária", response_class=FileResponse)
def get_grafico_sn_impostos_carga(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico de impostos e carga tributária.")
    caminho_grafico = charts_service.gerar_grafico_sn_impostos_carga(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/acumulado-anual", summary="[SN] Gera gráfico de Faturamento e Impostos Acumulados", response_class=FileResponse)
def get_grafico_sn_acumulado(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico de valores acumulados.")
    caminho_grafico = charts_service.gerar_grafico_sn_acumulado(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/limite-faturamento", summary="[SN] Gera gráfico de medidor para o Limite de Faturamento", response_class=FileResponse)
def get_grafico_sn_limite_faturamento(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    dados_kpis = analytics_service.preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("medidor"):
        raise HTTPException(status_code=404, detail="Dados de PGDAS não encontrados para o gráfico de limite de faturamento.")
    caminho_grafico = charts_service.gerar_grafico_sn_limite_faturamento(dados_kpis["medidor"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/sublimite-receita", summary="[SN] Gera gráfico de medidor para o Sublimite de Receita", response_class=FileResponse)
def get_grafico_sn_sublimite_receita(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    dados_kpis = analytics_service.preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("medidor") or not dados_kpis["medidor"].get("sublimite"):
        raise HTTPException(status_code=404, detail="Dados de PGDAS com sublimite válido não encontrados.")
    caminho_grafico = charts_service.gerar_grafico_sn_sublimite_receita(dados_kpis["medidor"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/simples-nacional/segregacao-tributos", summary="[SN] Gera gráfico de rosca para a Segregação dos Tributos", response_class=FileResponse)
def get_grafico_sn_segregacao_tributos(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    dados_kpis = analytics_service.preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("rosca"):
        raise HTTPException(status_code=404, detail="Dados de PGDAS sem valores de tributos para o gráfico de segregação.")
    caminho_grafico = charts_service.gerar_grafico_sn_segregacao_tributos(dados_kpis["rosca"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

# =============================================================================
# --- Endpoints - LUCRO PRESUMIDO SERVIÇOS ---
# =============================================================================

@router.get("/lucro-presumido/receita-crescimento", summary="[LP] Gera gráfico de Faturamento e Taxa de Crescimento", response_class=FileResponse)
def get_grafico_lp_receita_crescimento(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico.")
    caminho_grafico = charts_service.gerar_grafico_lp_receita_crescimento(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/lucro-presumido/impostos-carga", summary="[LP] Gera gráfico de Total de Tributos e Carga Tributária", response_class=FileResponse)
def get_grafico_lp_impostos_carga(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico de impostos e carga.")
    caminho_grafico = charts_service.gerar_grafico_lp_impostos_carga(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/lucro-presumido/acumulado", summary="[LP] Gera gráfico de Faturamento e Tributos Acumulados", response_class=FileResponse)
def get_grafico_lp_acumulado(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico de acumulados.")
    caminho_grafico = charts_service.gerar_grafico_lp_acumulado(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/lucro-presumido/tributos-detalhado", summary="[LP] Gera gráfico de Tributos Retidos vs Devidos", response_class=FileResponse)
def get_grafico_lp_tributos_detalhado(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    df_dados = analytics_service.preparar_dados_tributos_lp(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para o gráfico detalhado de tributos.")
    caminho_grafico = charts_service.gerar_grafico_lp_tributos_detalhado(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")
    
@router.get("/lucro-presumido/tributos-ano", summary="[LP] Gera gráfico de rosca com o percentual de tributos no ano", response_class=FileResponse)
def get_grafico_lp_tributos_ano(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    dados_kpis = analytics_service.preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("rosca"):
        raise HTTPException(status_code=404, detail="Dados de tributos não encontrados para o período.")
    caminho_grafico = charts_service.gerar_grafico_lp_tributos_ano(dados_kpis["rosca"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/lucro-presumido/limite-faturamento", summary="[LP] Gera gráfico de velocímetro do limite de faturamento", response_class=FileResponse)
def get_grafico_lp_limite_faturamento(
    cnpj: str = Query(..., description="CNPJ da empresa."),
    data_inicio: date = Query(..., description="Data de início do período."),
    data_fim: date = Query(..., description="Data de fim do período."),
    db: Session = Depends(get_db)
):
    faturamento_exercicio = analytics_service.calcular_faturamento_no_exercicio(db, cnpj=cnpj, regime="Lucro Presumido (Serviços)", data_inicio=data_inicio, data_fim=data_fim)
    dados_medidor = {'faturamento_exercicio': float(faturamento_exercicio)}
    
    caminho_grafico = charts_service.gerar_grafico_lp_limite_faturamento(dados_medidor, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

# =============================================================================
# --- GERAL ---
# =============================================================================

@router.get(
    "/{documento_id}",
    summary="Lista os gráficos associados a um documento"
)
def listar_graficos_por_documento(documento_id: int, db: Session = Depends(get_db)):
    """
    Retorna os metadados de todos os gráficos que foram gerados
    a partir de um documento específico.
    """
    graficos = crud_grafico.get_graficos_por_documento_id(db, documento_id=documento_id)
    if not graficos:
        raise HTTPException(
            status_code=404,
            detail="Nenhum gráfico encontrado para o documento especificado."
        )
    return graficos