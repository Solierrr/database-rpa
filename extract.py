"""Extração de usuários sem alterar o banco legado.

O controle de idempotência fica no banco de destino, em rpa_id_mapping.
O banco de origem permanece compatível com o DBML V8 e somente é lido.
"""
import logging

import pandas as pd

from db import engine_destino, engine_origem


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

    migrados = pd.read_sql(
        """
        SELECT origem_id
        FROM rpa_id_mapping
        WHERE origem_tabela = 'usuario'
          AND destino_tabela = 'person'
        """,
        engine_destino,
    )

    if migrados.empty:
        pendentes = usuarios
    else:
        ids_migrados = set(migrados["origem_id"].astype("int64").tolist())
        pendentes = usuarios[~usuarios["id"].isin(ids_migrados)].copy()

    logger.info("Extraídos %s usuários ainda não migrados.", len(pendentes))
    return pendentes
