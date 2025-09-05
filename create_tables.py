# create_tables.py
import time
from sqlalchemy.exc import OperationalError

from app.core.database import engine, Base
# --- ALTERAÇÃO: Importar TODOS os modelos ---
# É crucial importar todos os modelos para que o SQLAlchemy os "veja"
# e entenda as relações entre eles antes de criar as tabelas.
from app.models.empresa import Empresa
from app.models.documento import Documento
from app.models.dados_fiscais import DadosFiscais

def create_database_tables():
    """
    Conecta-se à base de dados, apaga todas as tabelas existentes (para garantir uma estrutura limpa)
    e cria todas as tabelas novamente com base nos modelos SQLAlchemy importados.
    """
    print("A tentar conectar ao banco de dados...")
    
    retries = 5
    while retries > 0:
        try:
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

    try:
        # --- ALTERAÇÃO: Apagar tabelas antigas antes de criar ---
        print("\nA apagar tabelas antigas (se existirem)...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Tabelas antigas apagadas com sucesso.")

        # --- Criação das tabelas ---
        print("\nA criar novas tabelas (Empresas, Documentos, Dados Fiscais)...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas relacionadas criadas com sucesso!")
        print("Pode agora executar o script 'adicionar_empresa.py' para popular os dados de teste.")

    except Exception as e:
        print(f"🚨 Ocorreu um erro ao recriar as tabelas: {e}")

if __name__ == "__main__":
    create_database_tables()