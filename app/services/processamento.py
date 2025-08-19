# app/services/processamento.py

import xmltodict
import pandas as pd
import re
import pdfplumber 
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal, InvalidOperation

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import re
import xmltodict
import pandas as pd




# PDF
try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover - ambiente sem pdfplumber
    pdfplumber = None

# ==========================
# Helpers
# ==========================

def _arquivo_existe(caminho: Path) -> None:
    if not Path(caminho).exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")


def _ler_texto_pdf(caminho: Path) -> str:
    _arquivo_existe(caminho)
    if pdfplumber is None:
        raise RuntimeError("pdfplumber não está disponível no ambiente.")

    texto = []
    with pdfplumber.open(caminho) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            texto.append(t)
    return "\n".join(texto)


def _limpar_valor_monetario(valor_str: str) -> Optional[Decimal]:
    if valor_str is None:
        return None
    s = str(valor_str)
    # remove R$, pontos de milhar e espaços
    s = re.sub(r"[R\$\s]", "", s)
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _extrair_por_regex(pattern: str, texto: str, flags: int = re.IGNORECASE | re.MULTILINE) -> Optional[str]:
    m = re.search(pattern, texto, flags)
    return m.group(1).strip() if m else None


def _extrair_valor(pattern: str, texto: str) -> Optional[Decimal]:
    g = _extrair_por_regex(pattern, texto)
    return _limpar_valor_monetario(g) if g is not None else None


def _extrair_int(pattern: str, texto: str) -> Optional[int]:
    g = _extrair_por_regex(pattern, texto)
    if g is None:
        return None
    try:
        return int(re.sub(r"[^0-9]", "", g))
    except ValueError:
        return None


def _normalizar_periodo_mm_aaaa(raw: Optional[str]) -> Optional[str]:
    """Aceita formatos como 05/2025, 2025-05, Maio/2025, etc., e tenta retornar MM/AAAA."""
    if not raw:
        return None
    s = raw.strip()
    # MM/AAAA
    m = re.search(r"(0?[1-9]|1[0-2])\s*[/.-]\s*(\d{4})", s)
    if m:
        mm = m.group(1).zfill(2)
        aaaa = m.group(2)
        return f"{mm}/{aaaa}"
    # AAAA-MM
    m = re.search(r"(\d{4})\s*[-/.]\s*(0?[1-9]|1[0-2])", s)
    if m:
        aaaa = m.group(1)
        mm = m.group(2).zfill(2)
        return f"{mm}/{aaaa}"
    # Nome do mês/AAAA (básico)
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08", "setembro": "09",
        "outubro": "10", "novembro": "11", "dezembro": "12",
    }
    m = re.search(r"([A-Za-zçÇãõáéíóúÁÉÍÓÚ]+)\s*[/.-]\s*(\d{4})", s, re.IGNORECASE)
    if m:
        mm = meses.get(m.group(1).lower())
        if mm:
            return f"{mm}/{m.group(2)}"
    return s  # retorna original se não conseguiu normalizar

# --- Funções Auxiliares para Extração ---
def _extrair_valor(padrao: str, texto: str) -> Decimal | None:
    match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    if match:
        valor_str = match.group(1).strip().replace('.', '').replace(',', '.')
        try:
            return Decimal(valor_str)
        except InvalidOperation: return None
    return None
def _converter_valor(valor_str: str | None) -> Decimal | None:
    """Converte uma string de valor (ex: 'R$ 1.234,56') para um objeto Decimal."""
    if not isinstance(valor_str, str):
        return None
    try:
        # Limpa a string e converte para Decimal
        valor_limpo = valor_str.replace("R$", "").strip().replace(".", "").replace(",", ".")
        return Decimal(valor_limpo)
    except (ValueError, TypeError, InvalidOperation):
        return None

def _extrair_texto(padrao: str, texto: str) -> str | None:
    match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None

