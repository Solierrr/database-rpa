import logging

import pandas as pd

from sqlalchemy import text

from db import engine_destino


logger = logging.getLogger(__name__)


SQL_CRIAR_MAPEAMENTO = text("""
    CREATE TABLE IF NOT EXISTS rpa_id_mapping (

        id SERIAL PRIMARY KEY,

        origem_tabela VARCHAR(50) NOT NULL,

        origem_id BIGINT NOT NULL,

        destino_tabela VARCHAR(50) NOT NULL,

        destino_id UUID NOT NULL,

        criado_em TIMESTAMP NOT NULL DEFAULT now(),

        UNIQUE (
            origem_tabela,
            origem_id,
            destino_tabela
        )
    )
""")


SQL_INSERT_USERS = text("""
    INSERT INTO users (
        id,
        avatar
    )
    VALUES (
        :users_id,
        :avatar
    )
""")


SQL_INSERT_CONTACT = text("""
    INSERT INTO contact (
        id,
        email,
        phone
    )
    VALUES (
        :contact_id,
        :email,
        :phone
    )
""")


SQL_INSERT_PERSON = text("""
    INSERT INTO person (
        id,
        fk_users,
        fk_contact,
        name,
        cpf,
        birth_date
    )
    VALUES (
        :person_id,
        :users_id,
        :contact_id,
        :name,
        :cpf,
        :birth_date
    )
""")


SQL_INSERT_MAPEAMENTO = text("""
    INSERT INTO rpa_id_mapping (
        origem_tabela,
        origem_id,
        destino_tabela,
        destino_id
    )
    VALUES (
        'usuario',
        :id_origem,
        'person',
        :person_id
    )

    ON CONFLICT (
        origem_tabela,
        origem_id,
        destino_tabela
    )
    DO NOTHING
""")


def criar_tabela_mapeamento_se_nao_existir():

    with engine_destino.begin() as conn:
        conn.execute(SQL_CRIAR_MAPEAMENTO)


def carregar(df: pd.DataFrame):

    if df.empty:
        logger.info("Nada para carregar no destino.")
        return

    registros = df.to_dict(
        orient="records"
    )

    with engine_destino.begin() as conn:

        conn.execute(
            SQL_INSERT_USERS,
            registros,
        )

        conn.execute(
            SQL_INSERT_CONTACT,
            registros,
        )

        conn.execute(
            SQL_INSERT_PERSON,
            registros,
        )

        conn.execute(
            SQL_INSERT_MAPEAMENTO,
            registros,
        )

    logger.info(
        "%s pessoas gravadas no destino.",
        len(registros),
    )