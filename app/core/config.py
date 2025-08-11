# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Classe de configurações para a aplicação.
    
    Usa Pydantic para validar e carregar variáveis de ambiente
    a partir de um ficheiro .env.
    """
    # Carrega as variáveis do ficheiro .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Variável de ambiente para a URL do banco de dados.
    # O Pydantic irá ler o valor de DATABASE_URL do seu ficheiro .env.
    DATABASE_URL: str

# Cria uma instância única das configurações que será usada em toda a aplicação.
settings = Settings()
