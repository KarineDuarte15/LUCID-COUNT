# tests/conftest.py

import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- Adiciona o diretório raiz ao caminho do Python ---
# Isto garante que 'from app...' e 'from main...' funcionam corretamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Importações da sua aplicação ---
# Estas importações só são possíveis por causa da linha `sys.path.insert` acima
from app.core.database import Base, get_db
from main import app

# --- Configuração da Base de Dados de TESTE (em memória) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Requisito para SQLite
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- Função para Substituir a Base de Dados ---
def override_get_db():
    """
    Uma função de dependência que fornece uma sessão da base de dados
    de teste e a fecha no final.
    """
    db = None
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        if db:
            db.close()


# --- Fixture Principal para os Testes ---
@pytest.fixture(scope="function")
def client():
    """
    Esta fixture é executada ANTES de cada função de teste.
    Garante um ambiente 100% limpo para cada teste.
    """
    # 1. Substitui a dependência 'get_db' pela nossa versão de teste
    app.dependency_overrides[get_db] = override_get_db

    # 2. Cria todas as tabelas na base de dados de teste em memória
    Base.metadata.create_all(bind=engine)

    # 3. Disponibiliza o cliente de teste para a função de teste
    yield TestClient(app)

    # 4. (Pós-teste) Limpa todas as tabelas da base de dados
    Base.metadata.drop_all(bind=engine)
    
    # 5. (Pós-teste) Remove a substituição para não afetar outros possíveis testes
    app.dependency_overrides.clear()