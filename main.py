# main.py (localizado na pasta raiz LUCID-COUNT)

from fastapi import FastAPI

# Importa os nossos routers
from app.routers import upload, documentos

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="LUCID-COUNT API",
    description="API para automação de relatórios e processamento de ficheiros.",
    version="0.1.0",
)

# Inclui as rotas de cada módulo na aplicação principal
app.include_router(upload.router)
app.include_router(documentos.router) #Regista o router de documentos


@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raiz da API.
    Retorna uma mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API LUCID-COUNT!"}
