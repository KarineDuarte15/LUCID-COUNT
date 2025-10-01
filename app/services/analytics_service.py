# app/services/analytics_service.py
from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, Any, Tuple, Optional
import pandas as pd


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

def preparar_dados_tributos_lp(db: Session, cnpj: str, data_inicio: date, data_fim: date) -> Optional[pd.DataFrame]:
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime="Lucro Presumido (Serviços)", data_inicio=data_inicio, data_fim=data_fim)
    if not registos:
        return None

    dados_mensais = defaultdict(lambda: {'Devido': Decimal(0), 'Retido': Decimal(0)})
    
    for reg in registos:
        if reg.data_competencia and reg.impostos:
            mes = reg.data_competencia.strftime('%Y-%m')
            if reg.documento.tipo_documento == 'Encerramento ISS':
                dados_mensais[mes]['Retido'] += _converter_valor(reg.impostos.get('iss_retido')) or Decimal(0)
                dados_mensais[mes]['Devido'] += _converter_valor(reg.impostos.get('iss_devido')) or Decimal(0)
            elif reg.documento.tipo_documento == 'MIT':
                dados_mensais[mes]['Devido'] += _converter_valor(reg.impostos.get('csll')) or Decimal(0)
                dados_mensais[mes]['Devido'] += _converter_valor(reg.impostos.get('irpj')) or Decimal(0)
                dados_mensais[mes]['Devido'] += _converter_valor(reg.impostos.get('ipi')) or Decimal(0)

    lista_para_df = []
    for mes, valores in dados_mensais.items():
        total_mes = valores['Devido'] + valores['Retido']
        if total_mes > 0:
            lista_para_df.append({
                'Mês': mes,
                'Tributo': 'Devido',
                'Valor': valores['Devido'],
                'Percentual': (valores['Devido'] / total_mes) * 100
            })
            lista_para_df.append({
                'Mês': mes,
                'Tributo': 'Retido',
                'Valor': valores['Retido'],
                'Percentual': (valores['Retido'] / total_mes) * 100
            })

    if not lista_para_df:
        return None

    return pd.DataFrame(lista_para_df)


#------------------------------------ KPIs ------------------------------------ 
#        FUNÇÕES PRINCIPAIS PARA CÁLCULO DAS KPIs
# -----------------------------------------------------------------

#-----------------------------------------------------------------  
# Função para calcular a carga tributária
#-----------------------------------------------------------------

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
        return Decimal("0.00")

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

#-----------------------------------------------------------------
# Função para projetar a carga tributária para os próximos 3 meses  
#-----------------------------------------------------------------

