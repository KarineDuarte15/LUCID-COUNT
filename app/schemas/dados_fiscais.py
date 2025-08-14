# app/schemas/dados_fiscais.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date

# --- Schema Genérico para Resposta ---
class RespostaProcessamento(BaseModel):
    documento_id: int
    tipo_documento: str
    dados_extraidos: Dict[str, Any]

# --- Schemas Específicos por Tipo de Documento ---

class DadosEncerramentoISS(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    faturamento_servicos: Optional[Decimal] = None
    qtd_nfse_emitidas: Optional[int] = None
    valor_total_servicos_tomados: Optional[Decimal] = None
    qtd_nfse_recebidas: Optional[int] = None
    iss_devido: Optional[Decimal] = None

class DadosEFDICMS(BaseModel):
    cnpj: Optional[str] = None
    debito_credito_icms: Optional[Decimal] = Field(None, description="Valor final do débito ou crédito de ICMS no período.")

class DadosEFDContribuicoes(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    faturamento_total: Optional[Decimal] = None
    credito_debito_pis: Optional[Decimal] = None
    credito_debito_cofins: Optional[Decimal] = None

class DadosMIT(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    csll: Optional[Decimal] = None
    irpj: Optional[Decimal] = None
    ipi: Optional[Decimal] = None

class DadosPGDAS(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    faturamento_total: Optional[Decimal] = None
    irpj: Optional[Decimal] = None
    csll: Optional[Decimal] = None
    pis: Optional[Decimal] = None
    cofins: Optional[Decimal] = None
    icms: Optional[Decimal] = None
    iss: Optional[Decimal] = None
    fator_r: Optional[str] = None # Fator R pode ser um texto ou valor

class DadosRelatorioSaidas(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    faturamento: Optional[Decimal] = None
    cfop: Optional[str] = None
    uf: Optional[str] = None

class DadosRelatorioEntradas(BaseModel):
    cnpj: Optional[str] = None
    periodo: Optional[str] = None
    valor_total_entradas: Optional[Decimal] = None
    cfop: Optional[str] = None
    uf: Optional[str] = None

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