def _extrair_int(padrao: str, texto: str) -> int | None:
    match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    return int(match.group(1).strip()) if match else None

# --- Funções de Leitura de Ficheiros ---
def ler_pdf(caminho_arquivo: Path) -> str:
    """Função auxiliar para ler todo o texto de um ficheiro PDF."""
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"O ficheiro não foi encontrado em: {caminho_arquivo}")
    texto_completo = ""
    with pdfplumber.open(caminho_arquivo) as pdf:
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"
    return texto_completo

def ler_xml(caminho_arquivo: Path) -> Dict[str, Any]:
    """Função auxiliar para ler e converter um ficheiro XML para dicionário."""
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"O ficheiro não foi encontrado em: {caminho_arquivo}")
    with open(caminho_arquivo, 'rb') as f:
        xml_content = f.read()
    return xmltodict.parse(xml_content)




# ==========================
# NFe XML
# ==========================

def processar_nfe_xml(caminho_arquivo: Path) -> Dict[str, Any]:
    """Lê um arquivo XML de NFe e extrai dados fiscais essenciais.

    Retorna:
        {
          "cnpj_emitente": str | None,
          "valor_total": Decimal | None,
          "produtos": List[{"cfop": str | None, "ncm": str | None}]
        }
    """
    _arquivo_existe(caminho_arquivo)

    try:
        with open(caminho_arquivo, "rb") as f:
            xml_content = f.read()
        dados = xmltodict.parse(xml_content)

        inf_nfe = dados.get("nfeProc", {}).get("NFe", {}).get("infNFe", {})
        if not inf_nfe:
            inf_nfe = dados.get("NFe", {}).get("infNFe", {})
        if not inf_nfe:
            raise ValueError("Estrutura de NFe inválida ou não encontrada no XML.")

        emitente = inf_nfe.get("emit", {})
        total = inf_nfe.get("total", {}).get("ICMSTot", {})

        produtos_extraidos: List[Dict[str, Optional[str]]] = []
        lista_produtos_xml = inf_nfe.get("det", [])
        if not isinstance(lista_produtos_xml, list):
            lista_produtos_xml = [lista_produtos_xml]
        for item in lista_produtos_xml:
            prod = item.get("prod", {}) if isinstance(item, dict) else {}
            produtos_extraidos.append({
                "cfop": prod.get("CFOP"),
                "ncm": prod.get("NCM"),
            })

        valor_total_decimal: Optional[Decimal] = None
        valor_total_str = total.get("vNF") if isinstance(total, dict) else None
        if valor_total_str:
            try:
                valor_total_decimal = Decimal(str(valor_total_str))
            except InvalidOperation:
                valor_total_decimal = None

        return {
            "cnpj_emitente": emitente.get("CNPJ") if isinstance(emitente, dict) else None,
            "valor_total": valor_total_decimal,
            "produtos": produtos_extraidos,
        }
    except Exception as e:
        raise ValueError(f"Falha ao processar XML {caminho_arquivo}: {e}") from e
# ==========================
# Encerramento ISS (PDF)
# ==========================

def processar_iss_pdf(caminho_arquivo: Path) -> Dict[str, Any]:
    """Extrai dados de Encerramento ISS a partir de PDF (via pdfplumber + regex)."""
    texto = _ler_texto_pdf(caminho_arquivo)

    dados: Dict[str, Any] = {
        "cnpj": _extrair_por_regex(r"CNPJ\s*:?\s*([\d./-]+)", texto),
        "periodo": _normalizar_periodo_mm_aaaa(_extrair_por_regex(r"Compet[êe]ncia\s*:\s*([A-Za-z]+\s+de\s+\d{4})", texto)),        
        "valor_total_servicos_tomados": _extrair_valor(r"Serviços\s+Tomados[\s\S]*?Somatório\s+[\d.]+\s+([\d.,]+)", texto),
        "valor_total_servicos_tomados": _extrair_valor(r"Serviços\s+Tomados[\s\S]*?Somatório\s+[\d.]+\s+([\d.,]+)", texto),
        "qtd_nfse_emitidas": _extrair_int(r"Serviços\s+Prestados[\s\S]*?Somatório\s+([\d.]+)", texto),
        "iss_devido": _extrair_valor(r"ISS\s+Próprio[\s\d.,]+?([\d.,]+)\s*$", texto),
    }
    return dados


