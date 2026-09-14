"""Mocks determinísticos para campos obrigatórios ausentes no legado.

Uma mesma entidade/ID sempre gera o mesmo valor. Isso permite reexecuções
previsíveis e deixa explícito o que não veio do banco primário.
"""
import hashlib
from datetime import date, datetime, timedelta, timezone

from faker import Faker

from config import FAKER_LOCALE


def _seed(entity: str, legacy_id) -> int:
    value = f"{entity}:{legacy_id}".encode("utf-8")
    digest = hashlib.sha256(value).hexdigest()
    return int(digest[:12], 16)


def _faker(entity: str, legacy_id) -> Faker:
    fake = Faker(FAKER_LOCALE)
    fake.seed_instance(_seed(entity, legacy_id))
    return fake


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def mock_cpf(usuario_id) -> str:
    return _digits(_faker("usuario_cpf", usuario_id).cpf())[:11]


def mock_birth_date(usuario_id):
    first_date = date(1950, 1, 1)
    last_date = date(2007, 12, 31)
    interval = (last_date - first_date).days + 1
    days = _seed("usuario_nascimento", usuario_id) % interval
    return first_date + timedelta(days=days)


def mock_postcode(endereco_id) -> str:
    return _digits(_faker("endereco_cep", endereco_id).postcode()).zfill(8)[:8]


def mock_cnpj(origem_tabela: str, origem_id) -> str:
    return _digits(_faker(f"{origem_tabela}_cnpj", origem_id).cnpj())[:14]


def mock_start_date(origem_tabela: str, origem_id):
    base = datetime(2020, 1, 1, tzinfo=timezone.utc)
    days = _seed(f"{origem_tabela}_inicio", origem_id) % 2192
    return base + timedelta(days=days)
