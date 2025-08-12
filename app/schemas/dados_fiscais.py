# app/schemas/dados_fiscais.py

from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal # NOVO: Importa o tipo Decimal

class ProdutoNFe(BaseModel):
    """Schema para os dados de um único produto dentro da NFe."""
    cfop: Optional[str] = Field(None, description="Código Fiscal de Operações e Prestações.")
    ncm: Optional[str] = Field(None, description="Nomenclatura Comum do Mercosul.")

class DadosNFe(BaseModel):
    """Schema para os dados extraídos de um ficheiro XML de NFe."""
    cnpj_emitente: Optional[str] = Field(None, description="CNPJ do emitente da nota.")
    valor_total: Optional[Decimal] = Field(None, description="Valor total da nota fiscal.") # ATUALIZADO para Decimal
    produtos: List[ProdutoNFe] = Field([], description="Lista de produtos contidos na nota.")

class NFeProcessadaResponse(BaseModel):
    """Schema final da resposta da API após processar uma NFe."""
    documento_id: int
    dados_nfe: DadosNFe
    
    class Config:
        from_attributes = True