def pdf_iss_para_dataframe(dados: Dict[str, Any]) -> pd.DataFrame:
    """Converte o dicionário do ISS em DataFrame padronizado."""
    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame([dados]).rename(columns={
        "cnpj": "CNPJ",
        "periodo": "Período",
        "faturamento_servicos": "Faturamento_Serviços",
        "qtd_nfse_emitidas": "Qtd_NFSe_Emitidas",
        "valor_total_servicos_tomados": "Valor_Total_Serviços_Tomados",
        "qtd_nfse_recebidas": "Qtd_NFSe_Recebidas",
        "iss_devido": "ISS_Devido",
    })

    # Validações básicas
    if df["CNPJ"].isna().all():
        raise ValueError("CNPJ não encontrado no PDF de ISS.")

    return df



# ==========================
# EFD ICMS (PDF) – Débito/Crédito por período
# ==========================

def processar_efd_icms_pdf(caminho_arquivo: Path) -> Dict[str, Any]:
    """
    Extrai CNPJ, Período e valores de ICMS de um PDF EFD-ICMS.
    
    Retorna um DICIONÁRIO com os dados extraídos, compatível com a API.
    """
    texto = _ler_texto_pdf(caminho_arquivo)

    # --- 1. Extração individual de cada campo ---
    cnpj = _extrair_por_regex(r"CNPJ/CPF:\s*([\d./-]+)", texto)
    periodo_raw = _extrair_por_regex(r"Período:\s*([\d/]+\s+a\s+[\d/]+)", texto)
    periodo = _normalizar_periodo_mm_aaaa(periodo_raw)
    
    # Extrai os valores da tabela de apuração
    icms_a_recolher = _extrair_valor(r"Valor\s+total\s+do\s+ICMS\s+a\s+recolher[\s\S]*?R\$\s*([\d.,]+)", texto)
    saldo_credor = _extrair_valor(r"saldo\s+credor\s+a\s+transportar[\s\S]*?R\$\s*([\d.,]+)", texto)

    # --- 2. Montagem do dicionário de retorno ---
    dados = {
        "cnpj": cnpj,
        "periodo": periodo,
        "icms_a_recolher": icms_a_recolher,
        "saldo_credor_a_transportar": saldo_credor
    }
    
    return dados
# ==========================
# EFD Contribuições (PDF) - VERSÃO CORRIGIDA
# ==========================

def processar_efd_contribuicoes_pdf(caminho_arquivo: Path) -> Dict[str, Any]:
    """Extrai dados de um PDF de EFD-Contribuições e retorna um dicionário."""
    texto = _ler_texto_pdf(caminho_arquivo)

    # --- Lógica de extração ---
    cnpj = _extrair_por_regex(r"CNPJ:\s*([\d./-]+)", texto)
    periodo = _normalizar_periodo_mm_aaaa(_extrair_por_regex(r"Período\s+de\s+apuração:\s*([\d/]+\s+a\s+[\d/]+)", texto))


    match_creditos = re.search(r"Valor\s+total\s+dos\s+créditos\s+descontados[\s\S]*?R\$\s*([\d.,]+)[\s\S]*?R\$\s*([\d.,]+)", texto)
    pis_credito_str = match_creditos.group(1) if match_creditos else "0.00"
    cofins_credito_str = match_creditos.group(2) if match_creditos else "0.00"

    match_debitos = re.search(
        r"= Valor da Contribuição Social a Recolher\s*R\$\s*([\d.,]+)\s*R\$\s*([\d.,]+)",
        texto
    )
    pis_debito_str = match_debitos.group(1) if match_debitos else "0.00"
    cofins_debito_str = match_debitos.group(2) if match_debitos else "0.00"

    # Se não encontrou créditos/débitos, tenta extrair faturamento total
    pis_credito = _converter_valor(pis_credito_str)
    cofins_credito = _converter_valor(cofins_credito_str)
    pis_debito = _converter_valor(pis_debito_str)
    cofins_debito = _converter_valor(cofins_debito_str)

    # --- Montar o dicionário de resultados ---
    dados = {
        "cnpj": cnpj,
        "periodo": periodo,
        "pis_credito": pis_credito,
        "pis_debito": pis_debito,
        "cofins_credito": cofins_credito,
        "cofins_debito": cofins_debito,
    }
    
    return dados
