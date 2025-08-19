# Em: app/crud/dados_fiscais.py

from sqlalchemy.orm import Session
from app.models import dados_fiscais as models
from app.schemas import documento as schemas_documento # Reutilizamos o que for preciso
from decimal import Decimal 
from datetime import date
import re

# Adiciona esta função em app/crud/dados_fiscais.py
def obter_dados_por_documento_id(db: Session, documento_id: int):
    return db.query(models.DadosFiscais).filter(models.DadosFiscais.documento_id == documento_id).first()
def _unificar_e_mapear_dados(dados_extraidos: dict) -> dict:
    """
    Esta função "unifica" os diferentes dicionários dos processadores
    num formato padrão para salvar na base de dados.
    """
    # Mapeamento de possíveis chaves para o valor_total
    chaves_valor_total = [
        'total', 'total_debitos_tributos', 'valor_total_servicos_tomados', 'iss_devido'
    ]
    valor_total = None
    for chave in chaves_valor_total:
        if chave in dados_extraidos and dados_extraidos[chave] is not None:
            valor_total = dados_extraidos[chave]
            break

    # Mapeamento da data de competência
    data_competencia = None
    if dados_extraidos.get("periodo"):
        # Extrai a primeira data no formato MM/AAAA ou dd/mm/aaaa
        match = re.search(r'(\d{2})[/-](\d{4})', str(dados_extraidos["periodo"]))
        if match:
            mes, ano = map(int, match.groups())
            data_competencia = date(ano, mes, 1)

    # Separa os campos principais dos impostos
    campos_principais = ['cnpj', 'periodo', 'receita_bruta_pa']
    impostos = {
        chave: valor for chave, valor in dados_extraidos.items() 
        if chave not in campos_principais and valor is not None
    }
# --- INÍCIO DA CORREÇÃO ---
    # Separa os campos principais dos impostos E CONVERTE DECIMAIS
    campos_principais = ['cnpj', 'periodo', 'receita_bruta_pa']
    impostos = {}
    for chave, valor in dados_extraidos.items():
        if chave not in campos_principais and valor is not None:
            # Se o valor for Decimal, converte para string. Senão, mantém como está.
            impostos[chave] = str(valor) if isinstance(valor, Decimal) else valor
    # --- FIM DA CORREÇÃO ---
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