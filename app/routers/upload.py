from fastapi import APIRouter, File, UploadFile, HTTPException, status
from typing import Annotated, List
from pathlib import Path
import uuid
import shutil

from app.schemas.upload import UploadResponse

router = APIRouter(
    prefix="/upload",
    tags=["Uploads"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/xml",
    "text/xml",
    "text/plain"
]
BASE_UPLOAD_DIRECTORY = Path("data/uploads")

# Mapeamento de tipos de documentos → pastas
DOCUMENT_FOLDERS = {
    "encerramento_iss": "Encerramento_ISS",
    "efd_icms": "EFD_ICMS",
    "efd_contribuicoes": "EFD_Contribuicoes",
    "mit": "MIT",
    "pgdas": "PGDAS",
    "relatorio_saidas": "Relatorio_Saidas",
    "relatorio_entradas": "Relatorio_Entradas"
}

@router.post(
    "/files/",
    response_model=list[UploadResponse],
    summary="Recebe múltiplos ficheiros",
    description="Upload de múltiplos ficheiros (PDF, XML, TXT) organizados por tipo de documento."
)
async def upload_multiple_files(
    files: Annotated[List[UploadFile], File(description="Lista de ficheiros a enviar")],
    doc_type: str = "encerramento_iss"  # tipo de documento
):
    if doc_type not in DOCUMENT_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de documento inválido. Tipos permitidos: {', '.join(DOCUMENT_FOLDERS.keys())}"
        )

    saved_files = []
    target_dir = BASE_UPLOAD_DIRECTORY / DOCUMENT_FOLDERS[doc_type]
    target_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Tipo não suportado ({file.filename})."
            )

        size = await file.read()
        if len(size) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo muito grande: {file.filename}"
            )
        await file.seek(0)

        unique_name = f"{uuid.uuid4()}{Path(file.filename).suffix}"
        file_path = target_dir / unique_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_files.append(UploadResponse(
            filename=unique_name,
            content_type=file.content_type,
            size_in_bytes=len(size)
        ))

    return saved_files
