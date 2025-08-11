
# app/routers/upload.py

import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from typing import Annotated

# Importa o schema de resposta usando um import absoluto a partir da raiz do pacote 'app'
from app.schemas.upload import UploadResponse

# Cria um novo "roteador". Podemos pensar nisso como uma mini-aplicação FastAPI.
router = APIRouter(
    prefix="/upload",
    tags=["Uploads"],
)

# --- Constantes de Validação ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabytes
ALLOWED_MIME_TYPES = ["application/pdf", "application/xml", "text/xml", "text/plain"  ]
UPLOAD_DIRECTORY = Path("data/uploads")


@router.post(
    "/file/",
    response_model=UploadResponse,
    summary="Recebe um único ficheiro (PDF ou XML)",
    description=f"Faz o upload de um ficheiro para o servidor, validando o tipo (PDF, XML ou TXT) e o tamanho (máx {MAX_FILE_SIZE / 1024 / 1024}MB)."
)
async def upload_validated_file(
    file: Annotated[UploadFile, File(description="O ficheiro a ser enviado (PDF ou XML,TXTS).")]
):
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de ficheiro não suportado. Use um dos seguintes: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    size = await file.read()
    if len(size) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ficheiro muito grande. O tamanho máximo permitido é de {MAX_FILE_SIZE / 1024 / 1024:.1f}MB."
        )
    await file.seek(0)

    try:
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIRECTORY / unique_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível salvar o ficheiro. Erro: {e}"
        )

    return UploadResponse(
        filename=unique_filename,
        content_type=file.content_type,
        size_in_bytes=len(size)
    )