def projetar_carga_tributaria(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Dict[str, str]:
    """
    Calcula a carga tributária atual e projeta para os próximos 3 meses,
    adicionando o IRPJ ao faturamento de cada mês projetado.
    """
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    faturamento_total, total_impostos, _ = _get_faturamento_e_impostos_por_regime(registos, regime)

    # Encontra o valor do IRPJ nos impostos do período
    irpj = Decimal(0)
    for reg in registos:
        if reg.impostos:
            valor_irpj_str = reg.impostos.get('irpj')
            if valor_irpj_str:
                irpj += _converter_valor(valor_irpj_str) or Decimal(0)
    
    # Se o faturamento for zero, não há como projetar
    if faturamento_total == 0:
        return {"Mes_Atual": "0.00%"}

    # Projeção
    projecao = {}
    faturamento_projetado = faturamento_total
    
    # Mês Atual
    carga_atual = (total_impostos / faturamento_total) * 100
    projecao["Mes_Atual"] = _formatar_percentual(carga_atual)

    # Próximos 3 meses
    for i in range(1, 4):
        # A cada mês, o faturamento acumulado aumenta pelo valor do IRPJ pago
        faturamento_projetado += irpj
        carga_projetada = (total_impostos / faturamento_projetado) * 100
        projecao[f"Mes_{i}"] = _formatar_percentual(carga_projetada)

    return projecao


#_-----------------------------------------------------------------
# KPIs para gerar relatório analítico completo do Lucro Presumido Serviços
#-----------------------------------------------------------------
def calcular_peso_entradas_sobre_receita(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal | None:
    """
    Calcula o peso das entradas sobre a receita/faturamento total do período.
    Fórmula: PEnt = Entradas / Receita/Faturamento
    """
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
    
    faturamento_total, _, _ = _get_faturamento_e_impostos_por_regime(registos, regime)
    
    entradas_reg = next((reg for reg in registos if reg.documento.tipo_documento == 'Relatório de Entradas'), None)
    
    if not entradas_reg or faturamento_total == 0:
        return Decimal(0)
        
    total_entradas = entradas_reg.valor_total or Decimal(0)
    
    peso_entradas = (total_entradas / faturamento_total) * 100
    return peso_entradas.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_variacao_tributos_mensal(db: Session, *, cnpj: str, regime: str, data_inicio_atual: date, data_fim_atual: date) -> Decimal | None:
    """
    Calcula a variação percentual do total de tributos em relação ao mês anterior.
    Fórmula: VaT = (Tributos Mês Atual / Tributos Mês Anterior) - 1
    """
    def _get_tributos_do_periodo(data_inicio, data_fim):
        registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=data_inicio, data_fim=data_fim)
        _, total_tributos, _ = _get_faturamento_e_impostos_por_regime(registos, regime)
        return total_tributos

    tributos_atuais = _get_tributos_do_periodo(data_inicio_atual, data_fim_atual)

    # Calcula o período anterior
    data_fim_anterior = data_inicio_atual - timedelta(days=1)
    data_inicio_anterior = data_fim_anterior.replace(day=1)
    
    tributos_anteriores = _get_tributos_do_periodo(data_inicio_anterior, data_fim_anterior)

    if tributos_anteriores is None or tributos_anteriores == 0:
        return None # Evita divisão por zero e retorna None se não houver dados anteriores

    variacao = ((tributos_atuais / tributos_anteriores) - 1) * 100
    return variacao.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calcular_faturamento_no_exercicio(db: Session, *, cnpj: str, regime: str, data_inicio: date, data_fim: date) -> Decimal:
    """
    Soma o faturamento total do início do ano fiscal até a data_fim.
    """
    ano_corrente = data_fim.year
    inicio_ano = date(ano_corrente, 1, 1)
    
    registos = _get_documentos_relevantes(db, cnpj=cnpj, regime=regime, data_inicio=inicio_ano, data_fim=data_fim)
    faturamento_total, _, _ = _get_faturamento_e_impostos_por_regime(registos, regime)
    
    return faturamento_total

def calcular_limite_faturamento_lp(faturamento_exercicio: Decimal) -> Decimal:
    """
    Calcula o percentual de uso do limite de faturamento para Lucro Presumido.
    Fórmula: Faturamento no Exercício / 78.000.000,00
    """
    limite = Decimal("78000000.00")
    if faturamento_exercicio is None or faturamento_exercicio == 0:
        return Decimal(0)
    
    percentual_uso = (faturamento_exercicio / limite) * 100
    return percentual_uso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

#-----------------------------------------------------------------
# KPIs para gerar relatório analítico completo do Lucro Presumido serviços
#-----------------------------------------------------------------
def gerar_relatorio_lucro_presumido_servicos(db: Session, *, cnpj: str, data_competencia: date) -> Dict[str, Any]:
    """
    Gera um relatório analítico completo para o regime Lucro Presumido - Serviços.
    """
    regime = "Lucro Presumido (Serviços)"
    
    # --- 1. DEFINIR PERÍODOS ---
    data_inicio_atual = data_competencia.replace(day=1)
    proximo_mes_primeiro_dia = (data_inicio_atual.replace(day=28) + timedelta(days=4)).replace(day=1)
    data_fim_atual = proximo_mes_primeiro_dia - timedelta(days=1)

    # --- 2. CÁLCULO DOS KPIs ---
    
    # KPIs Mensais
    crescimento_receita = calcular_crescimento_faturamento(
        db, cnpj=cnpj, regime=regime, data_inicio_atual=data_inicio_atual, data_fim_atual=data_fim_atual
    )
    carga_tributaria = calcular_carga_tributaria(
        db, cnpj=cnpj, regime=regime, data_inicio=data_inicio_atual, data_fim=data_fim_atual
    )
    peso_entradas = calcular_peso_entradas_sobre_receita(
        db, cnpj=cnpj, regime=regime, data_inicio=data_inicio_atual, data_fim=data_fim_atual
    )
    variacao_tributos = calcular_variacao_tributos_mensal(
        db, cnpj=cnpj, regime=regime, data_inicio_atual=data_inicio_atual, data_fim_atual=data_fim_atual
    )
    impostos_por_tipo = calcular_impostos_por_tipo(
        db, cnpj=cnpj, regime=regime, data_inicio=data_inicio_atual, data_fim=data_fim_atual
    )

    # KPIs Anuais/Exercício
    faturamento_exercicio = calcular_faturamento_no_exercicio(
        db, cnpj=cnpj, regime=regime, data_inicio=data_inicio_atual, data_fim=data_fim_atual
    )
    limite_faturamento_percentual = calcular_limite_faturamento_lp(faturamento_exercicio)

    # --- 3. MONTAGEM DO RELATÓRIO ---
    relatorio = {
        "Taxa de Crescimento da Receita (Mês)": _formatar_percentual(crescimento_receita),
        "Carga Tributária (Mês)": _formatar_percentual(carga_tributaria),
        "Peso das Entradas sobre a Receita (Mês)": _formatar_percentual(peso_entradas),
        "Variação dos Tributos (Mês)": _formatar_percentual(variacao_tributos),
        "Total de Faturamento no Período (Exercício)": _formatar_monetario(faturamento_exercicio),
        "Segregação dos Tributos (Mês)": impostos_por_tipo,
        "Limite de Faturamento (Exercício)": {
            "Valor Acumulado": _formatar_monetario(faturamento_exercicio),
            "Percentual Atingido": _formatar_percentual(limite_faturamento_percentual)
        }
    }

    return relatorio

#-----------------------------------------------------------------
# Funções para preparar dados para gráficos
#-----------------------------------------------------------------

def preparar_dados_para_graficos(db: Session, cnpj: str, data_inicio: date, data_fim: date) -> Optional[pd.DataFrame]:
    """
    Busca dados fiscais de PGDAS no período, calcula métricas e retorna um DataFrame.
    """
    # 1. Busca os dados relevantes (apenas PGDAS para estes gráficos)
    registos = crud_dados_fiscais.obter_dados_por_periodo(
        db,
        cnpj=cnpj,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipos_documento=["PGDAS"]
    )

    if not registos:
        return None

    # 2. Extrai os dados para uma lista de dicionários
    dados_grafico = []
    for reg in registos:
        impostos = reg.impostos or {}
        dados_grafico.append({
            'data_competencia': reg.data_competencia,
            'faturamento': reg.valor_total or Decimal(0),
            'total_impostos': _converter_valor(impostos.get("total_debitos_tributos")) or Decimal(0)
        })

    if not dados_grafico:
        return None

    # 3. Converte para DataFrame e ordena por data
    df = pd.DataFrame(dados_grafico)
    df = df.sort_values(by='data_competencia').reset_index(drop=True)

    # 4. Cálculos para os gráficos
    df['mes_ano'] = df['data_competencia'].dt.strftime('%b/%Y')
    df['ano'] = df['data_competencia'].dt.strftime('%Y')
    df['mes'] = df['data_competencia'].dt.strftime('%B')
    
    # Formatações para exibição
    df['faturamento_formatado'] = df['faturamento'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df['impostos_formatado'] = df['total_impostos'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Cálculo da Carga Tributária
    df['carga_tributaria'] = (df['total_impostos'] / df['faturamento']) * 100
    df['carga_formatado'] = df['carga_tributaria'].apply(lambda x: f"{x:.2f}%")

    # Cálculo da Taxa de Crescimento
    df['taxa_crescimento'] = df['faturamento'].pct_change() * 100
    df['crescimento_formatado'] = df['taxa_crescimento'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")

    # Cálculo dos valores acumulados
    df['faturamento_acumulado'] = df['faturamento'].cumsum()
    df['impostos_acumulados'] = df['total_impostos'].cumsum()
    df['faturamento_acumulado_formatado'] = df['faturamento_acumulado'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df['impostos_acumulados_formatado'] = df['impostos_acumulados'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    return df

def preparar_dados_para_kpis_visuais(db: Session, cnpj: str, data_inicio: date, data_fim: date) -> Optional[Dict[str, Any]]:
    """
    Busca o PGDAS mais recente no período e prepara os dados para os gráficos
    de medidor (gauge) e rosca (pie).
    """
    registos = crud_dados_fiscais.obter_dados_por_periodo(
        db,
        cnpj=cnpj,
        data_inicio=data_inicio,
        data_fim=data_fim,
        tipos_documento=["PGDAS"]
    )

    if not registos:
        return None

    # Pega o último registro do período para os KPIs
    ultimo_reg = max(registos, key=lambda r: r.data_competencia)
    impostos = ultimo_reg.impostos or {}

    # Dados para o gráfico de Medidor (Limite de Faturamento)
    dados_medidor = {
        "rba": _converter_valor(impostos.get("receita_bruta_acumulada_rba")),
        "limite": _converter_valor(impostos.get("limite_faturamento")),
        "sublimite": _converter_valor(impostos.get("sublimite_receita"))
    }

    # Dados para o gráfico de Rosca (Segregação de Tributos)
    tributos_rosca = {
        "IRPJ": _converter_valor(impostos.get("irpj")),
        "CSLL": _converter_valor(impostos.get("csll")),
        "COFINS": _converter_valor(impostos.get("cofins")),
        "PIS_PASEP": _converter_valor(impostos.get("pis_pasep")),
        "INSS_CPP": _converter_valor(impostos.get("inss_cpp")),
        "IPI": _converter_valor(impostos.get("ipi")),
        "ICMS": _converter_valor(impostos.get("icms")),
        "ISS": _converter_valor(impostos.get("iss")),
    }
    
    # Filtra apenas os tributos que têm valor
    dados_rosca = {k: v for k, v in tributos_rosca.items() if v is not None and v > 0}

    return {
        "medidor": dados_medidor,
        "rosca": dados_rosca
    }