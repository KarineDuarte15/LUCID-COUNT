# test_db_connection.py

import sys
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError

# Adiciona o diretório 'app' ao path para que possamos importar de 'app.core'
# Isso garante que o script funcione quando executado da pasta raiz do projeto.
sys.path.append('app')

try:
    # Tenta importar as configurações e o engine do banco de dados
    from core.database import engine
    print("✅ Módulos 'core.database' importados com sucesso.")
    print("---")
    print(f"Tentando conectar ao banco de dados...")
    print(f"URL (parcial): {str(engine.url).split('@')[-1]}") # Mostra o host sem as credenciais
    print("---")

    # Tenta estabelecer uma conexão real e executar uma consulta simples.
    # Esta é a parte que provavelmente está travando.
    with engine.connect() as connection:
        print("✅ Conexão estabelecida com sucesso!")
        
        # Executa uma consulta simples para verificar se tudo está funcionando
        result = connection.execute(text("SELECT 1"))
        for row in result:
            print(f"✅ Consulta de teste retornou: {row[0]}")

    print("\n🎉 O teste foi concluído com sucesso. A sua conexão com o banco de dados está funcionando!")

except ImportError as e:
    print(f"❌ Erro de Importação: Não foi possível encontrar os módulos. Verifique se o script está na pasta raiz do projeto.")
    print(f"   Detalhe: {e}")

except (OperationalError, DBAPIError) as e:
    print(f"❌ ERRO DE CONEXÃO: Não foi possível conectar ao banco de dados.")
    print("\n--- Possíveis Causas ---")
    print("1. Firewall: O Firewall do Windows ou o seu antivírus podem estar bloqueando a conexão de saída na porta 5432 (PostgreSQL).")
    print("2. Credenciais: Verifique se a DATABASE_URL no seu ficheiro .env está 100% correta (utilizador, senha, host, nome da base de dados).")
    print("3. Rede: Verifique a sua conexão com a internet ou se há alguma VPN/Proxy a interferir.")
    print("4. Servidor Offline: Verifique no painel do Supabase (ou do seu provedor) se o banco de dados está ativo.")
    print("\n--- Detalhes do Erro ---")
    print(e)
    
except Exception as e:
    print(f"❌ Ocorreu um erro inesperado durante o teste.")
    print(f"   Detalhes: {e}")

