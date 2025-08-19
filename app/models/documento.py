# app/models/documento.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from sqlalchemy.sql import func

# Importamos o objeto 'Base' do nosso módulo de banco de dados.
# Todas as nossas classes de modelo herdarão desta classe.
from app.core.database import Base

class Documento(Base):
    """
    Modelo SQLAlchemy para a tabela de documentos.
    
    Esta classe define a estrutura da tabela 'tabela_documentos' no banco de dados.
    O SQLAlchemy usará esta definição para criar a tabela e para mapear
    os resultados das consultas a objetos desta classe.
    """
    __tablename__ = "documentos"

    # Define as colunas da tabela:
    
    # id: Chave primária, um número inteiro que se auto-incrementa.
    id = Column(Integer, primary_key=True, index=True)
    
    # nome_arquivo: O nome único do ficheiro salvo no sistema (ex: UUID).
    # Não pode ser nulo.
    nome_arquivo = Column(String, nullable=False)
    
    # tipo_arquivo: O tipo MIME do ficheiro (ex: 'application/pdf').
    tipo_arquivo = Column(String, nullable=False)
    
    # caminho_arquivo: O caminho relativo onde o ficheiro foi salvo.
    caminho_arquivo = Column(String, nullable=False)
    
    # data_upload: A data e hora em que o registo foi criado.
    # O valor padrão é a data e hora atuais do banco de dados.
    data_upload = Column(DateTime(timezone=True), server_default=func.now())
    
    # tipo_documento: Coluna para identificar o tipo de documento (ex: "Encerramento ISS")
    tipo_documento = Column(String, nullable=False, index=True)