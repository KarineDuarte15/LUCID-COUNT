# app/routers/charts_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.responses import FileResponse
from datetime import date
from typing import Optional
import pandas as pd
from collections import defaultdict # Importação necessária

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

# --- HELPER PARA GRÁFICOS DE SÉRIE TEMPORAL ---
def preparar_dados_para_graficos(db: Session, cnpj: str, data_inicio: date, data_fim: date) -> Optional[pd.DataFrame]:
    """
    Busca dados da base de dados e calcula todos os KPIs necessários para os gráficos,
    retornando um DataFrame do Pandas pronto para ser visualizado.
    """
    dados_db = crud_dados_fiscais.obter_dados_por_periodo(db, cnpj=cnpj, data_inicio=data_inicio, data_fim=data_fim)

    if not dados_db:
        return None

    documentos_por_mes = defaultdict(list)
    for doc in dados_db:
        if doc.data_competencia:
            documentos_por_mes[doc.data_competencia.strftime('%Y-%m')].append(doc)

    dados_list = []
    for mes_str, docs_do_mes in documentos_por_mes.items():
        pgdas_doc = next((d for d in docs_do_mes if d.documento.tipo_documento == 'PGDAS'), None)
        
        faturamento_mes = 0
        impostos_mes = 0
        data_competencia_mes = None

        if pgdas_doc:
            faturamento_mes = pgdas_doc.valor_total
            impostos_mes = (pgdas_doc.impostos or {}).get('total_debitos_tributos', 0)
            data_competencia_mes = pgdas_doc.data_competencia
        elif docs_do_mes:
            doc_fallback = docs_do_mes[0]
            faturamento_mes = doc_fallback.valor_total
            impostos_mes = (doc_fallback.impostos or {}).get('total_debitos_tributos', 0)
            data_competencia_mes = doc_fallback.data_competencia

        if data_competencia_mes:
            dados_list.append({
                "data_competencia": data_competencia_mes,
                "faturamento": faturamento_mes,
                "total_impostos": impostos_mes
            })

    if not dados_list:
        return None
        
    df = pd.DataFrame(dados_list)
    
    df['data_competencia'] = pd.to_datetime(df['data_competencia'], errors='coerce')
    df['faturamento'] = pd.to_numeric(df['faturamento'], errors='coerce')
    df['total_impostos'] = pd.to_numeric(df['total_impostos'], errors='coerce')
    df.dropna(subset=['data_competencia', 'faturamento'], inplace=True)
    
    if df.empty:
        return None
        
    df = df.sort_values('data_competencia').reset_index(drop=True)

    df['taxa_crescimento'] = df['faturamento'].pct_change().mul(100)
    df['carga_tributaria'] = (df['total_impostos'] / df['faturamento'].replace(0, pd.NA)).mul(100)
    df['faturamento_acumulado'] = df.groupby(df['data_competencia'].dt.year)['faturamento'].cumsum()
    df['impostos_acumulados'] = df.groupby(df['data_competencia'].dt.year)['total_impostos'].cumsum()

    df['ano'] = df['data_competencia'].dt.year
    df['mes'] = df['data_competencia'].dt.strftime('%B').str.capitalize()
    df['mes_ano'] = df['data_competencia'].dt.strftime('%b/%Y')
    
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    def formatar_percentual(valor):
        return f"{valor:.2f}%" if pd.notna(valor) else "0.00%"

    df['faturamento_formatado'] = df['faturamento'].apply(formatar_moeda)
    df['crescimento_formatado'] = df['taxa_crescimento'].apply(formatar_percentual)
    df['impostos_formatado'] = df['total_impostos'].apply(formatar_moeda)
    df['carga_formatado'] = df['carga_tributaria'].apply(formatar_percentual)
    df['faturamento_acumulado_formatado'] = df['faturamento_acumulado'].apply(formatar_moeda)
    df['impostos_acumulados_formatado'] = df['impostos_acumulados'].apply(formatar_moeda)

    df.fillna(0, inplace=True)
    
    return df

