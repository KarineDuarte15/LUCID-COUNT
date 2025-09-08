from enum import Enum

class RegimeTributario(str, Enum):
    SIMPLES_NACIONAL = "Simples Nacional"
    LUCRO_PRESUMIDO_COMERCIO_INDUSTRIA = "Lucro Presumido (Comércio/Indústria ou Comércio/Indústria e Serviços)"
    LUCRO_PRESUMIDO_SERVICOS = "Lucro Presumido (Serviços)"
    LUCRO_REAL_COMERCIO_INDUSTRIA = "Lucro Real (Comércio/Indústria ou Comércio/Indústria e Serviços)"
    LUCRO_REAL_SERVICOS = "Lucro Real (Serviços)"

class TipoDocumento(str, Enum):
    ENCERRAMENTO_ISS = "Encerramento ISS"
    PGDAS = "PGDAS"
    EFD_ICMS = "EFD ICMS"
    EFD_CONTRIBUICOES = "EFD Contribuições"
    MIT = "MIT"
    RELATORIO_SAIDAS = "Relatório de Saídas"
    RELATORIO_ENTRADAS = "Relatório de Entradas"

# Mapeamento centralizado que será usado em toda a aplicação
GRUPOS_POR_REGIME = {
    RegimeTributario.SIMPLES_NACIONAL: [
        TipoDocumento.ENCERRAMENTO_ISS, 
        TipoDocumento.PGDAS
    ],
    RegimeTributario.LUCRO_PRESUMIDO_COMERCIO_INDUSTRIA: [
        TipoDocumento.ENCERRAMENTO_ISS,
        TipoDocumento.EFD_ICMS,
        TipoDocumento.EFD_CONTRIBUICOES,
        TipoDocumento.MIT, 
        TipoDocumento.RELATORIO_SAIDAS,
        TipoDocumento.RELATORIO_ENTRADAS
    ],
    RegimeTributario.LUCRO_PRESUMIDO_SERVICOS: [
        TipoDocumento.ENCERRAMENTO_ISS,
        TipoDocumento.EFD_CONTRIBUICOES,
        TipoDocumento.MIT,
        TipoDocumento.RELATORIO_ENTRADAS
    ],
    RegimeTributario.LUCRO_REAL_COMERCIO_INDUSTRIA: [
        TipoDocumento.ENCERRAMENTO_ISS,
        TipoDocumento.EFD_CONTRIBUICOES,
        TipoDocumento.EFD_ICMS,
        TipoDocumento.RELATORIO_SAIDAS,
        TipoDocumento.RELATORIO_ENTRADAS
    ],
    RegimeTributario.LUCRO_REAL_SERVICOS: [
        TipoDocumento.ENCERRAMENTO_ISS,
        TipoDocumento.EFD_CONTRIBUICOES,
        TipoDocumento.RELATORIO_ENTRADAS
    ]
}

# Em: app/schemas/tipos.py (exemplo)
class TipoGrafico(str, Enum):
    FATURAMENTO = "faturamento"
    IMPOSTOS_CARGA = "impostos_carga"
    SEGREGACAO_TRIBUTOS = "segregacao_tributos"
    CRESCIMENTO_MENSAL = "crescimento_mensal"
    LIMITE_FATURAMENTO = "limite_faturamento"
    SUBLIMITE_RECEITA = "sublimite_receita" 