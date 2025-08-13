# app/routers/documentos.py

from typing import List, Dict, Any # Importa Dict e Any para o modelo de resposta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Response # NOVO: Importa Response
from sqlalchemy.orm import Session
import pandas as pd # Importa pandas para manipulação de DataFrames

# Importações da nossa aplicação
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento
from app.services import processamento as services_processamento

# Cria um novo roteador para os endpoints de documentos
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
    response_model=List[Dict[str, Any]], # ATUALIZADO: A resposta agora é uma lista de dicionários (JSON de tabela)
    summary="Processa um XML de NFe e retorna os dados em formato de tabela"
)
def processar_documento_e_estruturar(
    documento_id: int,
    db: Session = Depends(get_db)
):
    """
    Encontra um documento, processa o ficheiro XML de NFe associado,
    estrutura os dados num DataFrame e retorna-o como JSON.
    """
    db_documento = crud_documento.obter_documento_por_id(db, documento_id=documento_id)
    if db_documento is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if db_documento.tipo_arquivo not in ["application/xml", "text/xml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O tipo de ficheiro '{db_documento.tipo_arquivo}' não é um XML processável."
        )

    caminho_arquivo = Path(db_documento.caminho_arquivo)

    try:
        # Passo 1: Extrai os dados brutos do XML
        dados_extraidos_nfe = services_processamento.processar_nfe_xml(caminho_arquivo)
        
        # Passo 2: Converte os dados brutos para um DataFrame estruturado
        df_documento = services_processamento.xml_para_dataframe(dados_extraidos_nfe)
        
        # Passo 3: Converte o DataFrame para um formato JSON (lista de dicionários)
        # O 'orient="records"' cria exatamente o formato que a API precisa.
        return df_documento.to_dict(orient="records")
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ficheiro físico '{caminho_arquivo}' não foi encontrado no servidor."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro ao processar ou validar o ficheiro XML: {e}"
        )
