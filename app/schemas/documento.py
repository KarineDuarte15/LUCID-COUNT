# app/schemas/documento.py

from pydantic import BaseModel
from datetime import datetime

# --- Schema Base ---
# Contém os campos comuns que são partilhados por outros schemas.
# Isto evita a repetição de código.
class DocumentoBase(BaseModel):
    tipo_documento: str 
    nome_arquivo: str
    tipo_arquivo: str
    caminho_arquivo: str

# --- Schema para Criação ---
# Usado especificamente quando estamos a criar um novo documento no banco.
# Herda todos os campos do DocumentoBase.
class DocumentoCreate(DocumentoBase):
    pass # Não precisa de campos adicionais por agora

# --- Schema para Leitura/Resposta ---
# Usado quando retornamos os dados de um documento a partir da API.
# Herda os campos do DocumentoBase e adiciona os campos que são gerados
# pelo banco de dados (id e data_upload).
class Documento(DocumentoBase):
    id: int
    data_upload: datetime

    # Configuração para que o Pydantic consiga ler os dados a partir de um
    # objeto SQLAlchemy (modo ORM).
    class Config:
        from_attributes = True
