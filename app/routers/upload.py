# app/routers/upload.py

import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from typing import Annotated

# Importa o schema de resposta que criamos
from app.schemas.upload import UploadResponse

# Cria um novo "roteador". Podemos pensar nisso como uma mini-aplicação FastAPI.
router = APIRouter(
    prefix="/upload",  # Todos os endpoints neste router começarão com /upload
    tags=["Uploads"],   # Agrupa os endpoints na documentação sob o título "Uploads"
)

# --- Constantes de Validação ---
# Define o tamanho máximo do arquivo em bytes (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabytes
# Define os tipos de arquivo permitidos (MIME types)
ALLOWED_MIME_TYPES = ["application/pdf", "application/xml", "text/xml"]
# Define o diretório onde os arquivos serão salvos
UPLOAD_DIRECTORY = Path("data/uploads")


@router.post(
    "/file/",
    response_model=UploadResponse,
    summary="Recebe um único arquivo (PDF ou XML)",
    description=f"Faz o upload de um arquivo para o servidor, validando o tipo (PDF, XML) e o tamanho (máx {MAX_FILE_SIZE / 1024 / 1024}MB)."
)
async def upload_validated_file(
    file: Annotated[UploadFile, File(description="O arquivo a ser enviado (PDF ou XML).")]
):
    """
    Endpoint para receber, validar e salvar um arquivo.

    ### Validações:
    1.  **Tipo de Arquivo**: Aceita apenas `application/pdf` e `application/xml`.
    2.  **Tamanho do Arquivo**: O arquivo não pode exceder 10MB.

    O arquivo é salvo com um nome único (UUID) para evitar conflitos.
    """
    # Garante que o diretório de upload exista
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # --- 1. Validação do Tipo de Arquivo (MIME Type) ---
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de arquivo não suportado. Use um dos seguintes: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # --- 2. Validação do Tamanho do Arquivo ---
    # Mede o tamanho do arquivo de forma segura
    size = await file.read()
    if len(size) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. O tamanho máximo permitido é de {MAX_FILE_SIZE / 1024 / 1024:.1f}MB."
        )
    # Retorna o cursor para o início do arquivo para poder salvá-lo
    await file.seek(0)

    # --- 3. Gerar Nome Único e Salvar o Arquivo ---
    try:
        # Pega a extensão do arquivo original (ex: .pdf)
        file_extension = Path(file.filename).suffix
        # Gera um nome de arquivo único usando UUID
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        # Monta o caminho completo para salvar o arquivo
        file_path = UPLOAD_DIRECTORY / unique_filename

        # Salva o arquivo no disco
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        # Se algo der errado ao salvar, lança um erro interno do servidor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível salvar o arquivo. Erro: {e}"
        )

    # --- 4. Retornar Resposta de Sucesso ---
    return UploadResponse(
        filename=unique_filename,  # Retorna o nome único com o qual o arquivo foi salvo
        content_type=file.content_type,
        size_in_bytes=len(size)
    )
