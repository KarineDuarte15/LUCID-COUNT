# app/schemas/empresa.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- Schemas para dados aninhados (JSON) ---
class EnderecoSchema(BaseModel):
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    cep: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None

class InscricaoEstadualSchema(BaseModel):
    inscricao: Optional[str] = None
    data: Optional[str] = None
    uf: Optional[str] = None

class ContatoSchema(BaseModel):
    nome: Optional[str] = None
    cargo: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None

# --- Schema Principal da Empresa ---
class EmpresaBase(BaseModel):
    cnpj: str = Field(..., example="54.811.719/0001-31")
    regime_tributario: str = Field(..., example="Simples Nacional")
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    ativa: bool = True
    endereco: Optional[EnderecoSchema] = None
    fones: Optional[List[str]] = None
    website: Optional[str] = None
    inscricao_municipal: Optional[str] = None
    inscricoes_estaduais: Optional[List[InscricaoEstadualSchema]] = None
    nire: Optional[str] = None
    outros_identificadores: Optional[List[str]] = None
    grupo_empresas: Optional[str] = None
    apelido_continuo: Optional[str] = None
    contatos: Optional[List[ContatoSchema]] = None

# Schema para criação (o que a API recebe)
class EmpresaCreate(EmpresaBase):
    pass

# Schema para resposta (o que a API envia de volta)
class EmpresaResponse(EmpresaBase):
    id: int
    
    class Config:
        from_attributes = True # Antigo orm_mode