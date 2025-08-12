# app/routers/upload.py

import shutil
import uuid
import os # Importado para manipulação de ficheiros
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

# Importações da nossa aplicação
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento

# Cria o roteador
router = APIRouter(
    prefix="/upload",
    tags=["Uploads"],
)

# --- Constantes de Validação ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabytes
ALLOWED_MIME_TYPES = ["application/pdf", "application/xml", "text/xml", "text/plain"]
UPLOAD_DIRECTORY = Path("data/uploads")


# --- Dependência da Base de Dados ---
def get_db():
    """
    Função de dependência para obter uma sessão da base de dados.
    Garante que a sessão é sempre fechada após a requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/files/",
    response_model=List[schemas_documento.Documento],
    summary="Recebe, valida e regista múltiplos ficheiros",
    description=f"Faz o upload de um ou mais ficheiros (PDF/XML/TXT, máx {MAX_FILE_SIZE/1024/1024}MB cada), guarda-os e regista os seus metadados na base de dados."
)
async def upload_e_registar_multiplos_ficheiros(
    files: Annotated[List[UploadFile], File(description="Uma lista de ficheiros a serem enviados (PDF, XML ou TXT).")],
    db: Session = Depends(get_db)
):
    """
    Endpoint para receber, validar, salvar múltiplos ficheiros e registar na base de dados.
    """
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    
    documentos_criados = []

    for file in files:
        # Validação de tipo de ficheiro (MIME Type)
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"O ficheiro '{file.filename}' tem um tipo não suportado. Use um dos seguintes: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        # Gerar nome único e caminho do ficheiro
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIRECTORY / unique_filename
        
        try:
            # Lógica de salvar ficheiro primeiro
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            # Captura outros erros que possam ocorrer ao salvar o ficheiro
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Não foi possível salvar o ficheiro '{file.filename}' no disco. Erro: {type(e).__name__} - {e}"
            )

        # Validação de tamanho APÓS salvar o ficheiro
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path) # Apaga o ficheiro se for muito grande
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"O ficheiro '{file.filename}' é muito grande ({file_size / 1024 / 1024:.2f}MB). O tamanho máximo permitido é de {MAX_FILE_SIZE / 1024 / 1024:.1f}MB."
            )

        # Interação com a Base de Dados para cada ficheiro
        try:
            # ATUALIZADO: Lógica para criar o caminho relativo de forma mais segura
            # Constrói o caminho relativo a partir das nossas constantes
            caminho_relativo_str = str(UPLOAD_DIRECTORY / unique_filename).replace('\\', '/')

            documento_a_criar = schemas_documento.DocumentoCreate(
                nome_arquivo=unique_filename,
                tipo_arquivo=file.content_type,
                caminho_arquivo=caminho_relativo_str
            )
            
            documento_criado = crud_documento.criar_novo_documento(db=db, documento=documento_a_criar)
            documentos_criados.append(documento_criado)
            
        except Exception as e:
            # Se algo der errado com a base de dados, apaga o ficheiro que foi salvo
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Não foi possível registar o ficheiro '{file.filename}' na base de dados. Erro: {type(e).__name__} - {e}"
            )
            
    return documentos_criados
