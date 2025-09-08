# Em: app/crud/grafico.py

from sqlalchemy.orm import Session
from app.models.grafico import Grafico
from datetime import datetime

def get_grafico_por_tipo_e_documento(db: Session, tipo_grafico: str, documento_id: int) -> Grafico | None:
    """Busca um gráfico específico pelo seu tipo e pelo ID do documento associado."""
    return db.query(Grafico).filter(
        Grafico.tipo_grafico == tipo_grafico,
        Grafico.documento_id == documento_id
    ).first()

def get_graficos_por_documento_id(db: Session, documento_id: int) -> list[Grafico]:
    """Retorna uma lista de todos os gráficos associados a um documento."""
    return db.query(Grafico).filter(Grafico.documento_id == documento_id).all()

def criar_grafico(db: Session, tipo_grafico: str, caminho_arquivo: str, documento_id: int) -> Grafico:
    """Cria um novo registro de gráfico no banco de dados."""
    db_grafico = Grafico(
        tipo_grafico=tipo_grafico,
        caminho_arquivo=caminho_arquivo,
        documento_id=documento_id
    )
    db.add(db_grafico)
    db.commit()
    db.refresh(db_grafico)
    return db_grafico

def remover_graficos_antigos(db: Session, data_limite: datetime) -> int:
    """Remove registros de gráficos mais antigos que a data limite e retorna a contagem."""
    query = db.query(Grafico).filter(Grafico.data_criacao < data_limite)
    num_removidos = query.count()
    query.delete(synchronize_session=False)
    db.commit()
    return num_removidos