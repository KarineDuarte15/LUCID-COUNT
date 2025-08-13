# app/services/processamento.py

import xmltodict
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal, InvalidOperation

def processar_nfe_xml(caminho_arquivo: Path) -> Dict[str, Any]:
    """
    Lê um ficheiro XML de NFe e extrai os dados fiscais.
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"O ficheiro não foi encontrado em: {caminho_arquivo}")

    try:
        with open(caminho_arquivo, 'rb') as f:
            xml_content = f.read()
        
        dados = xmltodict.parse(xml_content)
        
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
            produtos_extraidos.append({
                "cfop": produto_info.get('CFOP'),
                "ncm": produto_info.get('NCM')
            })

        valor_total_str = total.get('vNF')
        valor_total_decimal = None
        if valor_total_str:
            try:
                valor_total_decimal = Decimal(valor_total_str)
            except InvalidOperation:
                valor_total_decimal = None

        dados_finais = {
            "cnpj_emitente": emitente.get('CNPJ'),
            "valor_total": valor_total_decimal,
            "produtos": produtos_extraidos
        }
        
        return dados_finais

    except Exception as e:
        print(f"Erro ao processar o ficheiro XML {caminho_arquivo}: {e}")
        raise ValueError(f"Não foi possível processar o ficheiro XML. Verifique o formato. Erro: {e}")

# --- NOVA FUNÇÃO ---
def xml_para_dataframe(dados_extraidos: Dict[str, Any]) -> pd.DataFrame:
    """
    Converte os dados extraídos de um XML para um DataFrame do Pandas,
    padronizando e validando as informações.
    """
    # Pega a lista de produtos dos dados extraídos
    produtos = dados_extraidos.get("produtos", [])
    if not produtos:
        # Retorna um DataFrame vazio se não houver produtos
        return pd.DataFrame()

    # Cria o DataFrame a partir da lista de produtos
    df = pd.DataFrame(produtos)

    # Adiciona as informações gerais (CNPJ e Valor Total) a cada linha do DataFrame
    df['cnpj_emitente'] = dados_extraidos.get("cnpj_emitente")
    df['valor_total_nota'] = dados_extraidos.get("valor_total")
    
    # Padroniza os nomes das colunas
    df = df.rename(columns={
        'cnpj_emitente': 'CNPJ_Emitente',
        'valor_total_nota': 'Valor_Total_Nota',
        'cfop': 'CFOP',
        'ncm': 'NCM'
    })

    # Garante a ordem das colunas
    df = df[['CNPJ_Emitente', 'Valor_Total_Nota', 'CFOP', 'NCM']]

    # Validação de dados obrigatórios
    colunas_obrigatorias = ['CNPJ_Emitente', 'Valor_Total_Nota']
    if df[colunas_obrigatorias].isnull().values.any():
        raise ValueError("Dados obrigatórios (CNPJ ou Valor Total) não encontrados no XML.")
        
    # Converte os tipos de dados para os formatos corretos
    df['Valor_Total_Nota'] = pd.to_numeric(df['Valor_Total_Nota'], errors='coerce')
    df['CFOP'] = df['CFOP'].astype(str)
    df['NCM'] = df['NCM'].astype(str)
    
    return df
