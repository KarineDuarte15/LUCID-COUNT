# app/crud/empresa.py
from sqlalchemy.orm import Session
from app.models import empresa as models
from app.schemas import empresa as schemas

def get_empresa_por_cnpj(db: Session, cnpj: str) -> models.Empresa | None:
    return db.query(models.Empresa).filter(models.Empresa.cnpj == cnpj).first()

def get_todas_empresas(db: Session) -> list[models.Empresa]:
    return db.query(models.Empresa).all()

def criar_empresa(db: Session, empresa: schemas.EmpresaCreate) -> models.Empresa:
    """
    Cria um novo registo de empresa na base de dados a partir de um schema Pydantic.
    """
    # Converte o schema Pydantic para um dicionário e cria o modelo SQLAlchemy
    db_empresa = models.Empresa(**empresa.model_dump())
    
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa