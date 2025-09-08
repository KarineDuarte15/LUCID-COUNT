# Em: scripts/cleanup_charts.py

import os
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Adiciona o diretório raiz ao path para permitir importações da 'app'
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.grafico import Grafico
from app.crud.grafico import remover_graficos_antigos

# --- Configurações ---
DIRETORIO_GRAFICOS = Path("static/charts")
DIAS_PARA_MANTER = 30 # Apagar gráficos com mais de 30 dias

def limpar_graficos_orfãos():
    """
    Compara o banco de dados e o sistema de arquivos para remover
    registros sem arquivos e arquivos sem registros.
    """
    print("--- Iniciando limpeza de gráficos órfãos ---")
    db = SessionLocal()
    
    # 1. Encontrar registros no DB sem arquivo físico
    registros_db = db.query(Grafico).all()
    registros_a_remover = []
    
    for registro in registros_db:
        if not Path(registro.caminho_arquivo).exists():
            print(f"[DB -> FS] Arquivo não encontrado para o registro {registro.id}. Marcando para remoção.")
            registros_a_remover.append(registro)

    if registros_a_remover:
        for registro in registros_a_remover:
            db.delete(registro)
        db.commit()
        print(f"✅ {len(registros_a_remover)} registros órfãos removidos do banco de dados.")

    # 2. Encontrar arquivos físicos sem registro no DB
    caminhos_db = {g.caminho_arquivo for g in registros_db}
    arquivos_removidos = 0
    
    for arquivo in DIRETORIO_GRAFICOS.glob("*.png"):
        caminho_str = str(arquivo).replace('\\', '/')
        if caminho_str not in caminhos_db:
            print(f"[FS -> DB] Registro não encontrado para o arquivo {caminho_str}. Removendo arquivo.")
            os.remove(arquivo)
            arquivos_removidos += 1
            
    if arquivos_removidos > 0:
        print(f"✅ {arquivos_removidos} arquivos órfãos removidos da pasta de gráficos.")

    db.close()
    print("--- Limpeza de órfãos concluída ---")

def limpar_graficos_por_data():
    """Remove gráficos (arquivo e registro) mais antigos que o limite definido."""
    print(f"\n--- Iniciando limpeza de gráficos com mais de {DIAS_PARA_MANTER} dias ---")
    db = SessionLocal()
    
    data_limite = datetime.now() - timedelta(days=DIAS_PARA_MANTER)
    
    graficos_antigos = db.query(Grafico).filter(Grafico.data_criacao < data_limite).all()
    
    if not graficos_antigos:
        print("Nenhum gráfico antigo para remover.")
        db.close()
        return

    print(f"Encontrados {len(graficos_antigos)} gráficos para remover...")
    for grafico in graficos_antigos:
        if Path(grafico.caminho_arquivo).exists():
            os.remove(grafico.caminho_arquivo)
        db.delete(grafico)
        
    db.commit()
    db.close()
    print(f"✅ {len(graficos_antigos)} gráficos antigos removidos com sucesso.")
    print("--- Limpeza por data concluída ---")


if __name__ == "__main__":
    limpar_graficos_orfãos()
    limpar_graficos_por_data()