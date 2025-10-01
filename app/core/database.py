# app/core/database.py

import ssl #Importa o módulo SSL para configurar a conexão segura
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Importa o nosso objeto de configurações centralizadas
from .config import settings

# --- NOVO: Configuração de SSL para o pg8000 ---
# O Supabase exige uma conexão segura (SSL).
# O pg8000 precisa que esta configuração seja passada através de 'connect_args'.
ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

connect_args = {"ssl_context": ssl_context}


# Usa a URL do banco de dados a partir do objeto de configurações
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args # Adiciona os argumentos de conexão SSL
)

# Cria uma classe SessionLocal. Cada instância desta classe será uma sessão de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria uma classe Base. Usaremos esta classe para criar cada um dos modelos
# do banco de dados (os modelos ORM).
Base = declarative_base()

# --- FUNÇÃO DE DEPENDÊNCIA ---
# Cria e fornece uma sessão de banco de dados por requisição e garante que ela seja fechada.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
