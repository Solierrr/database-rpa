import logging
import uuid

import pandas as pd

from mock_data import mock_birth_date, mock_cpf


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
            "users_id": str(uuid.uuid4()),
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
