# app/routers/empresas.py
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import SessionLocal
from app.crud import empresa as crud_empresa
from app.schemas import empresa as schemas_empresa

router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- NOVO ENDPOINT PARA CONSULTAR CNPJ ---
@router.get(
    "/consultar/{cnpj}", 
    # Usamos o EmpresaBase porque não teremos um ID do banco de dados ainda
    response_model=schemas_empresa.EmpresaBase,
    summary="Consulta dados públicos de um CNPJ numa API externa."
)
async def consultar_cnpj_externo(cnpj: str):
    """
    Recebe um CNPJ, consulta na BrasilAPI e retorna os dados públicos
    formatados para preencher o formulário de cadastro.
    """
    # EXPLICAÇÃO: Limpa o CNPJ, deixando apenas os números.
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

    # EXPLICAÇÃO: URL da BrasilAPI para consulta de CNPJ.
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"

    try:
        # EXPLICAÇÃO: Faz a requisição para a API externa de forma assíncrona.
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

        # EXPLICAÇÃO: Se a API retornar um erro (ex: CNPJ não encontrado), repassamos o erro.
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CNPJ não encontrado ou inválido na base da Receita Federal."
            )

        dados = response.json()

        # EXPLICAÇÃO: Mapeamento dos dados da BrasilAPI para o nosso schema de empresa.
        # Isto garante que a resposta do nosso backend para o frontend será sempre consistente.
        empresa_formatada = schemas_empresa.EmpresaBase(
            cnpj=dados.get('cnpj', cnpj),
            regime_tributario="Simples Nacional", # Valor padrão
            razao_social=dados.get('razao_social'),
            nome_fantasia=dados.get('nome_fantasia'),
            ativa=True, # Valor padrão
            endereco=schemas_empresa.EnderecoSchema(
                logradouro=dados.get('logradouro'),
                numero=dados.get('numero'),
                complemento=dados.get('complemento'),
                cep=dados.get('cep'),
                bairro=dados.get('bairro'),
                cidade=dados.get('municipio'),
                uf=dados.get('uf')
            ),
            fones=[dados.get('ddd_telefone_1'), dados.get('ddd_telefone_2')],
            outros_identificadores=[f"Inscrição Estadual: {dados.get('descricao_situacao_cadastral')}"],
            # Adicione outros campos conforme necessário
        )
        
        return empresa_formatada

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro ao comunicar com a API externa de CNPJ: {exc}"
        )

# --- ENDPOINTS EXISTENTES (CRIAR E LISTAR) ---
@router.post("/", response_model=schemas_empresa.EmpresaResponse, status_code=status.HTTP_201_CREATED)
def criar_nova_empresa(
    empresa: schemas_empresa.EmpresaCreate, 
    db: Session = Depends(get_db)
):
    empresa_existente = crud_empresa.get_empresa_por_cnpj(db, cnpj=empresa.cnpj)
    if empresa_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A empresa com o CNPJ {empresa.cnpj} já está cadastrada."
        )
    
    nova_empresa = crud_empresa.criar_empresa(db=db, empresa=empresa)
    return nova_empresa
    
@router.get("/", response_model=List[schemas_empresa.EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    return crud_empresa.get_todas_empresas(db)