# ==========================
# MIT
# ==========================

def processar_mit_pdf(caminho_arquivo: Path) -> pd.DataFrame:
    """
    Extrai de um PDF de Recibo de Entrega da DCTFWeb os campos:
    CNPJ, Período, CSLL, IRPJ e IPI.
    
    Retorna um DICIONÁRIO com os dados extraídos, compatível com a API.
    """
    texto = _ler_texto_pdf(caminho_arquivo)

    # --- 1. Extração dos dados do cabeçalho ---
    cnpj = _extrair_por_regex(r"CNPJ/CPF\s*([\d./-]+)", texto)
    periodo = _normalizar_periodo_mm_aaaa(_extrair_por_regex(r"Período\s+de\s+apuração\s*(\d{2}/\d{4})", texto))

    # --- 2. Extração focada apenas nos tributos solicitados ---
    csll = _extrair_valor(r"CSLL[\s\S]*?R\$\s*([\d.,]+)", texto)
    irpj = _extrair_valor(r"IRPJ[\s\S]*?R\$\s*([\d.,]+)", texto)
    ipi = _extrair_valor(r"IPI[\s\S]*?R\$\s*([\d.,]+)", texto)
    
    # --- 3. Montagem do dicionário de retorno ---
    dados = {
        "cnpj": cnpj,
        "periodo": periodo,
        "csll": csll,
        "irpj": irpj,
        "ipi": ipi,
    }
    
    return dados


# ==========================
# Declaração PGDAS (PDF)
# ==========================

