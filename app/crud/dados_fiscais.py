# Em: app/crud/dados_fiscais.py
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import dados_fiscais as models
from decimal import Decimal
from datetime import date
from sqlalchemy import and_
import re

def obter_dados_por_documento_id(db: Session, documento_id: int):
    return db.query(models.DadosFiscais).filter(models.DadosFiscais.documento_id == documento_id).first()

def _unificar_e_mapear_dados(dados_extraidos: dict) -> dict:
    """
    Prepara os dados extraídos para serem salvos, convertendo tipos e
    identificando a data de competência.
    """
    valor_total = dados_extraidos.get('receita_bruta_pa') or \
                  dados_extraidos.get('valor_total') or \
                  dados_extraidos.get('valor_total_entradas') or \
                  Decimal("0.00")

    data_competencia = None
    periodo_str = dados_extraidos.get("periodo")
    if periodo_str:
        match_num = re.search(r'(\d{2})[/-](\d{4})', periodo_str)
        if match_num:
            mes, ano = map(int, match_num.groups())
            data_competencia = date(ano, mes, 1)

    campos_principais = ['cnpj', 'periodo', 'receita_bruta_pa', 'valor_total', 'valor_total_entradas']
    impostos = {}
    for chave, valor in dados_extraidos.items():
        if chave not in campos_principais and valor is not None:
            if isinstance(valor, Decimal):
                impostos[chave] = str(valor)
            elif isinstance(valor, dict):
                impostos[chave] = {k: str(v) if isinstance(v, Decimal) else v for k, v in valor.items()}
            else:
                impostos[chave] = valor
    
    return {
        "cnpj": dados_extraidos.get("cnpj"),
        "valor_total": valor_total,
        "impostos": impostos,
        "data_competencia": data_competencia,
    }

def salvar_dados_fiscais(db: Session, *, documento_id: int, dados_extraidos: dict):
    """Salva os dados fiscais extraídos, vinculados a um documento."""
    
    # Verifica se já existem dados para este documento
    db_dados_existentes = obter_dados_por_documento_id(db, documento_id)
    if db_dados_existentes:
        # Se existem, atualiza em vez de criar um novo
        return atualizar_dados_fiscais(db, db_dados_existentes, dados_extraidos)

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


def atualizar_dados_fiscais(db: Session, db_dados_fiscais: models.DadosFiscais, dados_atualizados: Dict[str, Any]) -> models.DadosFiscais:
    """Atualiza um registo de dados fiscais com os dados validados pelo utilizador."""
    
    dados_mapeados = _unificar_e_mapear_dados(dados_atualizados)

    db_dados_fiscais.cnpj = dados_mapeados["cnpj"]
    db_dados_fiscais.valor_total = dados_mapeados["valor_total"]
    db_dados_fiscais.impostos = dados_mapeados["impostos"]
    db_dados_fiscais.data_competencia = dados_mapeados["data_competencia"]
    
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
    if tipos_documento:
        query = query.filter(models.Documento.tipo_documento.in_(tipos_documento))
    return query.all()