"""
Configuração central do RPA.
Lê as URLs de conexão do .env (que você já tem pronto).

Formato esperado no .env:
    ORIGEM_DB_URL=postgresql+psycopg2://usuario:senha@host_origem:5432/banco_simples
    DESTINO_DB_URL=postgresql+psycopg2://usuario:senha@host_destino:5432/banco_solaria
"""
import os
from dotenv import load_dotenv

load_dotenv()

ORIGEM_DB_URL = os.getenv("ORIGEM_DB_URL")
DESTINO_DB_URL = os.getenv("DESTINO_DB_URL")

if not ORIGEM_DB_URL or not DESTINO_DB_URL:
    raise RuntimeError(
        "ORIGEM_DB_URL e/ou DESTINO_DB_URL não encontrados no .env. "
        "Confira se o arquivo .env está na raiz do projeto."
    )

# Locale do Faker para gerar dados fictícios coerentes com pt-BR
FAKER_LOCALE = "pt_BR"

# Nível de log
LOG_FILE = "rpa_etl.log"
LOG_LEVEL = "INFO"