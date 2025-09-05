# app/schemas/documento.py

from pydantic import BaseModel
from datetime import datetime

# --- Schema Base ---
class DocumentoBase(BaseModel):
    # ADICIONAR ESTA LINHA:
    empresa_id: int
    tipo_documento: str
    nome_arquivo_original: str
    nome_arquivo_unico: str
    tipo_arquivo: str
    caminho_arquivo: str

# --- Schema para Criação ---
class DocumentoCreate(DocumentoBase):
    pass

# --- Schema para Leitura/Resposta ---
class Documento(DocumentoBase):
    id: int
    data_upload: datetime

    class Config:
        from_attributes = True