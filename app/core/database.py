# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Importa o nosso objeto de configurações centralizadas
from .config import settings

# Usa a URL do banco de dados a partir do objeto de configurações
engine = create_engine(settings.DATABASE_URL)

# Cria uma classe SessionLocal. Cada instância desta classe será uma sessão de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria uma classe Base. Usaremos esta classe para criar cada um dos modelos
# do banco de dados (os modelos ORM).
Base = declarative_base()