"""Extração de usuários sem alterar o banco legado.

O controle de idempotência fica no mapeamento local (SQLite), em rpa_id_mapping.
O banco de origem permanece compatível com o DBML V8 e somente é lido.
"""
import logging

import pandas as pd

from db import engine_origem
from id_mapping import get_mapping


logger = logging.getLogger(__name__)


def extrair_usuarios() -> pd.DataFrame:
    """Retorna apenas usuários que ainda não possuem person no destino."""
    usuarios = pd.read_sql(
        """
        SELECT id, nome, email, senha, tipo_usuario, raio_procura_km
        FROM usuario
        ORDER BY id
        """,
        engine_origem,
    )

    if usuarios.empty:
        logger.info("Nenhum usuário encontrado na origem.")
        return usuarios

    ids_migrados = get_mapping().origin_ids("usuario", "person")

    if not ids_migrados:
        pendentes = usuarios
    else:
        pendentes = usuarios[~usuarios["id"].isin(ids_migrados)].copy()

    logger.info("Extraídos %s usuários ainda não migrados.", len(pendentes))
    return pendentes
