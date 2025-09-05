# app/models/empresa.py

from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Empresa(Base):
    """
    Modelo SQLAlchemy para a tabela de empresas.
    
    Esta classe define a estrutura da tabela 'empresas' na base de dados.
    Será a tabela central para associar todos os outros dados.
    """
    __tablename__ = "empresas"

    # id: Chave primária, um número inteiro que se auto-incrementa.
    id = Column(Integer, primary_key=True, index=True)
    
    # cnpj: O CNPJ da empresa, formatado. Será único para evitar duplicados.
    cnpj = Column(String, unique=True, index=True, nullable=False)
    
    # regime_tributario: O regime tributário da empresa (ex: "Simples Nacional").
    regime_tributario = Column(String, nullable=False)