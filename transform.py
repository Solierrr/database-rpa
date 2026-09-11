import logging
import uuid

import pandas as pd

from faker import Faker

from config import FAKER_LOCALE


logger = logging.getLogger(__name__)

fake = Faker(FAKER_LOCALE)


def _cpf_somente_digitos():
    return (
        fake.cpf()
        .replace(".", "")
        .replace("-", "")
    )


def transformar(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    registros = []

    for _, row in df.iterrows():

        registros.append({

            # ==================================
            # CONTROLE DO RPA
            # ==================================

            "id_origem": row["id"],

            "tipo_usuario": row["tipo_usuario"],

            "raio_procura_km": row["raio_procura_km"],


            # ==================================
            # IDs DO NOVO BANCO
            # ==================================

            "users_id": str(uuid.uuid4()),

            "contact_id": str(uuid.uuid4()),

            "person_id": str(uuid.uuid4()),


            # ==================================
            # USERS
            # ==================================

            "avatar": None,


            # ==================================
            # CONTACT
            # ==================================

            "email": str(row["email"])[:100],

            "phone": None,


            # ==================================
            # PERSON
            # ==================================

            "name": str(row["nome"])[:60],

            "cpf": _cpf_somente_digitos(),

            "birth_date": fake.date_of_birth(
                minimum_age=18,
                maximum_age=75,
            ).isoformat(),

        })

    resultado = pd.DataFrame(registros)

    logger.info(
        "%s usuários transformados.",
        len(resultado),
    )

    return resultado