# --- NOVO HELPER PARA GRÁFICOS DE KPI (MEDIDOR E ROSCA) ---
def preparar_dados_para_kpis_visuais(db: Session, cnpj: str, data_inicio: date, data_fim: date) -> Optional[dict]:
    """
    Busca o documento PGDAS mais recente no período e extrai os dados
    necessários para os gráficos de medidor e rosca.
    """
    dados_db = crud_dados_fiscais.obter_dados_por_periodo(
        db, cnpj=cnpj, data_inicio=data_inicio, data_fim=data_fim, tipos_documento=['PGDAS']
    )

    if not dados_db:
        return None

    # Pega o documento mais recente (maior data de competência)
    pgdas_recente = max(dados_db, key=lambda doc: doc.data_competencia)
    
    if not pgdas_recente or not pgdas_recente.impostos:
        return None

    impostos_pgdas = pgdas_recente.impostos
    
    # Extrai dados para os gráficos de medidor, convertendo para float para o Plotly
    dados_medidor = {
        'rba': float(impostos_pgdas.get('receita_bruta_acumulada_rba', 0)),
        'limite': float(impostos_pgdas.get('limite_faturamento', 0)),
        'sublimite': float(impostos_pgdas.get('sublimite_receita', 0))
    }
    
    # Extrai e soma dados para o gráfico de rosca
    tributos = ['iss', 'icms', 'csll', 'irpj', 'cofins', 'pis_pasep', 'inss_cpp', 'ipi']
    dados_rosca = {t.upper(): float(impostos_pgdas.get(t, 0)) for t in tributos if impostos_pgdas.get(t) is not None}
    
    # Filtra tributos com valor zero para não poluir o gráfico
    dados_rosca = {k: v for k, v in dados_rosca.items() if v > 0}
    
    return {
        "medidor": dados_medidor,
        "rosca": dados_rosca
    }

# --- ENDPOINTS ---
@router.get("/faturamento", summary="Gera gráfico de Faturamento Mensal com tabela", response_class=FileResponse)
def get_grafico_faturamento(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    df_dados = preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico de faturamento.")
    
    caminho_grafico = charts_service.gerar_grafico_faturamento(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/receita-crescimento", summary="Gera gráfico de Receita Bruta vs Taxa de Crescimento", response_class=FileResponse)
def get_grafico_receita_crescimento(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    df_dados = preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico de receita e crescimento.")
    
    caminho_grafico = charts_service.gerar_grafico_receita_crescimento(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/impostos-carga-tributaria", summary="Gera gráfico de Impostos vs Carga Tributária", response_class=FileResponse)
def get_grafico_impostos_carga_tributaria(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    df_dados = preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico de impostos e carga tributária.")
        
    caminho_grafico = charts_service.gerar_grafico_impostos_carga_tributaria(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/acumulado-anual", summary="Gera gráfico de Faturamento e Impostos Acumulados", response_class=FileResponse)
def get_grafico_acumulado(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    df_dados = preparar_dados_para_graficos(db, cnpj, data_inicio, data_fim)
    if df_dados is None or df_dados.empty:
        raise HTTPException(status_code=404, detail="Dados insuficientes para gerar o gráfico de valores acumulados.")
        
    caminho_grafico = charts_service.gerar_grafico_acumulado(df_dados, cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/limite-faturamento", summary="Gera gráfico de medidor para o Limite de Faturamento", response_class=FileResponse)
def get_grafico_limite_faturamento(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    dados_kpis = preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("medidor"):
        raise HTTPException(status_code=404, detail="Dados de PGDAS não encontrados para gerar o gráfico de limite de faturamento.")
    
    caminho_grafico = charts_service.gerar_grafico_limite_faturamento(dados_kpis["medidor"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/sublimite-receita", summary="Gera gráfico de medidor para o Sublimite de Receita (ICMS/ISS)", response_class=FileResponse)
def get_grafico_sublimite_receita(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    dados_kpis = preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("medidor") or not dados_kpis["medidor"].get("sublimite") or dados_kpis["medidor"]["sublimite"] == 0:
        raise HTTPException(status_code=404, detail="Dados de PGDAS com sublimite válido não encontrados para gerar o gráfico.")
    
    caminho_grafico = charts_service.gerar_grafico_sublimite_receita(dados_kpis["medidor"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")

@router.get("/segregacao-tributos", summary="Gera gráfico de rosca para a Segregação dos Tributos", response_class=FileResponse)
def get_grafico_segregacao_tributos(
    cnpj: str = Query(..., description="CNPJ da empresa.", example="20.295.854/0001-50"),
    data_inicio: date = Query(..., description="Data de início do período (YYYY-MM-DD)."),
    data_fim: date = Query(..., description="Data de fim do período (YYYY-MM-DD)."),
    db: Session = Depends(get_db)
):
    dados_kpis = preparar_dados_para_kpis_visuais(db, cnpj, data_inicio, data_fim)
    if not dados_kpis or not dados_kpis.get("rosca"):
        raise HTTPException(status_code=404, detail="Dados de PGDAS não encontrados ou sem valores de tributos para gerar o gráfico de segregação.")
        
    caminho_grafico = charts_service.gerar_grafico_segregacao_tributos(dados_kpis["rosca"], cnpj)
    return FileResponse(caminho_grafico, media_type="image/png")