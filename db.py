"""
Engines de conexão com os dois bancos Postgres.
pool_pre_ping evita erro de conexão "morta" quando o script fica
horas parado entre uma execução e outra (roda só 3-4x/dia).
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from config import ORIGEM_DB_URL, DESTINO_DB_URL
from id_mapping import get_mapping
 
engine_origem = create_engine(ORIGEM_DB_URL, pool_pre_ping=True)
engine_destino = create_engine(DESTINO_DB_URL, pool_pre_ping=True)


@contextmanager
def destination_transaction():
    mapping = get_mapping()
    try:
        with engine_destino.begin() as conn:
            yield conn
    except BaseException:
        mapping.discard()
        raise
    mapping.flush()
 