def processar_pgdas_pdf(caminho_arquivo: Path) -> Dict[str, Any]:
    """
    Extrai dados de um PDF do PGDAS (Simples Nacional), incluindo o Fator R opcional.
    
    Retorna um DICIONÁRIO com os dados extraídos, compatível com a API.
    """
    texto = _ler_texto_pdf(caminho_arquivo)

    # --- 1. Extração dos dados do cabeçalho e resumo ---
    cnpj = _extrair_por_regex(r"CNPJ\s+Matriz:\s*([\d./-]+)", texto)
    periodo = _normalizar_periodo_mm_aaaa(_extrair_por_regex(r"Período\s+de\s+Apuração:\s*([\d/]+\s+a\s+[\d/]+)", texto))
    receita_bruta = _extrair_valor(r"Receita\s+Bruta\s+do\s+PA\s+\(RPA\)[\s\S]*?([\d.,]+)\s*$", texto)
    
    # --- 2. Extração de todos os tributos da tabela com uma única regex ---
    padrao_tributos = r"IRPJ\s+CSLL\s+COFINS\s+PIS/Pasep\s+INSS/CPP\s+ICMS\s+IPI\s+ISS\s+Total[\s\S]*?([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)"
    
    match_tributos = re.search(padrao_tributos, texto)
    
    if match_tributos:
        valores = match_tributos.groups()
        irpj, csll, cofins, pis_pasep, inss_cpp, icms, ipi, iss, total_tributos = map(_converter_valor, valores)
    else:
        irpj, csll, cofins, pis_pasep, inss_cpp, icms, ipi, iss, total_tributos = [None] * 9

    # --- 3. Extração opcional do Fator R ---
    fator_r_texto = _extrair_por_regex(r"Fator\s*R\s*:?\s*([\d.,%]+)", texto)
    fator_r: Optional[Decimal] = None
    if fator_r_texto:
        # Limpa a string (remove '%') antes de converter
        valor_sem_percentagem = fator_r_texto.replace("%", "").strip()
        fator_decimal = _converter_valor(valor_sem_percentagem)
        
        # Normaliza para um valor percentual (ex: 28.5 -> 0.285)
        if fator_decimal is not None:
            if Decimal(0) <= fator_decimal <= Decimal(100):
                fator_r = fator_decimal / Decimal(100)
            else: # Se for um valor já normalizado (ex: 0.285), mantém.
                fator_r = fator_decimal

    # --- 4. Montagem do dicionário de retorno ---
    dados = {
        "cnpj": cnpj,
        "periodo": periodo,
        "receita_bruta_pa": receita_bruta,
        "irpj": irpj,
        "csll": csll,
        "cofins": cofins,
        "pis_pasep": pis_pasep,
        "inss_cpp": inss_cpp,
        "icms": icms,
        "ipi": ipi,
        "iss": iss,
        "total_debitos_tributos": total_tributos,
        "fator_r": fator_r, # Campo adicionado
    }
    
    return dados


# ==========================
# Relatório de Saídas / Entradas (PDF/CSV/XLSX)
# ==========================

# CFOPs comumente não incidentes em faturamento (exemplo; ajuste conforme sua regra)
CFOPS_NAO_INCIDENTES_PADRAO: set[str] = {
    "5.949", "6.949",  # Outras saídas de mercadoria/serviço
    "5.201", "6.201",  # Devolução de venda
    "5.202", "6.202",  # Devolução de venda
    "5.556", "6.556",  # Remessa para conserto/beneficiamento
}


def _ler_tabela_arquivo(caminho: Path) -> pd.DataFrame:
    """Lê CSV/XLSX em DataFrame. Se PDF, tenta heurística de tabela a partir do texto."""
    _arquivo_existe(caminho)
    ext = caminho.suffix.lower()
    if ext in {".csv"}:
        return pd.read_csv(caminho)
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(caminho)
    if ext == ".parquet":
        return pd.read_parquet(caminho)

    # PDF: tenta parsear colunas básicas via regex linha a linha
    if ext == ".pdf":
        texto = _ler_texto_pdf(caminho)
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        # heurística: procura linhas contendo CFOP e UF e um valor (R$)
        registros: List[Dict[str, Any]] = []
        for l in linhas:
            m = re.search(r"CFOP\s*:?\s*([\d.]{4})", l, re.IGNORECASE)
            uf = _extrair_por_regex(r"\b(UF)\s*:?\s*([A-Z]{2})\b", l)
            valor = _extrair_valor(r"R?\$\s*([\d.,]+)", l)
            if m:
                registros.append({
                    "CFOP": m.group(1),
                    "UF": (uf or "").split()[-1] if uf else None,
                    "Valor": valor,
                    "Linha": l,
                })
        if registros:
            return pd.DataFrame(registros)
        # fallback vazio
        return pd.DataFrame()

    # Desconhecido
    raise ValueError(f"Extensão não suportada para leitura tabular: {ext}")


