# app/routers/documentos.py
import traceback
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import pdfplumber
import xmltodict
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

# Importações da nossa aplicação
from app.core.config import settings # Importa as configurações
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento
from app.schemas.dados_fiscais import RespostaProcessamento
from app.services import processamento as services_processamento

# Mapeia o 'tipo_documento' da base de dados para a função de processamento correta
PROCESSADORES = {
    "Encerramento ISS": services_processamento.processar_iss_pdf,
    "EFD ICMS": services_processamento.processar_efd_icms_pdf,
    "EFD Contribuições": services_processamento.processar_efd_contribuicoes_pdf,
    "MIT": services_processamento.processar_mit_pdf,
    "Declaração PGDAS": services_processamento.processar_pgdas_pdf,
    "Relatório de Saídas": services_processamento.processar_relatorio_saidas,
    "Relatório de Entradas": services_processamento.processar_relatorio_entradas,
    "NFe": services_processamento.processar_nfe_xml,  # Exemplo de processamento de NFe
    # Adicione os outros tipos de documento aqui à medida que os for implementando
}

router = APIRouter(
    prefix="/documentos",
    tags=["Documentos"],
)

# --- Dependência da Base de Dados ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/",
    response_model=List[schemas_documento.Documento],
    summary="Lista todos os documentos registados"
)
def listar_documentos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtém uma lista de todos os registos de documentos da base de dados.
    """
    documentos = crud_documento.obter_documentos(db, skip=skip, limit=limit)
    return documentos

@router.post(
    "/{documento_id}/processar",
    response_model=RespostaProcessamento,
    summary="Processa um documento e extrai os seus dados"
)
def processar_documento_por_id(documento_id: int, db: Session = Depends(get_db)):
    """
    Encontra um documento pelo seu ID e chama o serviço de processamento
    apropriado com base no seu 'tipo_documento'.
    """
    db_documento = crud_documento.obter_documento_por_id(db, documento_id=documento_id)
    if not db_documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    funcao_processamento = PROCESSADORES.get(db_documento.tipo_documento)
    
    if not funcao_processamento:
        raise HTTPException(
            status_code=400,
            detail=f"O processamento para o tipo de documento '{db_documento.tipo_documento}' não está implementado."
        )

    caminho_absoluto = Path(db_documento.caminho_arquivo).resolve()
    
    if not caminho_absoluto.exists():
        raise HTTPException(status_code=404, detail=f"Ficheiro físico não encontrado: {caminho_absoluto}")

    try:
        # A lógica agora é mais clara: cada bloco é responsável por gerar os dados_extraidos.
        # Removemos a chamada confusa no final do bloco try.

        if db_documento.tipo_arquivo == "application/pdf":
            # A função de processamento de PDF espera o CAMINHO do ficheiro.
            dados_extraidos = funcao_processamento(caminho_absoluto)

        elif db_documento.tipo_arquivo in ["application/xml", "text/xml"]:
            # Assumindo que a função de XML também espera o CAMINHO.
            dados_extraidos = funcao_processamento(caminho_absoluto)
            
        elif db_documento.tipo_arquivo == "text/plain":
            # A função de processamento de TXT espera o CONTEÚDO do ficheiro.
            conteudo_texto = caminho_absoluto.read_text(encoding='utf-8')
            dados_extraidos = funcao_processamento(conteudo_texto)

        else:
            # Se o tipo de ficheiro não for nenhum dos esperados, levantamos um erro.
            raise HTTPException(status_code=415, detail=f"Tipo de ficheiro não suportado: '{db_documento.tipo_arquivo}'")

        # No final do bloco, retornamos o resultado.
        return RespostaProcessamento(
            documento_id=documento_id,
            tipo_documento=db_documento.tipo_documento,
            dados_extraidos=dados_extraidos
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno durante o processamento do ficheiro: {str(e)}")