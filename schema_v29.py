"""Regras do schema V29 do coredb que o ETL precisa respeitar ao gravar direto no banco.

O banco de destino exige valores que o legado não tem (slug, username, tipo da empresa, marca do modelo).
Tudo que é derivado aqui é determinístico, para que reexecuções do ETL deem o mesmo resultado.
"""
import re
import unicodedata
import uuid

OWNER_POSITION = "ADMIN"
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,30}$")


def slugify(value, max_len=160, fallback="item"):
    """Texto em minúsculas, sem acento, só letras, números e hífen."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return (slug or fallback)[:max_len].strip("-") or fallback


def unique_slug(conn, table, base, max_len=160):
    """Devolve `base`, ou `base-2`, `base-3`... até não existir em `table.slug`."""
    from sqlalchemy import text

    if table not in {"company", "technician", "offer"}:
        raise ValueError(f"Tabela sem slug: {table}")
    base = slugify(base, max_len - 6)
    candidate, counter = base, 1
    while conn.execute(text(f"SELECT 1 FROM {table} WHERE slug = :slug"), {"slug": candidate}).scalar():
        counter += 1
        candidate = f"{base}-{counter}"
    return candidate


def username_from(email, name, legacy_id):
    """Username válido (`^[a-z0-9_]{3,30}$`) a partir do e-mail, ou do nome, ou do id legado."""
    source = str(email or "").split("@")[0] or str(name or "")
    normalized = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode("ascii").lower()
    username = re.sub(r"[^a-z0-9_]+", "_", normalized).strip("_")[:30]
    if len(username) < 3:
        username = f"usuario_{legacy_id}"[:30]
    return username


def unique_username(taken, base):
    """Garante unicidade dentro de `taken` (conjunto já em uso) e registra o escolhido."""
    candidate, counter = base, 1
    while candidate in taken:
        counter += 1
        suffix = f"_{counter}"
        candidate = f"{base[:30 - len(suffix)]}{suffix}"
    taken.add(candidate)
    return candidate


def new_auth_id():
    """`users.auth_id` aponta para a conta no authdb. O ETL não escreve no authdb: gera um id sem conta,
    então o usuário migrado só consegue entrar depois que uma conta com esse id for criada."""
    return str(uuid.uuid4())


def get_or_create_legacy_brand(conn, name):
    """Marca do fabricante do legado. Marcas sem empresa dona precisam de `legacy = true` (restrição do schema)."""
    from sqlalchemy import text

    display = (str(name).strip() if name and str(name).strip() else "Não informado")[:255]
    normalized = re.sub(r"\s+", " ", display).lower()
    brand_id = conn.execute(
        text("SELECT id FROM brand WHERE normalized_name = :normalized ORDER BY created_at LIMIT 1"),
        {"normalized": normalized},
    ).scalar()
    if brand_id:
        return brand_id
    brand_id = str(uuid.uuid4())
    conn.execute(
        text("""
            INSERT INTO brand (id, name, normalized_name, visibility, legacy)
            VALUES (:id, :name, :normalized, 'PRIVATE', true)
        """),
        {"id": brand_id, "name": display, "normalized": normalized},
    )
    return brand_id
