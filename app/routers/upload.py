# app/routers/upload.py

import shutil
import uuid
import os
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.services.processamento import PROCESSADORES

# Importações da nossa aplicação
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento
# --- NOVAS IMPORTAÇÕES NECESSÁRIAS ---
from app.crud import dados_fiscais as crud_dados_fiscais
from app.services import processamento as services_processamento
# ------------------------------------

# Cria o roteador
router = APIRouter(
    prefix="/upload",
    tags=["Uploads"],
)

# --- Constantes de Validação ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 Megabytes
ALLOWED_MIME_TYPES = ["application/pdf", "application/xml", "text/xml", "text/plain"]
UPLOAD_DIRECTORY = Path("data/uploads")


# --- Dependência da Base de Dados ---
def get_db():
    """
    Função de dependência para obter uma sessão da base de dados.
    Garante que a sessão é sempre fechada após a requisição.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/files/",
    response_model=List[schemas_documento.Documento],
    summary="Recebe, valida e regista múltiplos ficheiros de um tipo específico",
    description=f"Faz o upload de um ou mais ficheiros (PDF/XML/TXT, máx {MAX_FILE_SIZE/1024/1024}MB cada), guarda-os e regista os seus metadados na base de dados."
)
async def upload_e_registar_multiplos_ficheiros(
    tipo_documento: Annotated[str, Form(description="O tipo de documento fiscal (ex: 'Encerramento ISS', 'EFD ICMS').")],
    files: Annotated[List[UploadFile], File(description="Uma lista de ficheiros a serem enviados.")],
    db: Session = Depends(get_db)
):
    """
    Endpoint para receber, validar, salvar, registar E PROCESSAR múltiplos ficheiros.
    """
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    
    documentos_criados = []

    for file in files:
        # Validações de tipo e tamanho (código existente)
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(...) # Mantém o teu código de erro aqui

        unique_filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
        file_path = UPLOAD_DIRECTORY / unique_filename
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(...) # Mantém o teu código de erro aqui

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(...) # Mantém o teu código de erro aqui

        # Interação com a Base de Dados
        try:
            caminho_relativo_str = str(file_path).replace('\\', '/')
            documento_a_criar = schemas_documento.DocumentoCreate(
                tipo_documento=tipo_documento,
                nome_arquivo=unique_filename,
                tipo_arquivo=file.content_type,
                caminho_arquivo=caminho_relativo_str
            )
            
            documento_criado = crud_documento.criar_novo_documento(db=db, documento=documento_a_criar)
            documentos_criados.append(documento_criado)
            
            # ===================================================================
            # --- INÍCIO DA LÓGICA DE PROCESSAMENTO E SALVAMENTO AUTOMÁTICO ---
            # ===================================================================
            
            funcao_processamento = PROCESSADORES.get(documento_criado.tipo_documento)
    
            if funcao_processamento:
                print(f"Processando documento ID {documento_criado.id} do tipo '{documento_criado.tipo_documento}'...")
                try:
                    caminho_absoluto = Path(documento_criado.caminho_arquivo).resolve()
                    dados_extraidos = funcao_processamento(caminho_absoluto)
                    
                    # Salva os dados extraídos na nova tabela 'dados_fiscais'
                    crud_dados_fiscais.salvar_dados_fiscais(
                        db=db, 
                        documento_id=documento_criado.id, 
                        dados_extraidos=dados_extraidos
                    )
                    print(f"SUCESSO: Dados do documento ID {documento_criado.id} foram extraídos e salvos.")
                    
                except Exception as e:
                    # Se o processamento falhar, o upload não é revertido, mas registamos o erro no terminal
                    print(f"AVISO: O ficheiro do documento ID {documento_criado.id} foi salvo, mas ocorreu um erro durante o processamento e extração de dados: {e}")
                    # Opcional: Adicionar uma lógica para marcar o documento como "falha_no_processamento" na base de dados
            else:
                print(f"AVISO: Nenhum processador encontrado para o tipo de documento '{documento_criado.tipo_documento}'. O ficheiro foi salvo mas não processado.")

            # ===================================================================
            # --- FIM DA LÓGICA DE PROCESSAMENTO E SALVAMENTO AUTOMÁTICO ---
            # ===================================================================

        except Exception as e:
            os.remove(file_path)
            raise HTTPException(...) # Mantém o teu código de erro aqui
            
    return documentos_criados