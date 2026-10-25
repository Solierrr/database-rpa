import logging
import uuid

import pandas as pd

from mock_data import mock_birth_date, mock_cpf
from schema_v29 import new_auth_id, username_from


logger = logging.getLogger(__name__)


def transformar(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma usuários V8 nos três registros exigidos pelo destino."""
    if df.empty:
        return df

    registros = []

    for _, row in df.iterrows():
        usuario_id = int(row["id"])
        registros.append({
            "id_origem": usuario_id,
            "tipo_usuario": row["tipo_usuario"],
            "raio_procura_km": row["raio_procura_km"],
            "user_id": str(uuid.uuid4()),
            "auth_id": new_auth_id(),
            "username_base": username_from(row["email"], row["nome"], usuario_id),
            "contact_id": str(uuid.uuid4()),
            "person_id": str(uuid.uuid4()),
            "avatar": None,
            "email": str(row["email"])[:100],
            "phone": None,
            "name": str(row["nome"])[:60],
            # Não existem no legado e são obrigatórios no destino.
            "cpf": mock_cpf(usuario_id),
            "birth_date": mock_birth_date(usuario_id),
        })

    resultado = pd.DataFrame(registros)
    logger.info("%s usuários transformados.", len(resultado))
    return resultado
