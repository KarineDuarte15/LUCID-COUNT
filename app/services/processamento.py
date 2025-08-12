# app/services/processamento.py

import xmltodict
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal, InvalidOperation # NOVO: Importa o tipo Decimal

def processar_nfe_xml(caminho_arquivo: Path) -> Dict[str, Any]:
    """
    Lê um ficheiro XML de NFe, converte-o para um dicionário e extrai
    os dados fiscais especificados.
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

        # ATUALIZADO: Converte o valor para Decimal de forma segura
        valor_total_str = total.get('vNF')
        valor_total_decimal = None
        if valor_total_str:
            try:
                valor_total_decimal = Decimal(valor_total_str)
            except InvalidOperation:
                # Lida com o caso de o valor no XML não ser um número válido
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
