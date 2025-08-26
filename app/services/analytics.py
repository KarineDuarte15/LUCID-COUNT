# app/services/analytics.py
from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, Any

# Importamos as nossas funções de CRUD
from app.crud import dados_fiscais as crud_dados_fiscais

# Dicionário central que define as regras de negócio para os regimes tributários
GRUPOS_POR_REGIME = {
    "Simples Nacional": [
        "Encerramento ISS", 
        "PGDAS"
    ],
    "Lucro Presumido (Comércio/Indústria ou Comércio/Indústria e Serviços)": [
        "Encerramento ISS",
        "EFD ICMS",
        "EFD Contribuições",
        "MIT", 
        "Relatório de Saídas",
        "Relatório de Entradas"
    ],
    "Lucro Presumido (Serviços)": [
        "Encerramento ISS",
        "EFD Contribuições",
        "MIT",
        "Relatório de Entradas"
    ],
    "Lucro Real (Comércio/Indústria ou Comércio/Indústria e Serviços)": [
        "Encerramento ISS",
        "EFD Contribuições",
        "EFD ICMS",
        "Relatório de Saídas",
        "Relatório de Entradas"
    ],
    "Lucro Real (Serviços)": [
        "Encerramento ISS",
        "EFD Contribuições",
        "Relatório de Entradas"
    ]
}

def _get_documentos_relevantes(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date):
    """Função helper para buscar os documentos corretos com base no regime."""
    tipos_documento_relevantes = GRUPOS_POR_REGIME.get(regime)
    if not tipos_documento_relevantes:
        raise ValueError(f"O regime tributário '{regime}' não é válido ou não foi definido.")
    
    return crud_dados_fiscais.obter_dados_por_periodo(
        db, 
        cnpj=cnpj, 
        data_inicio=data_inicio, 
        data_fim=data_fim,
        tipos_documento=tipos_documento_relevantes
    )

