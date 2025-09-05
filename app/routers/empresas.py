# app/routers/empresas.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import SessionLocal
from app.crud import empresa as crud_empresa
from app.schemas.tipos import RegimeTributario

router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"],
)

# Definição do Schema Pydantic para a resposta (para a documentação)
from pydantic import BaseModel

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
    cnpj: str, 
    regime: RegimeTributario, 
    db: Session = Depends(get_db)
):
    """
    Cria uma nova empresa na base de dados.
    """
    empresa_existente = crud_empresa.get_empresa_por_cnpj(db, cnpj=cnpj)
    if empresa_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A empresa com o CNPJ {cnpj} já está cadastrada."
        )
    
    return crud_empresa.criar_empresa(db=db, cnpj=cnpj, regime=regime)

@router.get("/", response_model=List[EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    """
    Retorna uma lista de todas as empresas cadastradas. 
    Ideal para popular o menu dropdown no dashboard.
    """
    return crud_empresa.get_todas_empresas(db)