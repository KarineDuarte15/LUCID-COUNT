# Em: app/models/grafico.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Grafico(Base):
    """
    Modelo SQLAlchemy para a tabela de gráficos.

    Esta tabela armazena os metadados de cada gráfico gerado,
    associando-o a um documento específico.
    """
    __tablename__ = "graficos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Chave estrangeira para o documento que originou os dados do gráfico
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False)
    
    # Tipo do gráfico (ex: 'faturamento', 'segregacao_tributos')
    tipo_grafico = Column(String, index=True, nullable=False)
    
    # Caminho onde o arquivo de imagem do gráfico foi salvo
    caminho_arquivo = Column(String, nullable=False, unique=True)
    
    # Data e hora da criação do registro, com valor padrão automático
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())

    # Relação para podermos acessar o documento a partir de um objeto Grafico
    documento = relationship("Documento", back_populates="graficos")