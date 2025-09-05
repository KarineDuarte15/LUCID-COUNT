# app/services/charts.py
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import uuid
from typing import List, Dict, Any
from plotly.subplots import make_subplots

CHARTS_DIR = Path("static/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# --- ALTERAÇÃO: Paleta de Cores Centralizada ---
COLOR_PAPER = '#0A192F'
COLOR_TEXT = '#CCD6F6'
COLOR_PRIMARY = '#D4AF37'
COLOR_PALETTE_PIE = ['#D4AF37', '#1E90FF', '#1EFF65', '#C70039', '#FF5733', '#DAF7A6', '#FFC300', '#581845']


def gerar_grafico_faturamento(dados: pd.DataFrame, cnpj: str) -> str:
    """ Gera um gráfico de barras do faturamento mensal com uma tabela de dados. """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.75, 0.25], specs=[[{"secondary_y": False}], [{"type": "table"}]]
    )

    # Adiciona o gráfico de barras
    fig.add_trace(go.Bar(
        x=dados['mes_ano'],
        y=dados['faturamento'],
        name='Faturamento',
        marker_color="#1EFF65",
        text=dados['faturamento_formatado'],
        textposition='outside',
    ), row=1, col=1)

    # Adiciona a tabela de dados
    fig.add_trace(go.Table(
        header=dict(values=['Ano', 'Mês', 'Faturamento'], fill_color='royalblue', align='center', font=dict(color='white', size=12)),
        cells=dict(values=[dados.ano, dados.mes, dados.faturamento_formatado], fill_color='lavender', align=['center', 'left', 'right'], font=dict(color='darkslategray', size=11))
    ), row=2, col=1)

    # Atualiza o layout geral
    fig.update_layout(
        height=800,
        title_text=f'Evolução do Faturamento Mensal - CNPJ: {cnpj}',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Faturamento (R$)", row=1, col=1)
    
    nome_arquivo = f"faturamento_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=1200, height=800, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_receita_crescimento(dados: pd.DataFrame, cnpj: str) -> str:
    """ Gera um gráfico combinado de Faturamento (barras) e Taxa de Crescimento (linha) com uma tabela de dados. """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.75, 0.25], specs=[[{"secondary_y": True}], [{"type": "table"}]]
    )
    fig.add_trace(go.Bar(x=dados['mes_ano'], y=dados['faturamento'], name='Faturamento', marker_color='#F28C28'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=dados['mes_ano'], y=dados['taxa_crescimento'], name='Taxa de Crescimento', mode='lines+markers', marker_color='#000000'), row=1, col=1, secondary_y=True)
    
    fig.add_trace(go.Table(
        header=dict(values=['Ano', 'Mês', 'Faturamento', 'Taxa de Crescimento'], fill_color='royalblue', align='center', font=dict(color='white', size=12)),
        cells=dict(values=[dados.ano, dados.mes, dados.faturamento_formatado, dados.crescimento_formatado], fill_color='lavender', align=['center', 'left', 'right', 'right'], font=dict(color='darkslategray', size=11))
    ), row=2, col=1)

    fig.update_layout(height=800, title_text=f'Faturamento e Taxa de Crescimento por Mês - CNPJ: {cnpj}', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Faturamento (R$)", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Crescimento (%)", secondary_y=True, row=1, col=1)

    nome_arquivo = f"receita_crescimento_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=1200, height=800, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_impostos_carga_tributaria(dados: pd.DataFrame, cnpj: str) -> str:
    """ Gera um gráfico combinado de Total de Impostos (barras) e Carga Tributária (linha) com tabela. """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.75, 0.25], specs=[[{"secondary_y": True}], [{"type": "table"}]]
    )
    fig.add_trace(go.Bar(x=dados['mes_ano'], y=dados['total_impostos'], name='Total Impostos', marker_color='#C70039'), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=dados['mes_ano'], y=dados['carga_tributaria'], name='Carga Tributária', mode='lines+markers', marker_color='#000000'), row=1, col=1, secondary_y=True)
    
    fig.add_trace(go.Table(
        header=dict(values=['Mês/Ano', 'Total de Impostos', 'Carga Tributária'], fill_color='royalblue', align='center', font=dict(color='white', size=12)),
        cells=dict(values=[dados.mes_ano, dados.impostos_formatado, dados.carga_formatado], fill_color='lavender', align=['center', 'right', 'right'], font=dict(color='darkslategray', size=11))
    ), row=2, col=1)

    fig.update_layout(height=800, title_text=f'Impostos e Carga Tributária por Mês - CNPJ: {cnpj}', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Impostos (R$)", secondary_y=False, row=1, col=1)
    fig.update_yaxes(title_text="Carga Tributária (%)", secondary_y=True, row=1, col=1)

    nome_arquivo = f"impostos_carga_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=1200, height=800, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_acumulado(dados: pd.DataFrame, cnpj: str) -> str:
    """ Gera um gráfico de linhas para Faturamento e Tributos Acumulados com tabela. """
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.75, 0.25], specs=[[{"secondary_y": False}], [{"type": "table"}]]
    )
    fig.add_trace(go.Scatter(x=dados['mes_ano'], y=dados['faturamento_acumulado'], name='Faturamento Acumulado', mode='lines+markers', line=dict(color='#1E90FF', width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=dados['mes_ano'], y=dados['impostos_acumulados'], name='Impostos Acumulados', mode='lines+markers', line=dict(color='#FF5733', width=3)), row=1, col=1)
    
    fig.add_trace(go.Table(
        header=dict(values=['Mês/Ano', 'Faturamento Acumulado', 'Impostos Acumulados'], fill_color='royalblue', align='center', font=dict(color='white', size=12)),
        cells=dict(values=[dados.mes_ano, dados.faturamento_acumulado_formatado, dados.impostos_acumulados_formatado], fill_color='lavender', align=['center', 'right', 'right'], font=dict(color='darkslategray', size=11))
    ), row=2, col=1)
    
    fig.update_layout(height=800, title_text=f'Faturamento e Impostos Acumulados no Exercício - CNPJ: {cnpj}', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Valor Acumulado (R$)", row=1, col=1)
    
    nome_arquivo = f"acumulado_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=1200, height=800, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_limite_faturamento(dados: dict, cnpj: str) -> str:
    """ Gera um gráfico de medidor para o limite de faturamento. """
    value = dados.get('rba', 0)
    limit = dados.get('limite', 1) # Evita divisão por zero
    percentage = (value / limit) * 100 if limit > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'prefix': "R$ ", 'valueformat': ',.2f'},
        title={'text': f"Faturamento Acumulado vs Limite ({percentage:.2f}%)", 'font': {'color': COLOR_TEXT, 'size': 16}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, limit], 'tickwidth': 1, 'tickcolor': "darkgrey"},
            'bar': {'color': COLOR_PRIMARY},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, limit * 0.5], 'color': '#2a5a3b'},
                {'range': [limit * 0.5, limit * 0.8], 'color': '#6e6114'},
                {'range': [limit * 0.8, limit], 'color': '#701c1c'}],
        }
    ))
    fig.update_layout(
        title_text=f'Limite de Faturamento - CNPJ: {cnpj}',
        paper_bgcolor=COLOR_PAPER,
        font={'color': COLOR_TEXT}
    )
    nome_arquivo = f"limite_faturamento_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=800, height=500, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_sublimite_receita(dados: dict, cnpj: str) -> str:
    """ Gera um gráfico de medidor (estilo rosca) para o sublimite de receita. """
    value = dados.get('rba', 0)
    sublimit = dados.get('sublimite', 1) # Evita divisão por zero
    percentage = (value / sublimit) * 100 if sublimit > 0 else 0

    fig = go.Figure(go.Indicator(
        mode = "number+gauge",
        gauge = {'shape': "angular",
                 'bar': {'color': COLOR_PRIMARY, 'thickness': 0.3},
                 'axis': {'range': [None, sublimit], 'visible': False},
                 'bgcolor': "rgba(0,0,0,0)",
                },
        number={'valueformat': '.2f', 'suffix': '%', 'font': {'size': 50, 'color': COLOR_PRIMARY}},
        value = percentage,
        domain = {'x': [0.1, 0.9], 'y': [0.1, 0.9]},
        title = {'text': f"Uso do Sublimite<br>R$ {value:,.2f} / R$ {sublimit:,.2f}", 'font': {'size': 20, 'color': COLOR_TEXT}}))

    fig.update_layout(
        title_text=f'Sublimite de Receita (ICMS/ISS) - CNPJ: {cnpj}',
        paper_bgcolor=COLOR_PAPER,
        font={'color': COLOR_TEXT},
        height=500
    )

    nome_arquivo = f"sublimite_receita_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=600, height=600, scale=2)
    return str(caminho_completo).replace('\\', '/')

def gerar_grafico_segregacao_tributos(dados: dict, cnpj: str) -> str:
    """ Gera um gráfico de rosca para a segregação de tributos. """
    labels = list(dados.keys())
    values = list(dados.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=.5,
        textinfo='percent+label',
        marker_colors=COLOR_PALETTE_PIE,
        pull=[0.02] * len(labels)
    )])
    
    fig.update_layout(
        title_text=f'Segregação dos Tributos no Período - CNPJ: {cnpj}',
        paper_bgcolor=COLOR_PAPER,
        plot_bgcolor=COLOR_PAPER,
        font={'color': COLOR_TEXT},
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    
    nome_arquivo = f"segregacao_tributos_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo
    fig.write_image(caminho_completo, width=800, height=800, scale=2)
    return str(caminho_completo).replace('\\', '/')