# app/core/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

# Pega a URL do banco de dados a partir das variáveis de ambiente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o "motor" do SQLAlchemy. Este é o ponto de entrada principal para o banco de dados.
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Cria uma classe SessionLocal. Cada instância desta classe será uma sessão de banco de dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria uma classe Base. Usaremos esta classe para criar cada um dos modelos
# do banco de dados (os modelos ORM).
Base = declarative_base()