# Em: app/crud/dados_fiscais.py
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import dados_fiscais as models
from app.schemas import documento as schemas_documento # Reutilizamos o que for preciso
from decimal import Decimal 
from datetime import date
from sqlalchemy import and_ # Importa o 'and_' no topo do ficheiro
from datetime import date
import re

# Adiciona esta função em app/crud/dados_fiscais.py
def obter_dados_por_documento_id(db: Session, documento_id: int):
    return db.query(models.DadosFiscais).filter(models.DadosFiscais.documento_id == documento_id).first()
def _unificar_e_mapear_dados(dados_extraidos: dict) -> dict:
    """
    Unifica os dicionários dos processadores num formato padrão para salvar na base de dados.
    """
    # Lógica de Faturamento explícita
    # Se 'receita_bruta_pa' existir, use-a. Senão, use 'valor_total'.
    valor_total = dados_extraidos.get('receita_bruta_pa', dados_extraidos.get('valor_total'))

    # Lógica de data
    data_competencia = None
    periodo_str = dados_extraidos.get("periodo")
    if periodo_str:
        MESES = {
            "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
        }
        match_num = re.search(r'(\d{2})[/-](\d{4})', periodo_str)
        match_txt = re.search(r'([a-zA-Zç]+)\s+de\s+(\d{4})', periodo_str, re.IGNORECASE)
        if match_num:
            mes, ano = map(int, match_num.groups())
            data_competencia = date(ano, mes, 1)
        elif match_txt:
            nome_mes, ano_str = match_txt.groups()
            mes = MESES.get(nome_mes.lower())
            if mes:
                data_competencia = date(int(ano_str), mes, 1)
    # --- CORREÇÃO: CONVERTE DECIMAIS PARA STRING ---
    # Separa os campos principais dos impostos E CONVERTE DECIMAIS
    campos_principais = ['cnpj', 'periodo', 'receita_bruta_pa']
    impostos = {}
    for chave, valor in dados_extraidos.items():
        if chave not in campos_principais and valor is not None:
            # Se o valor for Decimal, converte para string. Senão, mantém como está.
            impostos[chave] = str(valor) if isinstance(valor, Decimal) else valor
   


    # Lógica de impostos
    campos_principais = ['cnpj', 'periodo', 'receita_bruta_pa', 'valor_total']
    impostos = {
        chave: str(valor) if isinstance(valor, Decimal) else valor
        for chave, valor in dados_extraidos.items()
        if chave not in campos_principais and valor is not None
    }

    return {
        "cnpj": dados_extraidos.get("cnpj"),
        "valor_total": valor_total,
        "impostos": impostos,
        "data_competencia": data_competencia,
    }


def salvar_dados_fiscais(db: Session, *, documento_id: int, dados_extraidos: dict):
    """Salva os dados fiscais extraídos, vinculados a um documento."""
    
    dados_mapeados = _unificar_e_mapear_dados(dados_extraidos)

    db_dados_fiscais = models.DadosFiscais(
        documento_id=documento_id,
        tipo_dado="pdf_extracao",
        cnpj=dados_mapeados["cnpj"],
        valor_total=dados_mapeados["valor_total"],
        impostos=dados_mapeados["impostos"],
        data_competencia=dados_mapeados["data_competencia"]
    )
    
    db.add(db_dados_fiscais)
    db.commit()
    db.refresh(db_dados_fiscais)
    return db_dados_fiscais
def obter_dados_por_periodo(db: Session, *, cnpj: str, data_inicio: date, data_fim: date, tipos_documento: list[str] | None = None):
    """
    Obtém registos fiscais para um CNPJ num período, opcionalmente filtrando por tipo de documento.
    """
    query = db.query(models.DadosFiscais).join(models.Documento).filter(
        and_(
            models.DadosFiscais.cnpj == cnpj,
            models.DadosFiscais.data_competencia >= data_inicio,
            models.DadosFiscais.data_competencia <= data_fim
        )
    )
    
    # Se tipos_documento for fornecido, filtra por tipo de documento
    if tipos_documento:
        query = query.filter(models.Documento.tipo_documento.in_(tipos_documento))
    
    return query.all()

 
