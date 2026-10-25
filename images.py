"""Imagens do Cloudinary para os registros migrados.

O legado não traz fotos, então usuários, empresas e modelos migrados recebem imagens do `mocks-warehouse`
(as mesmas categorias do seed do `database-console`). A escolha é determinística por registro e só insere
quando o registro ainda não tem foto, então reexecutar o ETL não duplica nada.

Configuração (opcional; sem ela o passo é pulado):
    CLOUDINARY_CLOUD_NAME  nome da cloud
    MOCKS_MANIFEST         caminho do manifest.json (padrão: ../mocks-warehouse/manifest.json)
    MOCKS_PUBLIC_PREFIX    prefixo dos public ids (padrão: mocks)
"""
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "mocks-warehouse" / "manifest.json"
USER_CATEGORY = {"professional": "users/pfp/professionals", "supplier": "users/pfp/suitman", "client": "users/pfp/clients"}
BANNER_CATEGORY = {"SUPPLIER": "enterprises/banners/solar", "REQUESTER": "enterprises/banners/corporate"}
MODEL_PRIMARY = "products/solar-panels/hero"
MODEL_GALLERY = "products/solar-panels/demo"
GALLERY_SIZE = 2


class ImageCatalog:
    """Imagens do manifest por categoria, com escolha determinística por chave."""

    def __init__(self, assets, cloud_name, prefix="mocks"):
        self.cloud_name = cloud_name
        self.prefix = prefix
        self.by_category = {}
        self.crops = {}
        for asset in assets:
            self.by_category.setdefault(asset["category"], []).append(asset["id"])
            crop = asset.get("attributes", {}).get("crop")
            if crop:
                self.crops[asset["id"]] = crop
        for ids in self.by_category.values():
            ids.sort()

    def pick(self, category, key, offset=0):
        ids = self.by_category.get(category)
        if not ids:
            return None
        digest = int(hashlib.sha256(f"{category}:{key}".encode("utf-8")).hexdigest()[:12], 16)
        return ids[(digest + offset) % len(ids)]

    def url(self, asset_id):
        return f"https://res.cloudinary.com/{self.cloud_name}/image/upload/{self.prefix}/{asset_id}.webp"

    def public_id(self, asset_id):
        return f"{self.prefix}/{asset_id}"

    def crop_columns(self, asset_id):
        crop = self.crops.get(asset_id)
        if not crop:
            return {"crop_x": None, "crop_y": None, "crop_width": None, "crop_height": None}
        return {"crop_x": crop["x"], "crop_y": crop["y"], "crop_width": crop["width"], "crop_height": crop["height"]}


def load_catalog(environ=None):
    """Catálogo configurado pelo ambiente, ou None (com aviso) se a cloud ou o manifest não existirem."""
    environ = os.environ if environ is None else environ
    cloud_name = environ.get("CLOUDINARY_CLOUD_NAME")
    manifest = Path(environ.get("MOCKS_MANIFEST") or DEFAULT_MANIFEST)
    if not cloud_name:
        logger.warning("CLOUDINARY_CLOUD_NAME não definido: imagens não serão ligadas aos registros migrados.")
        return None
    if not manifest.is_file():
        logger.warning("Manifest de imagens não encontrado em %s: imagens não serão ligadas.", manifest)
        return None
    assets = json.loads(manifest.read_text(encoding="utf-8"))["assets"]
    return ImageCatalog(assets, cloud_name, environ.get("MOCKS_PUBLIC_PREFIX", "mocks"))


def _photo_row(catalog, asset_id, **fields):
    return {"id": str(uuid.uuid4()), "url": catalog.url(asset_id), "public_id": catalog.public_id(asset_id), **fields}


def _query(conn, sql, ids):
    from sqlalchemy import bindparam, text

    if not ids:
        return []
    return conn.execute(text(sql).bindparams(bindparam("ids", expanding=True)), {"ids": ids}).mappings().all()


def attach_images(conn, catalog, mapping):
    """Liga imagens a usuários, empresas e modelos migrados que ainda não têm foto. Devolve as contagens."""
    from sqlalchemy import text

    counts = {"user_photo": 0, "company_photo": 0, "model_photo": 0}

    users = _query(conn, """
        SELECT u.id,
               EXISTS (SELECT 1 FROM person p JOIN technician t ON t.person_id = p.id WHERE p.user_id = u.id) AS professional,
               EXISTS (SELECT 1 FROM user_company uc JOIN company c ON c.id = uc.company_id
                       WHERE uc.user_id = u.id AND c.type = 'SUPPLIER') AS supplier
        FROM user_account u
        WHERE u.id IN :ids
          AND NOT EXISTS (SELECT 1 FROM user_photo up WHERE up.user_id = u.id AND up.type = 'PROFILE')
    """, mapping.destination_ids("usuario", "user_account"))
    for user in users:
        kind = "professional" if user["professional"] else ("supplier" if user["supplier"] else "client")
        asset = catalog.pick(USER_CATEGORY[kind], user["id"])
        if asset:
            conn.execute(text("""
                INSERT INTO user_photo (id, user_id, type, url, public_id, created_at, crop_x, crop_y, crop_width, crop_height)
                VALUES (:id, :user, 'PROFILE', :url, :public_id, now(), :crop_x, :crop_y, :crop_width, :crop_height)
            """), _photo_row(catalog, asset, user=user["id"], **catalog.crop_columns(asset)))
            counts["user_photo"] += 1

    company_ids = sorted(
        set(mapping.destination_ids("fornecedor", "company")) | set(mapping.destination_ids("empresa_demandante", "company"))
    )
    companies = _query(conn, """
        SELECT c.id, c.type
        FROM company c
        WHERE c.id IN :ids
          AND NOT EXISTS (SELECT 1 FROM company_photo cp WHERE cp.company_id = c.id)
    """, company_ids)
    for company in companies:
        for kind, category in (("PROFILE", "enterprises/pfp"), ("BANNER", BANNER_CATEGORY[company["type"]])):
            asset = catalog.pick(category, company["id"])
            if asset:
                conn.execute(text("""
                    INSERT INTO company_photo (id, company_id, type, url, public_id, created_at, crop_x, crop_y, crop_width, crop_height)
                    VALUES (:id, :company, :type, :url, :public_id, now(), :crop_x, :crop_y, :crop_width, :crop_height)
                """), _photo_row(catalog, asset, company=company["id"], type=kind, **catalog.crop_columns(asset)))
                counts["company_photo"] += 1

    models = _query(conn, """
        SELECT m.id
        FROM model m
        WHERE m.id IN :ids
          AND NOT EXISTS (SELECT 1 FROM model_photo mp WHERE mp.model_id = m.id)
    """, mapping.destination_ids("produto", "model"))
    for model in models:
        chosen = [(catalog.pick(MODEL_PRIMARY, model["id"]), True)]
        chosen += [(catalog.pick(MODEL_GALLERY, model["id"], position), False) for position in range(GALLERY_SIZE)]
        for asset, primary in chosen:
            if asset:
                conn.execute(text("""
                    INSERT INTO model_photo (id, model_id, url, public_id, created_at, is_primary)
                    VALUES (:id, :model, :url, :public_id, now(), :primary)
                """), _photo_row(catalog, asset, model=model["id"], primary=primary))
                counts["model_photo"] += 1
    return counts


def executar_imagens():
    from db import engine_destino
    from id_mapping import get_mapping

    catalog = load_catalog()
    if catalog is None:
        return
    with engine_destino.begin() as conn:
        counts = attach_images(conn, catalog, get_mapping())
    logger.info("Imagens ligadas: %s", counts)
