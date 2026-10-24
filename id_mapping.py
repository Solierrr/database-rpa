import sqlite3
from contextlib import closing

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS rpa_id_mapping (
        origem_tabela TEXT NOT NULL,
        origem_id INTEGER NOT NULL,
        destino_tabela TEXT NOT NULL,
        destino_id TEXT NOT NULL,
        criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (origem_tabela, origem_id, destino_tabela)
    )
"""


class IdMapping:
    def __init__(self, path):
        self.path = str(path)
        self._pending = {}
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self):
        return closing(sqlite3.connect(self.path))

    def get(self, origem_tabela, origem_id, destino_tabela):
        key = (origem_tabela, int(origem_id), destino_tabela)
        if key in self._pending:
            return self._pending[key]
        with self._connect() as conn:
            row = conn.execute(
                "SELECT destino_id FROM rpa_id_mapping "
                "WHERE origem_tabela = ? AND origem_id = ? AND destino_tabela = ?",
                key,
            ).fetchone()
        return row[0] if row else None

    def save(self, origem_tabela, origem_id, destino_tabela, destino_id):
        key = (origem_tabela, int(origem_id), destino_tabela)
        if key not in self._pending and self.get(*key) is None:
            self._pending[key] = str(destino_id)

    def origin_ids(self, origem_tabela, destino_tabela):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT origem_id FROM rpa_id_mapping "
                "WHERE origem_tabela = ? AND destino_tabela = ?",
                (origem_tabela, destino_tabela),
            ).fetchall()
        return {row[0] for row in rows}

    def destination_ids(self, origem_tabela, destino_tabela):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT destino_id FROM rpa_id_mapping "
                "WHERE origem_tabela = ? AND destino_tabela = ? ORDER BY destino_id",
                (origem_tabela, destino_tabela),
            ).fetchall()
        return [row[0] for row in rows]

    def flush(self):
        pending, self._pending = self._pending, {}
        if not pending:
            return
        with self._connect() as conn:
            with conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO rpa_id_mapping "
                    "(origem_tabela, origem_id, destino_tabela, destino_id) VALUES (?, ?, ?, ?)",
                    [(*key, value) for key, value in pending.items()],
                )

    def discard(self):
        self._pending = {}


_default = None


def get_mapping():
    global _default
    if _default is None:
        from config import MAPPING_DB_PATH

        _default = IdMapping(MAPPING_DB_PATH)
    return _default
