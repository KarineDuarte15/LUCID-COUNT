# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path # NOVO

class Settings(BaseSettings):
    """
    Classe de configurações para a aplicação.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    
    # NOVO: Define o caminho absoluto para a pasta raiz do projeto (LUCID-COUNT)
    # Path(__file__) -> este ficheiro (config.py)
    # .parent -> pasta core/
    # .parent -> pasta app/
    # .parent -> pasta raiz do projeto
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

settings = Settings()
# Exemplo de uso do BASE_DIR
