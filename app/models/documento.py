# app/models/documento.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func

class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True) 
    empresa = relationship("Empresa")

    nome_arquivo_original = Column(String, nullable=False)
    nome_arquivo_unico = Column(String, nullable=False, unique=True) # Nome salvo em disco
    
    tipo_arquivo = Column(String, nullable=False)
    caminho_arquivo = Column(String, nullable=False)
    data_upload = Column(DateTime(timezone=True), server_default=func.now())
    tipo_documento = Column(String, nullable=False, index=True)
        # Relação para acessar os gráficos associados a este documento  
   
    dados_fiscais = relationship(
        "DadosFiscais", 
        back_populates="documento", 
        cascade="all, delete-orphan",
        uselist=False # Assumindo que um documento tem apenas um registo de dados fiscais
    )
    graficos = relationship("Grafico", back_populates="documento", cascade="all, delete-orphan")
