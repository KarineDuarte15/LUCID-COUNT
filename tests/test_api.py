# tests/test_api.py

from pathlib import Path
from app.schemas.tipos import RegimeTributario, TipoDocumento

# --- DADOS DE TESTE CONSTANTES ---
CNPJ_TESTE = "20.295.854/0001-50"
REGIME_TESTE = RegimeTributario.SIMPLES_NACIONAL.value
TIPO_DOCUMENTO_TESTE = TipoDocumento.PGDAS.value
CAMINHO_FICHEIRO_TESTE = Path("data/uploads/202958540001-50-PGDAS-e1b60383-0dcd-40a7-8cb7-a0943367e193.pdf")


def upload_documento_teste(client):
    """
    Função auxiliar para fazer o upload de um ficheiro.
    Isto evita a repetição de código nos testes.
    """
    assert CAMINHO_FICHEIRO_TESTE.exists(), f"Ficheiro de teste não encontrado: {CAMINHO_FICHEIRO_TESTE}"
    with open(CAMINHO_FICHEIRO_TESTE, "rb") as f:
        files = {'files': (CAMINHO_FICHEIRO_TESTE.name, f, 'application/pdf')}
        data = {
            'cnpj': CNPJ_TESTE,
            'regime': REGIME_TESTE,
            'tipo_documento': TIPO_DOCUMENTO_TESTE
        }
        response = client.post("/upload/files/", files=files, data=data)
        assert response.status_code == 200, f"Falha no upload do ficheiro de teste: {response.text}"
        return response.json()


# --- TESTES DA API ---

def test_read_main_root(client):
    """ Testa o endpoint raiz ("/") da API. """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bem-vindo à API LUCID-COUNT!"}


def test_list_documents(client):
    """ Testa o endpoint que lista os documentos. """
    # Primeiro, fazemos o upload para garantir que há o que listar
    upload_documento_teste(client)
    
    response = client.get(f"/documentos/?cnpj={CNPJ_TESTE}")
    assert response.status_code == 200
    lista_documentos = response.json()
    assert isinstance(lista_documentos, list)
    assert len(lista_documentos) > 0


# --- TESTES DOS GRÁFICOS ---

def test_geracao_todos_os_graficos(client):
    """
    Um teste único que verifica todos os endpoints de gráficos.
    Isto é mais eficiente do que fazer upload do ficheiro para cada gráfico.
    """
    # Garante que os dados existem na base de dados de teste
    upload_documento_teste(client)

    params = {
        "cnpj": CNPJ_TESTE,
        "data_inicio": "2025-03-01",
        "data_fim": "2025-03-31"
    }

    endpoints_graficos = [
        "/charts/simples-nacional/faturamento",
        "/charts/simples-nacional/receita-crescimento",
        "/charts/simples-nacional/impostos-carga",
        "/charts/simples-nacional/acumulado-anual",
        "/charts/simples-nacional/limite-faturamento",
        "/charts/simples-nacional/sublimite-receita",
        "/charts/simples-nacional/segregacao-tributos",
    ]

    for endpoint in endpoints_graficos:
        response = client.get(endpoint, params=params)
        assert response.status_code == 200, f"Falha no endpoint {endpoint}: {response.text}"
        assert response.headers['content-type'] == 'image/png'
        assert len(response.content) > 100 # Verifica se a imagem não está vazia