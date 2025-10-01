# app/routers/upload.py

import shutil
import uuid
import os
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.services.processamento import PROCESSADORES
from app.schemas.tipos import RegimeTributario
from app.schemas.tipos import TipoDocumento, TipoDocumento

# Importações da nossa aplicação
from app.core.database import SessionLocal
from app.crud import documento as crud_documento
from app.schemas import documento as schemas_documento
from app.schemas import empresa as schemas_empresa
# --- NOVAS IMPORTAÇÕES NECESSÁRIAS ---
from app.crud import dados_fiscais as crud_dados_fiscais
from app.services import processamento as services_processamento
from app.crud import empresa as crud_empresa 
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
    # ALTERADO: Agora tipo_documento é do tipo Enum
    cnpj: Annotated[str, Form(description="CNPJ da empresa à qual os documentos pertencem.")],
    regime: Annotated[RegimeTributario, Form(description="O regime tributário da empresa.")],
    tipo_documento: Annotated[TipoDocumento, Form(description="O tipo de documento fiscal.")],
    files: Annotated[List[UploadFile], File(description="Uma lista de ficheiros a serem enviados.")],
    db: Session = Depends(get_db)
):
    """
    Endpoint para receber, validar, salvar, registar E PROCESSAR múltiplos ficheiros.
    """
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    # CÓDIGO CORRIGIDO
    # Cria uma instância do schema Pydantic com os dados recebidos
    empresa_para_criar = schemas_empresa.EmpresaCreate(cnpj=cnpj, regime_tributario=regime.value)
    # Passa o objeto schema para a função do CRUD
    empresa = crud_empresa.criar_empresa(db=db, empresa=empresa_para_criar)
    if not empresa:
        print(f"Empresa com CNPJ {cnpj} não encontrada. Criando novo registo...")
        empresa = crud_empresa.criar_empresa(db=db, cnpj=cnpj, regime=regime)
        print(f"✅ Empresa {cnpj} criada com o ID {empresa.id}.")
    
    empresa_id = empresa.id
    documentos_criados = []
    for file in files:
        # Validações de tipo e tamanho (código existente)
         # --- CORREÇÃO: Validação no nível correto do loop ---
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Tipo de ficheiro '{file.content_type}' não suportado para '{file.filename}'.")

        # --- MUDANÇA: Lógica para criar um nome de ficheiro descritivo e único ---
        extensao = Path(file.filename).suffix
        # Remove caracteres especiais do tipo de documento para usar no nome do ficheiro
        tipo_doc_safe = tipo_documento.value.replace(" ", "_").replace("/", "-")
        # Novo formato: CNPJ-TipoDocumento-UUID.extensao
        unique_filename = f"{cnpj.replace('/', '').replace('.', '')}-{tipo_doc_safe}-{uuid.uuid4()}{extensao}"
        
        file_path = UPLOAD_DIRECTORY / unique_filename
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Não foi possível salvar o ficheiro: {e}")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"O ficheiro '{file.filename}' excede o tamanho máximo de {MAX_FILE_SIZE/1024/1024}MB.")

        try:
            caminho_relativo_str = str(file_path).replace('\\', '/')
            
            # --- MUDANÇA: Usar os novos campos do schema ---
            documento_a_criar = schemas_documento.DocumentoCreate(
                empresa_id=empresa.id, 
                tipo_documento=tipo_documento.value, # Salva o valor string do Enum
                nome_arquivo_original=file.filename,
                nome_arquivo_unico=unique_filename,
                tipo_arquivo=file.content_type,
                caminho_arquivo=caminho_relativo_str
            )
            
            documento_criado = crud_documento.criar_novo_documento(
                db=db, 
                documento=documento_a_criar, 
                empresa_id=empresa.id 
            )
            
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