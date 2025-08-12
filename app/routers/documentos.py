# app/routers/documentos.py

from typing import List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importações da nossa aplicação
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento
from app.schemas import dados_fiscais as schemas_dados_fiscais
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
    response_model=schemas_dados_fiscais.NFeProcessadaResponse, # ATUALIZADO
    summary="Processa um documento XML de NFe e extrai dados fiscais"
)
def processar_documento_por_id(
    documento_id: int,
    db: Session = Depends(get_db)
):
    """
    Encontra um documento pelo seu ID, processa o ficheiro XML de NFe associado
    e retorna os dados fiscais extraídos.
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
        # ATUALIZADO: Chama a nova função específica para NFe
        dados_extraidos_nfe = services_processamento.processar_nfe_xml(caminho_arquivo)
        
        # Monta a resposta final de acordo com o schema
        resposta = {
            "documento_id": documento_id,
            "dados_nfe": dados_extraidos_nfe
        }
        return resposta
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O ficheiro físico '{caminho_arquivo}' não foi encontrado no servidor."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro ao processar o ficheiro XML: {e}"
        )