def calcular_carga_tributaria(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal | None:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    if not registos:
        return None

    faturamento_total = Decimal(0)
    total_impostos = Decimal(0)

    # Lógica específica para Simples Nacional
    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        if not pgdas_reg:
            return None # PGDAS é essencial para este cálculo

        faturamento_total = pgdas_reg.valor_total or Decimal(0)
        if pgdas_reg.impostos:
            total_impostos = Decimal(pgdas_reg.impostos.get('total_debitos_tributos', 0))
    else:
        # A lógica anterior para outros regimes (pode ser refinada no futuro)
        faturamento_total = sum(reg.valor_total for reg in registos if reg.valor_total is not None)
        total_impostos = sum(Decimal(valor) for reg in registos if reg.impostos for valor in reg.impostos.values() if valor is not None and isinstance(valor, (str, int, float, Decimal)))

    if faturamento_total == 0:
        return Decimal(0)

    carga_tributaria = (total_impostos / faturamento_total) * 100
    return carga_tributaria.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_ticket_medio(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal | None:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    
    # --- INÍCIO DA DEPURAÇÃO ---
    print("\n--- DEPURAÇÃO: calcular_ticket_medio ---")
    print(f"Documentos encontrados para o período: {[reg.documento.tipo_documento for reg in registos]}")
    # --- FIM DA DEPURAÇÃO ---

    if not registos:
        return None

    faturamento_total = Decimal(0)
    numero_de_notas = 0

    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        iss_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'Encerramento ISS'), None)
        
        # --- MAIS DEPURAÇÃO ---
        print(f"PGDAS encontrado: {'Sim' if pgdas_reg else 'Não'}")
        print(f"Encerramento ISS encontrado: {'Sim' if iss_reg else 'Não'}")
        
        if not pgdas_reg or not iss_reg:
             print("Faltam documentos essenciais para o cálculo. A retornar null.")
             return None
        
        faturamento_total = pgdas_reg.valor_total or Decimal(0)
        if iss_reg.impostos:
            numero_de_notas = int(iss_reg.impostos.get('qtd_nfse_emitidas', 0))
        
        print(f"Faturamento Total para cálculo: {faturamento_total}")
        print(f"Número de Notas para cálculo: {numero_de_notas}")
        print("---------------------------------------\n")

    else:
        faturamento_total = sum(reg.valor_total for reg in registos if reg.valor_total is not None)
        numero_de_notas = len(registos)

    if numero_de_notas == 0:
        return Decimal(0)

    ticket_medio = faturamento_total / Decimal(numero_de_notas)
    return ticket_medio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_impostos_por_tipo(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Dict[str, str]:
    """
    Agrega o valor total para cada tipo de imposto e retorna um dicionário com valores formatados como strings.
    """
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    
    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        if pgdas_reg and pgdas_reg.impostos:
            # --- CORREÇÃO AQUI ---
            # Converte a string limpa da DB para Decimal e DEPOIS formata para string monetária
            impostos_finais = {
                k.upper(): _formatar_monetario(Decimal(v))
                for k, v in pgdas_reg.impostos.items()
                if v is not None
            }
            return impostos_finais
        else:
            return {}
    else:
        # Lógica para outros regimes (não testada, mas deve funcionar)
        impostos_agregados = defaultdict(Decimal)
        for reg in registos:
            if reg.impostos:
                for nome_imposto, valor_imposto in reg.impostos.items():
                    try:
                        impostos_agregados[nome_imposto] += Decimal(valor_imposto)
                    except (TypeError, InvalidOperation):
                        continue
        return {k.upper(): _formatar_monetario(v) for k, v in impostos_agregados.items()}



    
def extrair_receita_pgdas(impostos: dict) -> Decimal:
    """
    Extrai a receita correta do PGDAS.
    Dá prioridade à Receita Bruta do Período de Apuração (mensal).
    Se não existir, cai para RBA (que pode estar inflada).
    """
    receita = None

    # Receita do período de apuração (mensal)
    if "RECEITA_BRUTA_TOTAL" in impostos:
        receita = _converter_valor(impostos["RECEITA_BRUTA_TOTAL"])
    
    # Fallback: usa RBA (mas cuidado, é acumulado de 12 meses!)
    elif "RECEITA_BRUTA_ACUMULADA_RBA" in impostos:
        receita = _converter_valor(impostos["RECEITA_BRUTA_ACUMULADA_RBA"])

    return receita or Decimal(0)

#_________________________________________________________________

# -----------------------------------------------------------------
# --- ALTERAÇÃO 1: FUNÇÃO _converter_valor CORRIGIDA E SIMPLIFICADA ---
# -----------------------------------------------------------------
def _converter_valor(valor_str: Any) -> Decimal | None:
    """Converte uma string de valor (ex: 'R$ 1.234,56') para um objeto Decimal."""
    if valor_str is None:
        return None
    try:
        # Lógica segura: remove "R$", espaços, DEPOIS os pontos de milhar,
        # e finalmente troca a vírgula decimal por ponto.
        limpo = str(valor_str).replace("R$", "").strip().replace(".", "").replace(",", ".")
        return Decimal(limpo)
    except (TypeError, InvalidOperation):
        return None
# -----------------------------------------------------------------

def _formatar_monetario(valor: Decimal | None) -> str:
    """Formata um Decimal para a string R$ 1.234,56"""
    if valor is None: return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _formatar_percentual(valor: Decimal | None) -> str:
    """Formata um Decimal para a string 11.48%"""
    if valor is None: return "N/A"
    return f"{valor:.2f}%"

def _get_documentos_relevantes(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date):
    tipos_documento_relevantes = GRUPOS_POR_REGIME.get(regime)
    if not tipos_documento_relevantes:
        raise ValueError(f"O regime tributário '{regime}' não é válido.")
    return crud_dados_fiscais.obter_dados_por_periodo(
        db, cnpj=cnpj, data_inicio=data_inicio, data_fim=data_fim, tipos_documento=tipos_documento_relevantes
    )


def calcular_impostos_por_tipo(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Dict[str, str]:
    """
    Agrega o valor total para cada tipo de imposto e retorna um dicionário com valores formatados.
    """
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    
    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        if pgdas_reg and pgdas_reg.impostos:
            impostos_finais = {
                k.upper(): _formatar_monetario(Decimal(v))
                for k, v in pgdas_reg.impostos.items()
                if v is not None
            }
            return impostos_finais
        else:
            return {}
    else:
        # Lógica para outros regimes
        impostos_agregados = defaultdict(Decimal)
        for reg in registos:
            if reg.impostos:
                for nome_imposto, valor_imposto in reg.impostos.items():
                    impostos_agregados[nome_imposto] += _converter_valor(valor_imposto) or Decimal(0)
        
        # -----------------------------------------------------------------
        # --- ALTERAÇÃO 2: CHAMADA DA FUNÇÃO DE FORMATAÇÃO CORRETA ---
        # -----------------------------------------------------------------
        impostos_formatados = {
            k.upper(): _formatar_monetario(v) for k, v in impostos_agregados.items()
        }
        return impostos_formatados
# -----------------------------------------------------------------




# Função para calcular o crescimento do faturamento
def calcular_crescimento_faturamento(db: Session, *, cnpj: str, regime: str, data_inicio_atual: date, data_fim_atual: date) -> Decimal | None:
    
    def _get_faturamento_do_periodo(data_inicio, data_fim):
        registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
        if not registos:
            return None
        
        if regime == "Simples Nacional":
            pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
            return pgdas_reg.valor_total if pgdas_reg else None
        else:
            return sum(reg.valor_total for reg in registos if reg.valor_total is not None)

    faturamento_atual = _get_faturamento_do_periodo(data_inicio_atual, data_fim_atual)
    if faturamento_atual is None:
        return None

    duracao_periodo = data_fim_atual - data_inicio_atual
    data_fim_anterior = data_inicio_atual - timedelta(days=1)
    data_inicio_anterior = data_fim_anterior - duracao_periodo
    
    faturamento_anterior = _get_faturamento_do_periodo(data_inicio_anterior, data_fim_anterior)
    if faturamento_anterior is None or faturamento_anterior == 0:
        return None

    crescimento = ((faturamento_atual - faturamento_anterior) / faturamento_anterior) * 100
    return crescimento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)






#------------------------------------ novas KPIs ------------------------------------

def gerar_relatorio_simples_nacional(db: Session, *, cnpj: str, data_competencia: date) -> Dict[str, Any]:
    """
    Gera um relatório analítico completo para o regime Simples Nacional para um mês de competência.
    """

    # --- 1. BUSCAR DADOS DO PERÍODO ATUAL ---
    data_inicio_atual = data_competencia.replace(day=1)
    
    # --- ALTERAÇÃO: Lógica mais robusta para encontrar o último dia de qualquer mês ---
    proximo_mes_primeiro_dia = (data_inicio_atual.replace(day=28) + timedelta(days=4)).replace(day=1)
    data_fim_atual = proximo_mes_primeiro_dia - timedelta(days=1)

    registos_atuais = _get_documentos_relevantes(
        db, cnpj=cnpj, regime="Simples Nacional",
        data_inicio=data_inicio_atual, data_fim=data_fim_atual
    )

    pgdas_atual = next((reg for reg in registos_atuais if reg.documento.tipo_documento == 'PGDAS'), None)
    iss_atual = next((reg for reg in registos_atuais if reg.documento.tipo_documento == 'Encerramento ISS'), None)

    if not pgdas_atual:
        return {"erro": "Documento PGDAS não encontrado para o período de competência."}

    impostos_pgdas = pgdas_atual.impostos or {}
    
    # --- 2. EXTRAIR VALORES BASE ---
    receita_bruta_atual = pgdas_atual.valor_total or Decimal(0)
    total_impostos_atual = _converter_valor(impostos_pgdas.get("total_debitos_tributos")) or Decimal(0)

    # --- 3. CÁLCULO DOS KPIs ---

    # Carga Tributária
    carga_tributaria = (total_impostos_atual / receita_bruta_atual) * 100 if receita_bruta_atual > 0 else Decimal(0)

    # Ticket Médio
    numero_de_notas = 0
    if iss_atual and iss_atual.impostos:
        numero_de_notas = int(iss_atual.impostos.get('qtd_nfse_emitidas', 0))
    ticket_medio = receita_bruta_atual / Decimal(numero_de_notas) if numero_de_notas > 0 else Decimal(0)

    # Crescimento do Faturamento
    data_fim_anterior = data_inicio_atual - timedelta(days=1)
    data_inicio_anterior = data_fim_anterior.replace(day=1)
    
    registos_anteriores = _get_documentos_relevantes(
        db, cnpj=cnpj, regime="Simples Nacional",
        data_inicio=data_inicio_anterior, data_fim=data_fim_anterior
    )
    pgdas_anterior = next((reg for reg in registos_anteriores if reg.documento.tipo_documento == 'PGDAS'), None)
    
    crescimento_faturamento = None
    if pgdas_anterior and pgdas_anterior.valor_total and pgdas_anterior.valor_total > 0:
        faturamento_anterior = pgdas_anterior.valor_total
        crescimento = ((receita_bruta_atual - faturamento_anterior) / faturamento_anterior) * 100
        crescimento_faturamento = crescimento

    # Segregação dos Tributos
    TRIBUTOS_VALIDOS = {"irpj", "csll", "cofins", "pis_pasep", "inss_cpp", "icms", "ipi", "iss"}
    segregacao_tributos = {}
    if total_impostos_atual > 0:
        # --- ALTERAÇÃO: Garante que a soma para o percentual é feita apenas com os tributos válidos ---
        soma_tributos_individuais = sum(_converter_valor(v) or Decimal(0) for k, v in impostos_pgdas.items() if k.lower() in TRIBUTOS_VALIDOS)
        if soma_tributos_individuais > 0:
            for imposto, valor in impostos_pgdas.items():
                if imposto.lower() in TRIBUTOS_VALIDOS:
                    valor_decimal = _converter_valor(valor)
                    if valor_decimal is not None:
                        percentual = (valor_decimal / soma_tributos_individuais) * 100
                        # --- ALTERAÇÃO: Usa a função de formatação para manter a consistência ---
                        segregacao_tributos[imposto.upper()] = _formatar_percentual(percentual)


    # --- 4. RELATÓRIO FINAL ---
    # --- ALTERAÇÃO: Centralização da formatação e remoção de duplicados ---
    relatorio = {
        "Receita Bruta e Taxa de Crescimento": {
            "Receita Bruta Total": _formatar_monetario(receita_bruta_atual),
            "Taxa de Crescimento da Receita": _formatar_percentual(crescimento_faturamento)
        },
        "Total de Impostos e Carga Tributária": {
            "Simples Nacional (Total Impostos)": _formatar_monetario(total_impostos_atual),
            "Carga Tributária Total": _formatar_percentual(carga_tributaria)
        },
        "Ticket Médio": _formatar_monetario(ticket_medio),
        "Segregação dos Tributos": segregacao_tributos,
        # Adicione os outros grupos de KPIs (Acumulados, Limites, Variações) aqui quando a lógica estiver pronta.
    }

    return relatorio
def validar_documentos_simples(pgdas: Any, encerramento_iss: Any) -> Dict[str, Any]:
    """
    Valida os documentos do Simples Nacional (PGDASD e Encerramento ISS).
    Retorna um dicionário com status e lista de avisos/erros.
    """

    avisos = []

    # --- 1. Receita Bruta ---
    receita_pgdas = _converter_valor(pgdas.valor_total) or Decimal(0)
    receita_iss = Decimal(0)
    if encerramento_iss and encerramento_iss.impostos:
        receita_iss = _converter_valor(encerramento_iss.impostos.get("valor_total_servicos")) or Decimal(0)

    if receita_pgdas != receita_iss and receita_iss > 0:
        avisos.append(f"Inconsistência: Receita Bruta PGDAS (R$ {receita_pgdas:,.2f}) "
                      f"≠ Receita Encerramento ISS (R$ {receita_iss:,.2f})")

    # --- 2. Tributos ---
    impostos = pgdas.impostos or {}
    total_impostos = _converter_valor(impostos.get("total_debitos_tributos")) or Decimal(0)

    TRIBUTOS_VALIDOS = {"irpj", "csll", "cofins", "pis_pasep", "inss_cpp", "icms", "ipi", "iss"}
    soma_individual = sum(
        _converter_valor(impostos.get(t)) or Decimal(0) for t in TRIBUTOS_VALIDOS if t in impostos
    )

    if soma_individual != total_impostos:
        avisos.append(f"Inconsistência: Soma dos tributos ({soma_individual:,.2f}) "
                      f"≠ Total de débitos ({total_impostos:,.2f})")

    # --- 3. NFSe (Ticket Médio) ---
    qtd_nfse = 0
    if encerramento_iss and encerramento_iss.impostos:
        qtd_nfse = encerramento_iss.impostos.get("qtd_nfse_emitidas") or 0

    if qtd_nfse == 0:
        avisos.append("Atenção: Nenhuma NFSe encontrada no Encerramento ISS (ticket médio pode ficar incorreto).")

    # --- 4. Limites ---
    limite_faturamento = _converter_valor(impostos.get("limite_receita_bruta"))
    sublimite_receita = _converter_valor(impostos.get("sublimite_receita"))

    if not limite_faturamento:
        avisos.append("Limite de faturamento não informado no PGDASD.")
    if not sublimite_receita:
        avisos.append("Sublimite de receita (ICMS/ISS) não informado no PGDASD.")

    # --- 5. Resultado ---
    return {
        "status": "OK" if not avisos else "ATENÇÃO",
        "avisos": avisos
    }