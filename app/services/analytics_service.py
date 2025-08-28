# app/services/analytics_service.py
from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, Any, Tuple

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

# --- Funções Auxiliares (Helpers) ---

# -----------------------------------------------------------------
# --- ALTERAÇÃO 1: FUNÇÃO _converter_valor CORRIGIDA E SIMPLIFICADA ---
# -----------------------------------------------------------------
def _converter_valor(valor_str: Any) -> Decimal | None:
    """Converte uma string de valor para um objeto Decimal de forma segura."""
    if valor_str is None:
        return None
    try:
        s = str(valor_str).replace("R$", "").strip()
        # Se a string contém vírgula, assume-se formato brasileiro (ex: 1.234,56)
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        # Se não há vírgula, o ponto (se existir) é tratado como decimal padrão
        return Decimal(s)
    except (TypeError, InvalidOperation):
        return None

    
def _formatar_monetario(valor: Decimal | None) -> str:
    """Formata um Decimal para a string R$ 1.234,56"""
    if valor is None: return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _formatar_percentual(valor: Decimal | None) -> str:
    """Formata um Decimal para a string 11.48%"""
    if valor is None: return "N/A"
    return f"{valor:.2f}%"
# -----------------------------------------------------------------
#        FUNÇÃO AUXILIAR PARA PEGAR OS DOCUMENTOS RELEVANTES
# -----------------------------------------------------------------
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
# -----------------------------------------------------------------
#        FUNÇÃO AUXILIAR PARA CALCULAR FATURAMENTO E IMPOSTOS   
# -----------------------------------------------------------------
def _get_faturamento_e_impostos_por_regime(registos: list, regime: str) -> Tuple[Decimal, Decimal, int]:
    """
    Centraliza a lógica para extrair faturamento, total de impostos e número de notas
    com base no regime tributário.
    """
    faturamento_total = Decimal(0)
    total_impostos = Decimal(0)
    numero_de_notas = 0

    if not registos:
        return faturamento_total, total_impostos, numero_de_notas

    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        iss_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'Encerramento ISS'), None)
        
        if pgdas_reg:
            faturamento_total = pgdas_reg.valor_total or Decimal(0)
            if pgdas_reg.impostos:
                total_impostos = _converter_valor(pgdas_reg.impostos.get('total_debitos_tributos')) or Decimal(0)
        
        if iss_reg and iss_reg.impostos:
            numero_de_notas = int(iss_reg.impostos.get('qtd_nfse_emitidas', 0))
       
# -----------------------------------------------------------------
#--------------- Lógica para Lucro Presumido e Lucro Real----------
# -----------------------------------------------------------------

    else: 
        impostos_agregados = defaultdict(Decimal)
        
        for reg in registos:
            faturamento_total += reg.valor_total or Decimal(0)
            if reg.documento.tipo_documento == 'Encerramento ISS' and reg.impostos:
                 numero_de_notas += int(reg.impostos.get('qtd_nfse_emitidas', 0))

            if reg.impostos:
                for nome_imposto, valor_imposto in reg.impostos.items():
                    impostos_agregados[nome_imposto] += _converter_valor(valor_imposto) or Decimal(0)
        
        total_impostos = sum(impostos_agregados.values())

    return faturamento_total, total_impostos, numero_de_notas


#------------------------------------ KPIs ------------------------------------ 
#        FUNÇÕES PRINCIPAIS PARA CÁLCULO DAS KPIs
# -----------------------------------------------------------------

def calcular_carga_tributaria(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal | None:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    faturamento_total, total_impostos, _ = _get_faturamento_e_impostos_por_regime(registos, regime)

    if faturamento_total == 0:
        return Decimal(0)

    carga_tributaria = (total_impostos / faturamento_total) * 100
    return carga_tributaria.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
#-----------------------------------------------------------------
# Função para calcular o ticket médio
#-----------------------------------------------------------------

def calcular_ticket_medio(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal | None:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    faturamento_total, _, numero_de_notas = _get_faturamento_e_impostos_por_regime(registos, regime)

    if numero_de_notas == 0:
        return Decimal(0)

    ticket_medio = faturamento_total / Decimal(numero_de_notas)
    return ticket_medio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#-----------------------------------------------------------------
# Função para calcular o crescimento do faturamento 
#-----------------------------------------------------------------
def calcular_crescimento_faturamento(db: Session, *, cnpj: str, regime: str, data_inicio_atual: date, data_fim_atual: date) -> Decimal | None:
    
    def _get_faturamento_do_periodo(data_inicio, data_fim):
        registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
        faturamento, _, _ = _get_faturamento_e_impostos_por_regime(registos, regime)
        return faturamento

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


#-----------------------------------------------------------------
# Função para calcular impostos por tipo
#-----------------------------------------------------------------

def calcular_impostos_por_tipo(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Dict[str, str]:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    impostos_agregados = defaultdict(Decimal)

    if regime == "Simples Nacional":
        pgdas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'PGDAS'), None)
        iss_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'Encerramento ISS'), None)
        
        if pgdas_reg:
            # Adiciona os impostos do PGDAS
            if pgdas_reg.impostos:
                for k, v in pgdas_reg.impostos.items():
                    impostos_agregados[k] = _converter_valor(v) or Decimal(0)
            # Adiciona o faturamento total do PGDAS
            impostos_agregados['faturamento_total'] = pgdas_reg.valor_total or Decimal(0)
        
        if iss_reg and iss_reg.impostos:
            # Adiciona a quantidade de notas do Encerramento ISS
            impostos_agregados['qtd_nfse_emitidas'] = Decimal(iss_reg.impostos.get('qtd_nfse_emitidas', 0))

    else:
        # A lógica para outros regimes permanece a mesma
        for reg in registos:
            if reg.impostos:
                for nome_imposto, valor_imposto in reg.impostos.items():
                    impostos_agregados[nome_imposto] += _converter_valor(valor_imposto) or Decimal(0)
    
    # --- LÓGICA DE FORMATAÇÃO ---
    impostos_formatados = {}
    for k, v in impostos_agregados.items():
        if k == 'qtd_nfse_emitidas':
            impostos_formatados[k.upper()] = int(v) # Formata como inteiro
        else:
            impostos_formatados[k.upper()] = _formatar_monetario(v) # Formata como moeda

    return impostos_formatados

#-----------------------------------------------------------------
# Função para validar documentos do Simples Nacional    
#-----------------------------------------------------------------
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

#-----------------------------------------------------------------
# Função para gerar relatório analítico completo do Simples Nacional    
#-----------------------------------------------------------------

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
