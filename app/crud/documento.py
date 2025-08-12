# app/crud/documento.py

from sqlalchemy.orm import Session
from app.models.documento import TabelaDocumentos
from app.schemas.documento import DocumentoCreate

def obter_documento_por_id(db: Session, documento_id: int) -> TabelaDocumentos | None:
    """
    Obtém um registo de documento pelo seu ID.
    
    Args:
        db: A sessão do banco de dados.
        documento_id: O ID do documento a ser procurado.
        
    Returns:
        O objeto SQLAlchemy do documento encontrado ou None se não existir.
    """
    return db.query(TabelaDocumentos).filter(TabelaDocumentos.id == documento_id).first()

def obter_documentos(db: Session, skip: int = 0, limit: int = 100) -> list[TabelaDocumentos]:
    """
    Obtém uma lista de registos de documentos, com paginação.
    
    Args:
        db: A sessão do banco de dados.
        skip: O número de registos a saltar (para paginação).
        limit: O número máximo de registos a retornar.
        
    Returns:
        Uma lista de objetos SQLAlchemy de documentos.
    """
    return db.query(TabelaDocumentos).offset(skip).limit(limit).all()


def criar_novo_documento(db: Session, documento: DocumentoCreate) -> TabelaDocumentos:
    """
    Cria um novo registo de documento no banco de dados.
    
    Args:
        db: A sessão do banco de dados.
        documento: Um objeto Pydantic com os dados do documento a ser criado.
        
    Returns:
        O objeto SQLAlchemy do documento que foi criado.
    """
    # Cria uma instância do modelo SQLAlchemy com os dados do schema Pydantic
    db_documento = TabelaDocumentos(
        nome_arquivo=documento.nome_arquivo,
        tipo_arquivo=documento.tipo_arquivo,
        caminho_arquivo=documento.caminho_arquivo
    )
    
    # Adiciona a nova instância à sessão
    db.add(db_documento)
    
    # Confirma (commit) a transação para salvar no banco de dados
    db.commit()
    
    # Atualiza a instância com os dados do banco (como o ID gerado)
    db.refresh(db_documento)
    
    return db_documento
