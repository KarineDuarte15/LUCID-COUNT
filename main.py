# main.py 
import json
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI

# Importa os nossos routers
from app.routers import upload, documentos
# Importa o router de analytics
from app.routers import analytics as analytics_router

# ---  resposta personalizada ---
class CustomJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self.default_serializer # Usa o nosso serializador personalizado
        ).encode("utf-8")

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, Decimal):
            return str(obj) # Converte Decimal para string
        raise TypeError
# --------------------------------------------------

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="LUCID-COUNT API",
    description="API para automação de relatórios e processamento de ficheiros.",
    version="0.1.0",
    default_response_class=CustomJSONResponse   # Usa a nossa resposta personalizada
)

# Inclui as rotas de cada módulo na aplicação principal
app.include_router(upload.router)
app.include_router(documentos.router) #Regista o router de documentos
app.include_router(analytics_router.router) # Regista o router de analytics


@app.get("/", tags=["Root"])
def read_root():
    """
    Endpoint raiz da API.
    Retorna uma mensagem de boas-vindas.
    """
    return {"message": "Bem-vindo à API LUCID-COUNT!"}
