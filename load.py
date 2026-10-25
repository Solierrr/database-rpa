import logging

import pandas as pd
from sqlalchemy import text

from db import destination_transaction, engine_destino
from id_mapping import get_mapping
from schema_v29 import unique_username


logger = logging.getLogger(__name__)


SQL_INSERT_USERS = text("""
    INSERT INTO user_account (id, auth_id, username, avatar)
    VALUES (:user_id, :auth_id, :username, :avatar)
""")

SQL_INSERT_CONTACT = text("""
    INSERT INTO contact (id, email, phone)
    VALUES (:contact_id, :email, :phone)
""")

SQL_INSERT_PERSON = text("""
    INSERT INTO person (id, user_id, contact_id, name, cpf, birth_date)
    VALUES (:person_id, :user_id, :contact_id, :name, :cpf, :birth_date)
""")


def carregar(df: pd.DataFrame):
    if df.empty:
        logger.info("Nada para carregar no destino.")
        return

    registros = df.to_dict(orient="records")

    with engine_destino.connect() as conn:
        usernames = {row[0] for row in conn.execute(text("SELECT username FROM user_account"))}
    for registro in registros:
        registro["username"] = unique_username(usernames, registro["username_base"])

    mapping = get_mapping()

    with destination_transaction() as conn:
        conn.execute(SQL_INSERT_USERS, registros)
        conn.execute(SQL_INSERT_CONTACT, registros)
        conn.execute(SQL_INSERT_PERSON, registros)
        for registro in registros:
            for destino_tabela, destino_id in (
                ("user_account", registro["user_id"]),
                ("contact", registro["contact_id"]),
                ("person", registro["person_id"]),
            ):
                mapping.save("usuario", registro["id_origem"], destino_tabela, destino_id)

    logger.info("%s pessoas gravadas no destino.", len(registros))
