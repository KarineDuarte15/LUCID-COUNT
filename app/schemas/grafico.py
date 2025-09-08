# app/schemas/grafico.py
from app.schemas.grafico import GraficoResponse
from pydantic import BaseModel
from datetime import datetime

# Você precisará de um schema Pydantic para a resposta.
class GraficoResponse(BaseModel):
    id: int
    tipo_grafico: str
    caminho_arquivo: str
    data_criacao: datetime
    class Config:
         from_attributes = True




