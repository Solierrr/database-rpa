"""
Extração — busca os registros ainda não processados no banco simples.

⚠️ AJUSTE NECESSÁRIO:
Este arquivo assume que a tabela de origem se chama "usuario" e tem uma
coluna de controle "processado_em" (timestamp, nullable). Troque o nome
da tabela/colunas abaixo assim que você tiver o schema real do banco
simples.

Se não quiser alterar a tabela de origem, use a variante com tabela de
controle separada (comentada no final do arquivo).
"""
import logging
import pandas as pd
from sqlalchemy import text
from db import engine_origem

logger = logging.getLogger(__name__)


def criar_coluna_controle_se_nao_existir():
    """
    Idempotente: cria a coluna 'processado_em' na tabela usuario da
    origem, caso ainda não exista. Rode isso uma vez (ou deixe aqui,
    não tem custo rodar de novo).
    """
    with engine_origem.begin() as conn:
        conn.execute(text("""
            ALTER TABLE usuario
            ADD COLUMN IF NOT EXISTS processado_em TIMESTAMP NULL
        """))


def extrair_usuarios() -> pd.DataFrame:
    """Busca usuários da origem que ainda não foram enviados ao destino."""
    query = """
        SELECT id, nome, email, senha, tipo_usuario, raio_procura_km
        FROM usuario
        WHERE processado_em IS NULL
        ORDER BY id
    """
    df = pd.read_sql(query, engine_origem)
    logger.info(f"Extraídos {len(df)} registros novos da origem")
    return df


def marcar_processado(ids: list):
    """Marca os IDs como processados para não reprocessar na próxima execução."""
    if not ids:
        return
    with engine_origem.begin() as conn:
        conn.execute(
            text("UPDATE usuario SET processado_em = now() WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
    logger.info(f"{len(ids)} registros marcados como processados na origem")


# ---------------------------------------------------------------------------
# Alternativa: tabela de controle separada, sem alterar a tabela de origem.
# Descomente e use no lugar das funções acima se preferir esse caminho.
# ---------------------------------------------------------------------------
#
# def criar_tabela_controle_se_nao_existir():
#     with engine_origem.begin() as conn:
#         conn.execute(text("""
#             CREATE TABLE IF NOT EXISTS rpa_controle (
#                 origem_id BIGINT PRIMARY KEY,
#                 processado_em TIMESTAMP NOT NULL DEFAULT now()
#             )
#         """))
#
# def extrair_usuarios() -> pd.DataFrame:
#     query = """
#         SELECT u.id, u.nome, u.email, u.senha, u.tipo_usuario, u.raio_procura_km
#         FROM usuario u
#         LEFT JOIN rpa_controle rc ON rc.origem_id = u.id
#         WHERE rc.origem_id IS NULL
#         ORDER BY u.id
#     """
#     return pd.read_sql(query, engine_origem)
#
# def marcar_processado(ids: list):
#     if not ids:
#         return
#     with engine_origem.begin() as conn:
#         conn.execute(
#             text("""
#                 INSERT INTO rpa_controle (origem_id)
#                 SELECT unnest(:ids)
#                 ON CONFLICT (origem_id) DO NOTHING
#             """),
#             {"ids": ids},
#         )