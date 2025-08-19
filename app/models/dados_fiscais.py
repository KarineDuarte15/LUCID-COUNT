# Em: app/models/dados_fiscais.py

from sqlalchemy import Column, Integer, String, JSON, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from .documento import Documento # Importa a classe Documento do outro ficheiro de modelo

class DadosFiscais(Base):
    __tablename__ = "dados_fiscais"

    id = Column(Integer, primary_key=True, index=True)
    
    # Chave estrangeira para criar o vínculo com o documento original
    documento_id = Column(Integer, ForeignKey("documentos.id"), nullable=False, unique=True)
    
    # Relação para podermos aceder ao documento a partir daqui (ex: dados.documento)
    documento = relationship("Documento")

    tipo_dado = Column(String, index=True) # Ex: "pdf_extracao"
    cnpj = Column(String, index=True)
    
    # Usamos Numeric para valores monetários para evitar problemas de arredondamento do Float
    valor_total = Column(Numeric(10, 2)) 
    
    # O campo JSON é perfeito para guardar os diferentes impostos de cada tipo de documento
    impostos = Column(JSON) 
    
    data_competencia = Column(Date)