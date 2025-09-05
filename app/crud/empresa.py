# app/crud/empresa.py

from sqlalchemy.orm import Session
from app.models.empresa import Empresa
from app.schemas.tipos import RegimeTributario # Usamos o Enum para consistência

def get_empresa_por_cnpj(db: Session, cnpj: str) -> Empresa | None:
    """Procura e retorna uma empresa pelo seu CNPJ."""
    return db.query(Empresa).filter(Empresa.cnpj == cnpj).first()

def get_todas_empresas(db: Session) -> list[Empresa]:
    """Retorna uma lista de todas as empresas cadastradas."""
    return db.query(Empresa).all()

def criar_empresa(db: Session, cnpj: str, regime: RegimeTributario) -> Empresa:
    """Cria um novo registo de empresa na base de dados."""
    
    # Cria uma instância do modelo SQLAlchemy
    db_empresa = Empresa(
        cnpj=cnpj,
        regime_tributario=regime.value # Usamos .value para guardar a string
    )
    
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa