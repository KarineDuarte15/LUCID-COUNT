# app/routers/empresas.py

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated

from app.core.database import SessionLocal
from app.crud import empresa as crud_empresa
from app.crud import empresa as crud_empresa, documento as crud_documento # Adicionar crud_documento
from app.crud import documento as crud_documento
from pydantic import BaseModel
from app.schemas.tipos import RegimeTributario
from fastapi import Query
from typing import Optional


router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"],
)

# O Schema de Resposta continua igual
class EmpresaResponse(BaseModel):
    id: int
    cnpj: str
    regime_tributario: str
    
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def criar_nova_empresa(
    # Agora recebemos os dados como campos de formulário
    cnpj: Annotated[str, Form(description="O CNPJ da nova empresa.")],
    regime: Annotated[RegimeTributario, Form(description="O regime tributário da empresa.")],
    # O campo documentos_ids é opcional
    documentos_ids: Optional[List[int]] = Form(None, description="IDs de documentos existentes para associar à nova empresa."),
    db: Session = Depends(get_db)
):
    empresa_existente = crud_empresa.get_empresa_por_cnpj(db, cnpj=cnpj)
    if empresa_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A empresa com o CNPJ {cnpj} já está cadastrada."
        )
    
    # 4. Usar as variáveis diretamente
    nova_empresa = crud_empresa.criar_empresa(db=db, cnpj=cnpj, regime=regime)
    
    if documentos_ids:
        crud_documento.associar_documentos_a_empresa(
            db=db,
            empresa_id=nova_empresa.id,
            documentos_ids=documentos_ids
        )
        
    return nova_empresa
    
@router.get("/", response_model=List[EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as empresas cadastradas. 
    Ideal para popular o menu dropdown no dashboard.
    """
    return crud_empresa.get_todas_empresas(db)
