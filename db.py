"""
Engines de conexão com os dois bancos Postgres.
pool_pre_ping evita erro de conexão "morta" quando o script fica
horas parado entre uma execução e outra (roda só 3-4x/dia).
"""
from sqlalchemy import create_engine
from config import ORIGEM_DB_URL, DESTINO_DB_URL
 
engine_origem = create_engine(ORIGEM_DB_URL, pool_pre_ping=True)
engine_destino = create_engine(DESTINO_DB_URL, pool_pre_ping=True)
 
