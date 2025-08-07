# main.py (localizado na pasta raiz LUCID-COUNT)

from fastapi import FastAPI
# Importa o módulo de upload a partir do pacote 'app'
# A importação agora funciona perfeitamente porque 'app' é um pacote
# claramente visível a partir da raiz do projeto.
from app.routers import upload

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="LUCID-COUNT API",
    description="API para automação de relatórios e processamento de ficheiros.",
    version="0.1.0",
)

# Inclui as rotas definidas no módulo de upload
app.include_router(upload.router)


@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raiz da API.
    Retorna uma mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API LUCID-COUNT!"}

