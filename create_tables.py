# create_tables.py

import time
from sqlalchemy.exc import OperationalError
from app.core.database import engine, Base
from app.models import documento # Importa o módulo para que o SQLAlchemy reconheça o modelo

def create_database_tables():
    """
    Tenta conectar ao banco de dados e cria todas as tabelas definidas
    pelo Base do SQLAlchemy.
    """
    print("A tentar conectar ao banco de dados...")
    

    retries = 5
    while retries > 0:
        try:
            # Tenta estabelecer uma conexão
            connection = engine.connect()
            connection.close()
            print("✅ Conexão com o banco de dados bem-sucedida!")
            break
        except OperationalError:
            print("❌ Conexão com o banco de dados falhou. A tentar novamente em 5 segundos...")
            retries -= 1
            time.sleep(5)
    
    if retries == 0:
        print("🚨 Não foi possível conectar ao banco de dados após várias tentativas. Abortando.")
        return

    print("\nA criar tabelas no banco de dados...")
    try:
        # O comando mágico: cria todas as tabelas que herdam de Base
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas com sucesso!")
        print("Pode verificar a tabela 'tabela_documentos' usando o DBeaver.")
    except Exception as e:
        print(f"🚨 Ocorreu um erro ao criar as tabelas: {e}")

if __name__ == "__main__":
    create_database_tables()