def _normalizar_colunas_mov(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas prováveis para um schema comum."""
    if df.empty:
        return df
    mapeamento = {
        # comuns
        "cnpj": "CNPJ",
        "empresa_cnpj": "CNPJ",
        "periodo": "Período",
        "competencia": "Período",
        "faturamento": "Faturamento",
        "valor_total": "Valor_Total",
        "valor": "Valor",
        "cfop": "CFOP",
        "uf": "UF",
        "estado": "UF",
    }
    # renomeia ignorando caixa
    renomear = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in mapeamento:
            renomear[c] = mapeamento[cl]
    df = df.rename(columns=renomear)
    return df


def processar_relatorio_saidas(caminho_arquivo: Path, cfops_nao_incidentes: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Lê relatório de saídas e retorna DataFrame com:
    [CNPJ, Período, Faturamento, CFOP, Incide_Faturamento (bool), UF]

    - Aceita CSV/XLSX/PDF (heurístico).
    - Define Incide_Faturamento=false para CFOPs na lista de não incidentes.
    """
    df = _ler_tabela_arquivo(caminho_arquivo)
    df = _normalizar_colunas_mov(df)

    # garante colunas
    for col in ["CNPJ", "Período", "Faturamento", "CFOP", "UF"]:
        if col not in df.columns:
            df[col] = None

    # limpa CFOP (ex.: 5949 -> 5.949)
    def fmt_cfop(x: Any) -> Optional[str]:
        if pd.isna(x):
            return None
        s = str(x)
        d = re.sub(r"[^0-9]", "", s)
        return f"{d[0]}.{d[1:]}" if len(d) == 4 else s

    df["CFOP"] = df["CFOP"].map(fmt_cfop)

    # normaliza período
    df["Período"] = df["Período"].map(_normalizar_periodo_mm_aaaa)

    # normaliza faturamento/valor
    if "Faturamento" in df.columns and df["Faturamento"].notna().any():
        df["Faturamento"] = df["Faturamento"].map(lambda v: _limpar_valor_monetario(str(v)) if pd.notna(v) else None)
    elif "Valor" in df.columns:
        df = df.rename(columns={"Valor": "Faturamento"})
        df["Faturamento"] = df["Faturamento"].map(lambda v: _limpar_valor_monetario(str(v)) if pd.notna(v) else None)
    else:
        df["Faturamento"] = None

    nao_inc = set(cfops_nao_incidentes or CFOPS_NAO_INCIDENTES_PADRAO)
    df["Incide_Faturamento"] = ~df["CFOP"].fillna("").isin(nao_inc)

    return df[["CNPJ", "Período", "Faturamento", "CFOP", "Incide_Faturamento", "UF"]]


def processar_relatorio_entradas(caminho_arquivo: Path) -> pd.DataFrame:
    """
    Lê relatório de entradas e retorna DataFrame com:
    [CNPJ, Período, Valor_Total_Entradas, CFOP, UF]
    """
    df = _ler_tabela_arquivo(caminho_arquivo)
    df = _normalizar_colunas_mov(df)

    for col in ["CNPJ", "Período", "Valor_Total_Entradas", "CFOP", "UF"]:
        if col not in df.columns:
            if col == "Valor_Total_Entradas" and "Valor_Total" in df.columns:
                df[col] = df["Valor_Total"]
            elif col == "Valor_Total_Entradas" and "Valor" in df.columns:
                df[col] = df["Valor"]
            else:
                df[col] = None

    # normalizações
    df["Período"] = df["Período"].map(_normalizar_periodo_mm_aaaa)

    def fmt_cfop(x: Any) -> Optional[str]:
        if pd.isna(x):
            return None
        s = str(x)
        d = re.sub(r"[^0-9]", "", s)
        return f"{d[0]}.{d[1:]}" if len(d) == 4 else s

    df["CFOP"] = df["CFOP"].map(fmt_cfop)
    df["Valor_Total_Entradas"] = df["Valor_Total_Entradas"].map(lambda v: _limpar_valor_monetario(str(v)) if pd.notna(v) else None)

    return df[["CNPJ", "Período", "Valor_Total_Entradas", "CFOP", "UF"]]
def processar_nfe_xml(caminho_arquivo: Path) -> Dict[str, Any]:
    """Lê um ficheiro XML de NFe e extrai os dados fiscais."""
    try:
        dados = ler_xml(caminho_arquivo)
        inf_nfe = dados.get('nfeProc', {}).get('NFe', {}).get('infNFe', {})
        if not inf_nfe:
            inf_nfe = dados.get('NFe', {}).get('infNFe', {})
        if not inf_nfe:
            raise ValueError("Estrutura de NFe inválida ou não encontrada no XML.")
        emitente = inf_nfe.get('emit', {})
        total = inf_nfe.get('total', {}).get('ICMSTot', {})
        produtos_extraidos = []
        lista_produtos_xml = inf_nfe.get('det', [])
        if not isinstance(lista_produtos_xml, list):
            lista_produtos_xml = [lista_produtos_xml]
        for item in lista_produtos_xml:
            produto_info = item.get('prod', {})
            produtos_extraidos.append({"cfop": produto_info.get('CFOP'), "ncm": produto_info.get('NCM')})
        valor_total_str = total.get('vNF')
        valor_total_decimal = Decimal(valor_total_str) if valor_total_str else None
        return {
            "cnpj_emitente": emitente.get('CNPJ'),
            "valor_total": valor_total_decimal,
            "produtos": produtos_extraidos
        }
    except Exception as e:
        raise ValueError(f"Não foi possível processar o ficheiro XML. Verifique o formato. Erro: {e}")




# ==========================
# Consolidação opcional
# ==========================

def consolidar_resultados(
    iss_df: Optional[pd.DataFrame] = None,
    efd_icms_df: Optional[pd.DataFrame] = None,
    efd_contrib_df: Optional[pd.DataFrame] = None,
    mit_df: Optional[pd.DataFrame] = None,
    pgdas_df: Optional[pd.DataFrame] = None,
    saidas_df: Optional[pd.DataFrame] = None,
    entradas_df: Optional[pd.DataFrame] = None,
) -> Dict[str, pd.DataFrame]:
    """Agrupa todos os DataFrames em um dicionário para facilitar export ou saving."""
    out: Dict[str, pd.DataFrame] = {}
    if iss_df is not None and not iss_df.empty:
        out["ISS"] = iss_df
    if efd_icms_df is not None and not efd_icms_df.empty:
        out["EFD_ICMS"] = efd_icms_df
    if efd_contrib_df is not None and not efd_contrib_df.empty:
        out["EFD_Contribuicoes"] = efd_contrib_df
    if mit_df is not None and not mit_df.empty:
        out["MIT"] = mit_df
    if pgdas_df is not None and not pgdas_df.empty:
        out["PGDAS"] = pgdas_df
    if saidas_df is not None and not saidas_df.empty:
        out["Relatorio_Saidas"] = saidas_df
    if entradas_df is not None and not entradas_df.empty:
        out["Relatorio_Entradas"] = entradas_df
    return out


# ==========================
# Utilitário: detecção simples por nome do arquivo
# ==========================

def detectar_e_processar(caminho_arquivo: Path) -> Dict[str, Any] | pd.DataFrame:
    """Roteia automaticamente com base no nome/ extensão do arquivo."""
    p = Path(caminho_arquivo)
    nome = p.name.lower()
    if nome.endswith(".xml") and ("nfe" in nome or "nota" in nome):
        return processar_nfe_xml(p)
    if nome.endswith(".pdf"):
        if "iss" in nome:
            return pdf_iss_para_dataframe(processar_iss_pdf(p))
        if "efd" in nome and "icms" in nome:
            return processar_efd_icms_pdf(p)
        if "efd" in nome and ("contrib" in nome or "contribu" in nome):
            return processar_efd_contribuicoes_pdf(p)
        if "mit" in nome:
            return processar_mit_pdf(p)
        if "pgdas" in nome:
            return processar_pgdas_pdf(p)
        if "saida" in nome or "saidas" in nome:
            return processar_relatorio_saidas(p)
        if "entrada" in nome or "entradas" in nome:
            return processar_relatorio_entradas(p)
    if p.suffix.lower() in {".csv", ".xlsx", ".xls", ".parquet"}:
        if "saida" in nome or "saidas" in nome:
            return processar_relatorio_saidas(p)
        if "entrada" in nome or "entradas" in nome:
            return processar_relatorio_entradas(p)
    raise ValueError("Tipo de arquivo não reconhecido para roteamento automático.")

# --- Funções de Conversão para DataFrame ---

def xml_para_dataframe(dados_extraidos: Dict[str, Any]) -> pd.DataFrame:
    """Converte os dados extraídos de um XML para um DataFrame do Pandas."""
    produtos = dados_extraidos.get("produtos", [])
    if not produtos:
        return pd.DataFrame()
    df = pd.DataFrame(produtos)
    df['cnpj_emitente'] = dados_extraidos.get("cnpj_emitente")
    df['valor_total_nota'] = dados_extraidos.get("valor_total")
    df = df.rename(columns={'cnpj_emitente': 'CNPJ_Emitente', 'valor_total_nota': 'Valor_Total_Nota', 'cfop': 'CFOP', 'ncm': 'NCM'})
    df = df[['CNPJ_Emitente', 'Valor_Total_Nota', 'CFOP', 'NCM']]
    colunas_obrigatorias = ['CNPJ_Emitente', 'Valor_Total_Nota']
    if df[colunas_obrigatorias].isnull().values.any():
        raise ValueError("Dados obrigatórios (CNPJ ou Valor Total) não encontrados no XML.")
    df['Valor_Total_Nota'] = pd.to_numeric(df['Valor_Total_Nota'], errors='coerce')
    df['CFOP'] = df['CFOP'].astype(str)
    df['NCM'] = df['NCM'].astype(str)
    return df

def pdf_para_dataframe_geral(dados_extraidos: Dict[str, Any], colunas_renomeadas: Dict[str, str]) -> pd.DataFrame:
    """
    Função genérica para converter um dicionário de dados extraídos de um PDF
    para um DataFrame de linha única, padronizando e validando.
    """
    if not dados_extraidos:
        return pd.DataFrame()

    df = pd.DataFrame([dados_extraidos])
    df = df.rename(columns=colunas_renomeadas)
    
    # Validação de dados obrigatórios (CNPJ é comum a todos)
    if 'CNPJ' not in df.columns or df['CNPJ'].isnull().all():
        raise ValueError("Dado obrigatório (CNPJ) não encontrado no documento.")
        
    return df
# --- DICIONÁRIO DE PROCESSADORES ATUALIZADO ---
# Garante que este dicionário está atualizado com as funções corretas que criámos.
PROCESSADORES = {
    "Encerramento ISS": processar_iss_pdf,
    "EFD ICMS": processar_efd_icms_pdf,
    "EFD Contribuições": processar_efd_contribuicoes_pdf,
    "MIT": processar_mit_pdf, # Nome da função que criámos
    "PGDAS": processar_pgdas_pdf,     # Nome da função que criámos
    "NFe": processar_nfe_xml,
    # As funções abaixo retornam DataFrames e precisam ser ajustadas para retornar dict
    # se quiseres que o salvamento automático funcione para elas.
    # "Relatório de Saídas": services_processamento.processar_relatorio_saidas,
    # "Relatório de Entradas": services_processamento.processar_relatorio_entradas,
}


__all__ = [
    "processar_nfe_xml",
    "processar_iss_pdf",
    "pdf_iss_para_dataframe",
    "processar_efd_icms_pdf",
    "processar_efd_contribuicoes_pdf",
    "processar_mit_pdf",
    "processar_pgdas_pdf",
    "processar_relatorio_saidas",
    "processar_relatorio_entradas",
    "consolidar_resultados",
    "detectar_e_processar",
]
