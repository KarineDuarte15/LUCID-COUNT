# main.py 
import json
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os nossos routers
from app.routers import upload, documentos, charts_router,empresas
# Importa o router de analytics
from app.routers import analytics as analytics_router
from app.routers import upload_options
# --- Serializador Personalizado ---
# Função para ensinar o JSON a lidar com tipos de dados que ele não conhece.
def custom_serializer(obj):
    if isinstance(obj, Decimal):
        return str(obj) # Converte Decimal para string
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# Configuração do CORS
# ---  resposta personalizada ---
class CustomJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        # Usa o jsonable_encoder da FastAPI, que é mais robusto.
        return super().render(jsonable_encoder(content, custom_encoder={Decimal: str}))


# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="LUCID-COUNT API",
    description="API para automação de relatórios e processamento de ficheiros.",
    version="0.1.0",
    default_response_class=CustomJSONResponse   # Usa a nossa resposta personalizada
)

origins = [
    "http://localhost:3000", # Endereço do seu frontend React/Next.js
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos
)

# Inclui as rotas de cada módulo na aplicação principal
app.include_router(upload.router)
app.include_router(documentos.router) #Regista o router de documentos
app.include_router(analytics_router.router) # Regista o router de analytics
app.include_router(charts_router.router)
app.include_router(upload_options.router)
app.include_router(empresas.router)

@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raiz da API.
    Retorna uma mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API LUCID-COUNT!"}
