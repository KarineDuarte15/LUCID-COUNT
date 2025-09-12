# app/routers/empresas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import SessionLocal
from app.crud import empresa as crud_empresa
# Importa os novos schemas que criamos
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

@router.post("/", response_model=schemas_empresa.EmpresaResponse, status_code=status.HTTP_201_CREATED)
def criar_nova_empresa(
    # ALTERADO: Agora a função recebe um objeto JSON no corpo da requisição
    empresa: schemas_empresa.EmpresaCreate, 
    db: Session = Depends(get_db)
):
    empresa_existente = crud_empresa.get_empresa_por_cnpj(db, cnpj=empresa.cnpj)
    if empresa_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A empresa com o CNPJ {empresa.cnpj} já está cadastrada."
        )
    
    # A lógica fica muito mais simples, apenas passa o objeto para a função do CRUD
    nova_empresa = crud_empresa.criar_empresa(db=db, empresa=empresa)
    return nova_empresa
    
@router.get("/", response_model=List[schemas_empresa.EmpresaResponse])
def listar_empresas(db: Session = Depends(get_db)):
    return crud_empresa.get_todas_empresas(db)