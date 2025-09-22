# app/crud/documento.py

from sqlalchemy.orm import Session
from app.schemas.documento import DocumentoCreate
from app.models.documento import Documento
import os
from pathlib import Path
def obter_documento_por_id(db: Session, documento_id: int):
    return db.query(Documento).filter(Documento.id == documento_id).first() 

def obter_documento_por_id(db: Session, documento_id: int) -> Documento | None:
    """
    Obtém um registo de documento pelo seu ID.
    
    Args:
        db: A sessão do banco de dados.
        documento_id: O ID do documento a ser procurado.
        
    Returns:
        O objeto SQLAlchemy do documento encontrado ou None se não existir.
    """
    return db.query(Documento).filter(Documento.id == documento_id).first()

def obter_documentos(db: Session, skip: int = 0, limit: int = 100, empresa_id: int | None = None) -> list[Documento]:
    """
    Obtém uma lista de registos de documentos, com paginação.
    Pode filtrar opcionalmente por empresa_id.
    """
    query = db.query(Documento)
    if empresa_id is not None:
        query = query.filter(Documento.empresa_id == empresa_id)
    return query.offset(skip).limit(limit).all()



def criar_novo_documento(db: Session, documento: DocumentoCreate, empresa_id: int) -> Documento:
    """
    Cria um novo registo de documento no banco de dados.
    
    Args:
        db: A sessão do banco de dados.
        documento: Um objeto Pydantic com os dados do documento a ser criado.
        empresa_id: O ID da empresa à qual este documento pertence.
        
    Returns:
        O objeto SQLAlchemy do documento que foi criado.
    """
    # Cria uma instância do modelo SQLAlchemy com os dados do schema Pydantic
    db_documento = Documento(
        empresa_id=empresa_id,
        tipo_documento=documento.tipo_documento,
        # MUDANÇA: Salvar os novos campos
        nome_arquivo_original=documento.nome_arquivo_original,
        nome_arquivo_unico=documento.nome_arquivo_unico,
        tipo_arquivo=documento.tipo_arquivo,
        caminho_arquivo=documento.caminho_arquivo
    )
    
    db.add(db_documento)
    db.commit()
    db.refresh(db_documento)
    
    return db_documento
def apagar_documento_por_id(db: Session, documento_id: int) -> Documento | None:
    """
    Encontra um documento pelo ID, apaga o seu ficheiro físico e remove o registo
    do banco de dados. A remoção em cascata apaga os dados fiscais e gráficos.
    """
    db_documento = db.query(Documento).filter(Documento.id == documento_id).first()
    
    if not db_documento:
        return None

    # Apaga o ficheiro físico do servidor
    caminho_arquivo = Path(db_documento.caminho_arquivo)
    if caminho_arquivo.exists():
        os.remove(caminho_arquivo)

    # Apaga o registo do documento. A base de dados irá apagar os registos
    # dependentes em 'dados_fiscais' e 'graficos' automaticamente.
    db.delete(db_documento)
    db.commit()
    
    return db_documento
def associar_documentos_a_empresa(db: Session, empresa_id: int, documentos_ids: list[int]):
    """Atualiza o empresa_id de uma lista de documentos."""
    db.query(Documento).filter(Documento.id.in_(documentos_ids)).update(
        {"empresa_id": empresa_id}, synchronize_session=False
    )
    db.commit()

