import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
import uuid
from typing import List, Dict, Any

# Define o diretório onde os gráficos serão guardados
CHARTS_DIR = Path("static/charts")
# Garante que o diretório exista
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def gerar_grafico_faturamento(dados_faturamento: List[Dict[str, Any]], cnpj: str) -> str:
    """
    Gera um gráfico de barras do faturamento mensal e o salva como uma imagem PNG.

    Args:
        dados_faturamento: Uma lista de dicionários, onde cada dicionário
                           contém 'data_competencia' (date) e 'valor_total' (Decimal).
        cnpj: O CNPJ da empresa para ser usado no título do gráfico.

    Returns:
        O caminho relativo do arquivo de imagem gerado.
    """
    if not dados_faturamento:
        raise ValueError("A lista de dados de faturamento não pode estar vazia.")

    # Converte os dados para um DataFrame do Pandas para facilitar a manipulação
    df = pd.DataFrame(dados_faturamento)
    df['valor_total'] = pd.to_numeric(df['valor_total'])
    
    # Formata a data para Mês/Ano (ex: Jan/2025)
    df['mes_ano'] = pd.to_datetime(df['data_competencia']).dt.strftime('%b/%Y')
    df = df.sort_values('data_competencia')

    # Cria a figura do gráfico
    fig = go.Figure()

    # Adiciona as barras ao gráfico
    fig.add_trace(go.Bar(
        x=df['mes_ano'],
        y=df['valor_total'],
        name='Faturamento',
        marker_color="#1EFF65",  # Azul-dodger como cor principal
        text=df['valor_total'].apply(lambda x: f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')),
        textposition='outside',
    ))

    # Personaliza o layout do gráfico
    # --- CORREÇÃO APLICADA AQUI ---
    fig.update_layout(
        title=f'Evolução do Faturamento Mensal - CNPJ: {cnpj}',
        xaxis_title='Mês de Competência',
        yaxis_title='Faturamento (R$)',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Arial, sans-serif",
            size=14,
            color="#333"
        ),
        xaxis=dict(showgrid=False),
        # O argumento 'yaxis' foi unificado numa única declaração
        yaxis=dict(
            tickprefix="R$ ", 
            showgrid=True, 
            gridwidth=1, 
            gridcolor='LightGray'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    # Gera um nome de arquivo único
    nome_arquivo = f"faturamento_{cnpj.replace('/', '').replace('.', '').replace('-', '')}_{uuid.uuid4()}.png"
    caminho_completo = CHARTS_DIR / nome_arquivo

    # Salva o gráfico como imagem PNG
    try:
        fig.write_image(caminho_completo, width=1200, height=600, scale=2)
    except Exception as e:
        raise RuntimeError(
            "Falha ao exportar o gráfico. "
            "Certifique-se de que a biblioteca 'kaleido' está instalada ('pip install kaleido'). "
            f"Erro original: {e}"
        ) from e


    # Retorna o caminho relativo para ser usado na API
    return str(caminho_completo).replace('\\', '/')