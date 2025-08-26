from sqlalchemy import Column, Integer, String
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    cnpj = Column(String, unique=True, index=True, nullable=False)
    regime_tributario = Column(String, nullable=False)
