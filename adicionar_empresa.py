# adicionar_empresa.py
from app.core.database import SessionLocal
from app.models.empresa import Empresa

# --- DADOS DA EMPRESA PARA TESTE ---
# Use um CNPJ real que você espera ver no dashboard
CNPJ_TESTE = "20.295.854/0001-50" 
REGIME_TESTE = "Simples Nacional"
# ------------------------------------

def adicionar_empresa_teste():
    print("A iniciar sessão na base de dados...")
    db = SessionLocal()
    try:
        # Verifica se a empresa já existe
        empresa_existente = db.query(Empresa).filter(Empresa.cnpj == CNPJ_TESTE).first()

        if empresa_existente:
            print(f"✅ A empresa com CNPJ {CNPJ_TESTE} já existe na base de dados.")
        else:
            print(f"A adicionar nova empresa: {CNPJ_TESTE}")
            nova_empresa = Empresa(
                cnpj=CNPJ_TESTE,
                regime_tributario=REGIME_TESTE
            )
            db.add(nova_empresa)
            db.commit()
            print(f"✅ Empresa {CNPJ_TESTE} adicionada com sucesso!")

    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")
        db.rollback()
    finally:
        print("A fechar sessão.")
        db.close()

if __name__ == "__main__":
    adicionar_empresa_teste()