# app/models/empresa.py

from sqlalchemy import Column, Integer, String, Boolean, JSON
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    
    # --- Campos Principais ---
    cnpj = Column(String, unique=True, index=True, nullable=False)
    regime_tributario = Column(String, nullable=False)
    razao_social = Column(String, nullable=True)
    nome_fantasia = Column(String, nullable=True)
    ativa = Column(Boolean, default=True)

    # --- Endereço e Contato (armazenados como JSON) ---
    endereco = Column(JSON, nullable=True)
    # Exemplo: {"logradouro": "Av...", "numero": "123", "cep": "60000-000", ...}
    
    fones = Column(JSON, nullable=True) # Para armazenar uma lista de telefones
    website = Column(String, nullable=True)
    
    # --- Dados Fiscais e de Registro ---
    inscricao_municipal = Column(String, nullable=True)
    inscricoes_estaduais = Column(JSON, nullable=True) 
    # Exemplo: [{"inscricao": "12345", "data": "2024-01-01", "uf": "CE"}]
    
    nire = Column(String, nullable=True)
    outros_identificadores = Column(JSON, nullable=True)

    # --- Outras Informações ---
    grupo_empresas = Column(String, nullable=True)
    apelido_continuo = Column(String, nullable=True)
    contatos = Column(JSON, nullable=True)
    # Exemplo: [{"nome": "Fulano", "cargo": "CEO", "celular": "8599999...", "email": "..."}]