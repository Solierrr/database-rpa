"""Migrações complementares do legado V8 para o schema Solaria.

O módulo usa rpa_id_mapping para manter idempotência e preservar relações
BIGINT -> UUID. Dados inexistentes na origem só recebem mock/default quando
uma coluna obrigatória do destino exige isso.
"""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

import pandas as pd
from sqlalchemy import text

from db import engine_destino, engine_origem
from mock_data import mock_cnpj, mock_postcode, mock_start_date


logger = logging.getLogger(__name__)
DEFAULT_LOCATION_TYPE = "COMPLEX"


def _uuid() -> str:
    return str(uuid.uuid4())


def _digits(value, max_len=None):
    if value is None or pd.isna(value):
        return None
    result = "".join(character for character in str(value) if character.isdigit())
    return result[:max_len] if max_len else result


def _txt(value, max_len=None, fallback=None):
    if value is None or pd.isna(value) or not str(value).strip():
        value = fallback
    if value is None:
        return None
    result = str(value).strip()
    return result[:max_len] if max_len else result


def _mapping(origem_tabela: str, origem_id, destino_tabela: str, conn=None):
    query = text("""
        SELECT destino_id
        FROM rpa_id_mapping
        WHERE origem_tabela = :origem_tabela
          AND origem_id = :origem_id
          AND destino_tabela = :destino_tabela
    """)
    params = {
        "origem_tabela": origem_tabela,
        "origem_id": int(origem_id),
        "destino_tabela": destino_tabela,
    }
    if conn is not None:
        return conn.execute(query, params).scalar()
    with engine_destino.connect() as connection:
        return connection.execute(query, params).scalar()


def _save_mapping(conn, origem_tabela, origem_id, destino_tabela, destino_id):
    conn.execute(
        text("""
            INSERT INTO rpa_id_mapping (
                origem_tabela, origem_id, destino_tabela, destino_id
            )
            VALUES (:origem_tabela, :origem_id, :destino_tabela, :destino_id)
            ON CONFLICT (origem_tabela, origem_id, destino_tabela) DO NOTHING
        """),
        {
            "origem_tabela": origem_tabela,
            "origem_id": int(origem_id),
            "destino_tabela": destino_tabela,
            "destino_id": destino_id,
        },
    )


def _person_ids(usuario_id, conn=None):
    """Obtém person/users/contact e recupera mappings de versões antigas."""
    person_id = _mapping("usuario", usuario_id, "person", conn)
    if not person_id:
        return None, None, None

    users_id = _mapping("usuario", usuario_id, "users", conn)
    contact_id = _mapping("usuario", usuario_id, "contact", conn)

    if not users_id or not contact_id:
        query = text("SELECT fk_users, fk_contact FROM person WHERE id = :id")
        if conn is not None:
            row = conn.execute(query, {"id": person_id}).mappings().first()
        else:
            with engine_destino.connect() as connection:
                row = connection.execute(query, {"id": person_id}).mappings().first()
        if not row:
            return None, None, None
        users_id = users_id or row["fk_users"]
        contact_id = contact_id or row["fk_contact"]

        if conn is not None:
            if users_id:
                _save_mapping(conn, "usuario", usuario_id, "users", users_id)
            if contact_id:
                _save_mapping(conn, "usuario", usuario_id, "contact", contact_id)

    return person_id, users_id, contact_id


def migrar_telefones():
    df = pd.read_sql(
        """
        SELECT id, id_usuario, telefone, principal
        FROM telefone
        ORDER BY principal DESC, id
        """,
        engine_origem,
    )
    atualizados = 0
    usuarios_vistos = set()

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            usuario_id = int(row["id_usuario"])
            if usuario_id in usuarios_vistos:
                continue

            _, _, contact_id = _person_ids(usuario_id, conn)
            phone = _digits(row["telefone"], 12)
            if not contact_id or not phone:
                continue

            conn.execute(
                text("UPDATE contact SET phone = :phone WHERE id = :id"),
                {"phone": phone, "id": contact_id},
            )
            _save_mapping(conn, "telefone", row["id"], "contact", contact_id)
            usuarios_vistos.add(usuario_id)
            atualizados += 1

    logger.info("Telefones migrados: %s", atualizados)


def migrar_perfis():
    df = pd.read_sql(
        "SELECT id, id_usuario, foto_perfil FROM perfil ORDER BY id",
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("perfil", row["id"], "users", conn):
                continue

            _, users_id, _ = _person_ids(row["id_usuario"], conn)
            if not users_id:
                continue

            avatar = _txt(row["foto_perfil"])
            if avatar:
                conn.execute(
                    text("UPDATE users SET avatar = :avatar WHERE id = :id"),
                    {"avatar": avatar, "id": users_id},
                )
            _save_mapping(conn, "perfil", row["id"], "users", users_id)
            total += 1

    logger.info("Perfis migrados: %s", total)


def migrar_enderecos():
    df = pd.read_sql(
        """
        SELECT id, id_usuario, estado, cidade, bairro, cep,
               logradouro, numero, complemento
        FROM endereco
        ORDER BY id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("endereco", row["id"], "address", conn):
                continue

            address_id = _uuid()
            zip_code = _digits(row["cep"], 8) or mock_postcode(row["id"])
            conn.execute(
                text("""
                    INSERT INTO address (
                        id, state, city, neighborhood, zip_code, street, number
                    )
                    VALUES (
                        :id, :state, :city, :neighborhood, :zip_code, :street, :number
                    )
                """),
                {
                    "id": address_id,
                    "state": _txt(row["estado"], 2, "SP").upper(),
                    "city": _txt(row["cidade"], fallback="São Paulo"),
                    "neighborhood": _txt(row["bairro"]),
                    "zip_code": zip_code.zfill(8)[:8],
                    "street": _txt(row["logradouro"], fallback="Endereço não informado"),
                    "number": _txt(row["numero"], 10, "S/N"),
                },
            )
            _save_mapping(conn, "endereco", row["id"], "address", address_id)
            total += 1

    logger.info("Endereços migrados: %s", total)


def _address_for_user(usuario_id, conn):
    addresses = pd.read_sql(
        text("SELECT id FROM endereco WHERE id_usuario = :usuario ORDER BY id LIMIT 1"),
        engine_origem,
        params={"usuario": int(usuario_id)},
    )
    if not addresses.empty:
        address_id = _mapping("endereco", int(addresses.iloc[0]["id"]), "address", conn)
        if address_id:
            return address_id

    # address é obrigatório no destino e não há endereço correspondente no legado.
    address_id = _uuid()
    conn.execute(
        text("""
            INSERT INTO address (
                id, state, city, neighborhood, zip_code, street, number
            )
            VALUES (
                :id, 'SP', 'São Paulo', NULL, '00000000',
                'Endereço não informado', 'S/N'
            )
        """),
        {"id": address_id},
    )
    return address_id


def _create_company_for_legacy(
    conn,
    origem_tabela,
    origem_id,
    usuario_id,
    cnpj,
    razao_social,
):
    existing = _mapping(origem_tabela, origem_id, "company", conn)
    if existing:
        return existing

    normalized_cnpj = _digits(cnpj, 14) or mock_cnpj(origem_tabela, origem_id)
    normalized_cnpj = normalized_cnpj.zfill(14)[:14]

    # Uma empresa pode exercer mais de um papel. Reutiliza company pelo CNPJ.
    company_row = conn.execute(
        text("""
            SELECT id, fk_business_contact
            FROM company
            WHERE cnpj = :cnpj
            LIMIT 1
        """),
        {"cnpj": normalized_cnpj},
    ).mappings().first()
    if company_row:
        _save_mapping(
            conn,
            origem_tabela,
            origem_id,
            "business_contact",
            company_row["fk_business_contact"],
        )
        _save_mapping(conn, origem_tabela, origem_id, "company", company_row["id"])
        return company_row["id"]

    _, _, contact_id = _person_ids(usuario_id, conn)
    email = None
    phone = None
    if contact_id:
        contact = conn.execute(
            text("SELECT email, phone FROM contact WHERE id = :id"),
            {"id": contact_id},
        ).mappings().first()
        if contact:
            email, phone = contact["email"], contact["phone"]

    business_contact_id = _uuid()
    company_id = _uuid()
    company_email = _txt(email, 100, f"empresa{origem_id}@migracao.local")
    conn.execute(
        text("""
            INSERT INTO business_contact (id, company_email, phone, website)
            VALUES (:id, :email, :phone, NULL)
        """),
        {
            "id": business_contact_id,
            "email": company_email,
            "phone": _txt(phone, 12),
        },
    )

    address_id = _address_for_user(usuario_id, conn)
    corporate_name = _txt(razao_social, 120, f"Empresa migrada {origem_id}")
    conn.execute(
        text("""
            INSERT INTO company (
                id, fk_address, fk_business_contact, cnpj,
                trade_name, corporate_name
            )
            VALUES (
                :id, :address, :business_contact, :cnpj,
                :trade_name, :corporate_name
            )
        """),
        {
            "id": company_id,
            "address": address_id,
            "business_contact": business_contact_id,
            "cnpj": normalized_cnpj,
            "trade_name": corporate_name,
            "corporate_name": corporate_name,
        },
    )
    _save_mapping(
        conn,
        origem_tabela,
        origem_id,
        "business_contact",
        business_contact_id,
    )
    _save_mapping(conn, origem_tabela, origem_id, "company", company_id)
    return company_id


def _get_or_create_position(conn, name: str, accesses: str = "DEFAULT"):
    position_id = conn.execute(
        text("SELECT id FROM position WHERE name = :name ORDER BY id LIMIT 1"),
        {"name": name},
    ).scalar()
    if position_id:
        return position_id

    position_id = _uuid()
    conn.execute(
        text("""
            INSERT INTO position (id, name, accesses)
            VALUES (:id, :name, :accesses)
        """),
        {"id": position_id, "name": name, "accesses": accesses},
    )
    return position_id


def _link_user_company(
    conn,
    origem_tabela,
    origem_id,
    usuario_id,
    company_id,
):
    if _mapping(origem_tabela, origem_id, "user_company", conn):
        return

    users_id = _mapping("usuario", usuario_id, "users", conn)
    if not users_id:
        _, users_id, _ = _person_ids(usuario_id, conn)
    if not users_id:
        logger.warning("Usuário %s sem mapping para users", usuario_id)
        return

    position_id = _get_or_create_position(conn, "OWNER")
    conn.execute(
        text("""
            INSERT INTO company_positions (id, fk_company, fk_position)
            VALUES (:id, :company, :position)
            ON CONFLICT (fk_company, fk_position) DO NOTHING
        """),
        {"id": _uuid(), "company": company_id, "position": position_id},
    )

    existing = conn.execute(
        text("""
            SELECT id
            FROM user_company
            WHERE fk_company = :company
              AND fk_users = :users
              AND fk_position = :position
            ORDER BY id
            LIMIT 1
        """),
        {"company": company_id, "users": users_id, "position": position_id},
    ).scalar()
    user_company_id = existing or _uuid()

    if not existing:
        conn.execute(
            text("""
                INSERT INTO user_company (id, fk_company, fk_users, fk_position)
                VALUES (:id, :company, :users, :position)
            """),
            {
                "id": user_company_id,
                "company": company_id,
                "users": users_id,
                "position": position_id,
            },
        )

    _save_mapping(
        conn,
        origem_tabela,
        origem_id,
        "user_company",
        user_company_id,
    )


def migrar_fornecedores():
    df = pd.read_sql(
        """
        SELECT id, id_usuario, tipo_fornecedor, cnpj, razao_social
        FROM fornecedor
        ORDER BY id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            company_id = _create_company_for_legacy(
                conn,
                "fornecedor",
                row["id"],
                row["id_usuario"],
                row["cnpj"],
                row["razao_social"],
            )
            supplier_id = _mapping("fornecedor", row["id"], "supplier", conn)
            if not supplier_id:
                supplier_id = _uuid()
                conn.execute(
                    text("""
                        INSERT INTO supplier (id, fk_company, status, business_type)
                        VALUES (:id, :company, 'ACTIVE', :business_type)
                    """),
                    {
                        "id": supplier_id,
                        "company": company_id,
                        "business_type": _txt(row["tipo_fornecedor"], 40),
                    },
                )
                _save_mapping(conn, "fornecedor", row["id"], "supplier", supplier_id)
                total += 1

            _link_user_company(
                conn,
                "fornecedor",
                row["id"],
                row["id_usuario"],
                company_id,
            )

    logger.info("Fornecedores migrados: %s", total)


def migrar_demandantes():
    df = pd.read_sql(
        "SELECT id, id_usuario, cnpj, razao_social FROM empresa_demandante ORDER BY id",
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            company_id = _create_company_for_legacy(
                conn,
                "empresa_demandante",
                row["id"],
                row["id_usuario"],
                row["cnpj"],
                row["razao_social"],
            )
            requester_id = _mapping(
                "empresa_demandante", row["id"], "requester", conn
            )
            if not requester_id:
                requester_id = _uuid()
                conn.execute(
                    text("""
                        INSERT INTO requester (id, fk_company, business_type)
                        VALUES (:id, :company, 'REQUESTER')
                    """),
                    {"id": requester_id, "company": company_id},
                )
                _save_mapping(
                    conn,
                    "empresa_demandante",
                    row["id"],
                    "requester",
                    requester_id,
                )
                total += 1

            _link_user_company(
                conn,
                "empresa_demandante",
                row["id"],
                row["id_usuario"],
                company_id,
            )

    logger.info("Demandantes migrados: %s", total)


def migrar_unidades_locais():
    df = pd.read_sql(
        """
        SELECT
            ed.id AS empresa_demandante_id,
            e.id AS endereco_id,
            e.complemento
        FROM empresa_demandante ed
        INNER JOIN endereco e ON e.id_usuario = ed.id_usuario
        ORDER BY ed.id, e.id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("endereco", row["endereco_id"], "local_unit", conn):
                continue

            requester_id = _mapping(
                "empresa_demandante",
                row["empresa_demandante_id"],
                "requester",
                conn,
            )
            address_id = _mapping("endereco", row["endereco_id"], "address", conn)
            if not requester_id or not address_id:
                logger.warning(
                    "Unidade ignorada: demandante %s ou endereço %s sem mapping",
                    row["empresa_demandante_id"],
                    row["endereco_id"],
                )
                continue

            local_unit_id = _uuid()
            conn.execute(
                text("""
                    INSERT INTO local_unit (
                        id, fk_requester, fk_address, complement, location_type
                    )
                    VALUES (
                        :id, :requester, :address, :complement, :location_type
                    )
                """),
                {
                    "id": local_unit_id,
                    "requester": requester_id,
                    "address": address_id,
                    "complement": _txt(row["complemento"]),
                    "location_type": DEFAULT_LOCATION_TYPE,
                },
            )
            _save_mapping(
                conn,
                "endereco",
                row["endereco_id"],
                "local_unit",
                local_unit_id,
            )
            total += 1

    logger.info("Unidades locais migradas: %s", total)


def migrar_projetos_tecnicos():
    df = pd.read_sql(
        """
        SELECT DISTINCT ON (p.id)
            p.id AS projeto_id,
            up.id_usuario
        FROM projeto p
        INNER JOIN usuario_projeto up ON up.id_projeto = p.id
        WHERE up.dono_do_projeto = true
        ORDER BY p.id, up.id_usuario
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("projeto", row["projeto_id"], "technical_project", conn):
                continue

            demandante = pd.read_sql(
                text("""
                    SELECT id
                    FROM empresa_demandante
                    WHERE id_usuario = :usuario
                    LIMIT 1
                """),
                engine_origem,
                params={"usuario": int(row["id_usuario"])},
            )
            if demandante.empty:
                logger.warning(
                    "Projeto %s ignorado: dono não é demandante",
                    row["projeto_id"],
                )
                continue

            demandante_id = int(demandante.iloc[0]["id"])
            requester_id = _mapping(
                "empresa_demandante", demandante_id, "requester", conn
            )
            if not requester_id:
                continue

            local_unit_id = conn.execute(
                text("""
                    SELECT id
                    FROM local_unit
                    WHERE fk_requester = :requester
                    ORDER BY id
                    LIMIT 1
                """),
                {"requester": requester_id},
            ).scalar()
            if not local_unit_id:
                logger.warning("Projeto %s sem local_unit", row["projeto_id"])
                continue

            project_id = _uuid()
            conn.execute(
                text("""
                    INSERT INTO technical_project (
                        id, fk_requester, fk_local_unit, status, start_date, end_date
                    )
                    VALUES (
                        :id, :requester, :local_unit, 'OPEN', :start_date, NULL
                    )
                """),
                {
                    "id": project_id,
                    "requester": requester_id,
                    "local_unit": local_unit_id,
                    "start_date": mock_start_date("projeto", row["projeto_id"]),
                },
            )
            _save_mapping(
                conn,
                "projeto",
                row["projeto_id"],
                "technical_project",
                project_id,
            )
            total += 1

    logger.info("Projetos técnicos migrados: %s", total)


def migrar_profissionais():
    df = pd.read_sql(
        """
        SELECT id, id_usuario, profissao, cpf, id_fornecedor
        FROM profissional
        ORDER BY id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            person_id, _, _ = _person_ids(row["id_usuario"], conn)
            if not person_id:
                continue

            cpf = _digits(row["cpf"], 11)
            if cpf and len(cpf) == 11:
                conflict = conn.execute(
                    text("SELECT id FROM person WHERE cpf = :cpf AND id <> :id"),
                    {"cpf": cpf, "id": person_id},
                ).scalar()
                if not conflict:
                    conn.execute(
                        text("UPDATE person SET cpf = :cpf WHERE id = :id"),
                        {"cpf": cpf, "id": person_id},
                    )

            technician_id = _mapping("profissional", row["id"], "technician", conn)
            if not technician_id:
                technician_id = _uuid()
                conn.execute(
                    text("INSERT INTO technician (id, fk_person) VALUES (:id, :person)"),
                    {"id": technician_id, "person": person_id},
                )
                _save_mapping(
                    conn, "profissional", row["id"], "technician", technician_id
                )
                total += 1

            profession_name = _txt(row["profissao"], 100, "Profissional")
            profession_id = conn.execute(
                text("SELECT id FROM profession WHERE name = :name"),
                {"name": profession_name},
            ).scalar()
            if not profession_id:
                profession_id = _uuid()
                conn.execute(
                    text("""
                        INSERT INTO profession (id, name, requires_registration)
                        VALUES (:id, :name, false)
                    """),
                    {"id": profession_id, "name": profession_name},
                )
            _save_mapping(
                conn, "profissional", row["id"], "profession", profession_id
            )

            fornecedor_id = row.get("id_fornecedor")
            if fornecedor_id is None or pd.isna(fornecedor_id):
                continue
            company_id = _mapping(
                "fornecedor", int(fornecedor_id), "company", conn
            )
            if not company_id:
                continue

            affiliation_id = conn.execute(
                text("""
                    SELECT id
                    FROM technician_affiliation
                    WHERE fk_company = :company AND fk_technician = :technician
                    LIMIT 1
                """),
                {"company": company_id, "technician": technician_id},
            ).scalar()
            if not affiliation_id:
                affiliation_id = _uuid()
                conn.execute(
                    text("""
                        INSERT INTO technician_affiliation (
                            id, fk_company, fk_technician, affiliation_type
                        )
                        VALUES (:id, :company, :technician, 'AFFILIATED')
                    """),
                    {
                        "id": affiliation_id,
                        "company": company_id,
                        "technician": technician_id,
                    },
                )
            _save_mapping(
                conn,
                "profissional",
                row["id"],
                "technician_affiliation",
                affiliation_id,
            )

    logger.info("Profissionais migrados: %s", total)


def _cycle(value):
    normalized = str(value or "").upper()
    if "SEM" in normalized or "WEEK" in normalized:
        return "WEEKLY"
    if "ANO" in normalized or "ANU" in normalized or "YEAR" in normalized:
        return "YEARLY"
    return "MONTHLY"


def migrar_planos():
    df = pd.read_sql(
        "SELECT id, nome, valor, tipo_mensalidade FROM plano ORDER BY id",
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("plano", row["id"], "company_plans", conn):
                continue
            plan_id = _uuid()
            value = Decimal("0") if pd.isna(row["valor"]) else Decimal(str(row["valor"]))
            conn.execute(
                text("""
                    INSERT INTO company_plans (id, name, value, cycle)
                    VALUES (:id, :name, :value, :cycle)
                """),
                {
                    "id": plan_id,
                    "name": _txt(row["nome"], fallback=f"Plano {row['id']}"),
                    "value": value,
                    "cycle": _cycle(row["tipo_mensalidade"]),
                },
            )
            _save_mapping(conn, "plano", row["id"], "company_plans", plan_id)
            total += 1

    logger.info("Planos migrados: %s", total)


def _supplier_by_user(usuario_id, conn):
    supplier = pd.read_sql(
        text("SELECT id FROM fornecedor WHERE id_usuario = :usuario LIMIT 1"),
        engine_origem,
        params={"usuario": int(usuario_id)},
    )
    if supplier.empty:
        return None
    return _mapping("fornecedor", int(supplier.iloc[0]["id"]), "supplier", conn)


def migrar_assinaturas():
    df = pd.read_sql(
        """
        SELECT id, id_usuario, id_plano, status_assinatura,
               renovacao_automatica, data_inicio, validade
        FROM assinatura
        ORDER BY id
        """,
        engine_origem,
    )
    total = 0
    status_map = {
        "ATIVA": "PAID",
        "PAGA": "PAID",
        "INADIMPLENTE": "IN_DEBT",
        "SUSPENSA": "SUSPENDED",
    }

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("assinatura", row["id"], "subscription", conn):
                continue

            supplier_id = _supplier_by_user(row["id_usuario"], conn)
            plan_id = _mapping("plano", row["id_plano"], "company_plans", conn)
            if not supplier_id or not plan_id:
                logger.warning(
                    "Assinatura %s ignorada: destino exige supplier e plano",
                    row["id"],
                )
                continue

            subscription_id = _uuid()
            status = status_map.get(str(row["status_assinatura"]).upper(), "PAID")
            start = (
                mock_start_date("assinatura", row["id"])
                if pd.isna(row["data_inicio"])
                else row["data_inicio"]
            )
            end = None if pd.isna(row["validade"]) else row["validade"]
            auto_renewal = (
                True
                if pd.isna(row["renovacao_automatica"])
                else bool(row["renovacao_automatica"])
            )
            conn.execute(
                text("""
                    INSERT INTO subscription (
                        id, fk_supplier, fk_plan, status, auto_renewal,
                        start_date, end_date
                    )
                    VALUES (
                        :id, :supplier, :plan, :status, :auto_renewal,
                        :start_date, :end_date
                    )
                """),
                {
                    "id": subscription_id,
                    "supplier": supplier_id,
                    "plan": plan_id,
                    "status": status,
                    "auto_renewal": auto_renewal,
                    "start_date": start,
                    "end_date": end,
                },
            )
            _save_mapping(
                conn,
                "assinatura",
                row["id"],
                "subscription",
                subscription_id,
            )
            total += 1

    logger.info("Assinaturas migradas: %s", total)


def contar_produtos_sem_equipamento() -> int:
    df = pd.read_sql(
        """
        SELECT COUNT(*) AS total
        FROM produto p
        LEFT JOIN equipamento_eletrico e ON e.id_produto = p.id
        WHERE e.id IS NULL
        """,
        engine_origem,
    )
    return int(df.iloc[0]["total"])


def migrar_produtos():
    ignorados = contar_produtos_sem_equipamento()
    if ignorados:
        logger.warning(
            "%s produtos ignorados por não possuírem equipamento_eletrico",
            ignorados,
        )

    df = pd.read_sql(
        """
        SELECT
            p.id, p.id_fornecedor, p.nome, p.quantidade_em_estoque,
            p.fabricante, p.preco, e.altura_mm, e.largura_mm,
            e.comprimento_mm, e.potencia_w, e.peso_kg, e.eficiencia
        FROM produto p
        INNER JOIN equipamento_eletrico e ON e.id_produto = p.id
        ORDER BY p.id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if _mapping("produto", row["id"], "model", conn):
                continue
            supplier_id = _mapping(
                "fornecedor", row["id_fornecedor"], "supplier", conn
            )
            if not supplier_id:
                continue

            height = Decimal(str(row["altura_mm"]))
            width = Decimal(str(row["largura_mm"]))
            length = Decimal(str(row["comprimento_mm"]))
            dimension = (height * width * length) / Decimal("1000000000")
            dimension = min(max(dimension, Decimal("0.001")), Decimal("99999.999"))
            power = Decimal(str(row["potencia_w"]))
            weight = Decimal(str(row["peso_kg"]))
            efficiency = (
                Decimal("0")
                if pd.isna(row["eficiencia"])
                else Decimal(str(row["eficiencia"]))
            )
            efficiency = min(max(efficiency, Decimal("0")), Decimal("100"))

            model_id = _uuid()
            conn.execute(
                text("""
                    INSERT INTO model (
                        id, brand, model, power_wp, efficiency,
                        dimension, weight, status
                    )
                    VALUES (
                        :id, :brand, :model, :power, :efficiency,
                        :dimension, :weight, 'UNDER_ANALYSIS'
                    )
                """),
                {
                    "id": model_id,
                    "brand": _txt(row["fabricante"], fallback="Não informado"),
                    "model": _txt(row["nome"], fallback=f"Produto {row['id']}"),
                    "power": power,
                    "efficiency": efficiency,
                    "dimension": dimension,
                    "weight": weight,
                },
            )

            quantity = (
                0
                if pd.isna(row["quantidade_em_estoque"])
                else max(int(row["quantidade_em_estoque"]), 0)
            )
            inventory_id = _uuid()
            offer_id = _uuid()
            conn.execute(
                text("""
                    INSERT INTO inventory (id, fk_supplier, fk_model, quantity)
                    VALUES (:id, :supplier, :model, :quantity)
                """),
                {
                    "id": inventory_id,
                    "supplier": supplier_id,
                    "model": model_id,
                    "quantity": quantity,
                },
            )
            price = (
                Decimal("0")
                if pd.isna(row["preco"])
                else max(Decimal(str(row["preco"])), Decimal("0"))
            )
            conn.execute(
                text("""
                    INSERT INTO offer (
                        id, fk_supplier, fk_model, unit_price, availability
                    )
                    VALUES (:id, :supplier, :model, :price, :availability)
                """),
                {
                    "id": offer_id,
                    "supplier": supplier_id,
                    "model": model_id,
                    "price": price,
                    "availability": quantity,
                },
            )
            _save_mapping(conn, "produto", row["id"], "model", model_id)
            _save_mapping(conn, "produto", row["id"], "inventory", inventory_id)
            _save_mapping(conn, "produto", row["id"], "offer", offer_id)
            total += 1

    logger.info("Produtos migrados: %s", total)


def _qualification_kind(row) -> str:
    values = (
        row.get("tipo_credencial"),
        row.get("nome"),
        row.get("orgao_expeditor"),
    )
    description = " ".join(str(value or "") for value in values).upper()
    registration_markers = (
        "CREA",
        "CAU",
        "CFT",
        "CRT",
        "CONSELHO",
        "REGISTRO PROFISSIONAL",
    )
    return (
        "REGISTRATION"
        if any(marker in description for marker in registration_markers)
        else "CERTIFICATION"
    )


def _certification_information(row) -> str:
    parts = [_txt(row.get("nome"), fallback="Qualificação migrada")]
    optional = {
        "Órgão": row.get("orgao_expeditor"),
        "Registro": row.get("numero_registro"),
        "NR": row.get("numero_nr"),
        "Fabricante": row.get("fabricante_certificado"),
        "Carga horária": row.get("carga_horaria_curso"),
        "Emissão": row.get("data_emissao"),
        "Validade": row.get("validade"),
    }
    for label, value in optional.items():
        if value is not None and not pd.isna(value) and str(value).strip():
            parts.append(f"{label}: {value}")
    return " | ".join(parts)


def migrar_qualificacoes():
    df = pd.read_sql(
        """
        SELECT
            id, id_profissional, orgao_expeditor, nome, tipo_credencial,
            data_emissao, validade, carga_horaria_curso, numero_registro,
            documento, numero_nr, fabricante_certificado
        FROM qualificacao
        ORDER BY id
        """,
        engine_origem,
    )
    total = 0

    with engine_destino.begin() as conn:
        for row in df.to_dict("records"):
            if (
                _mapping("qualificacao", row["id"], "certification", conn)
                or _mapping(
                    "qualificacao", row["id"], "professional_registration", conn
                )
            ):
                continue

            technician_id = _mapping(
                "profissional", row["id_profissional"], "technician", conn
            )
            if not technician_id:
                continue

            if _qualification_kind(row) == "REGISTRATION":
                profession_id = _mapping(
                    "profissional", row["id_profissional"], "profession", conn
                )
                if not profession_id:
                    logger.warning(
                        "Qualificação %s sem profession correspondente", row["id"]
                    )
                    continue

                registration_id = _uuid()
                issuance = row["data_emissao"]
                expiration = row["validade"]
                if pd.isna(expiration):
                    expiration = issuance + timedelta(days=3650)
                conn.execute(
                    text("""
                        INSERT INTO professional_registration (
                            id, fk_technician, fk_profession,
                            council, number, expiration_date
                        )
                        VALUES (
                            :id, :technician, :profession,
                            :council, :number, :expiration
                        )
                    """),
                    {
                        "id": registration_id,
                        "technician": technician_id,
                        "profession": profession_id,
                        "council": _txt(
                            row["orgao_expeditor"], 60, "Não informado"
                        ),
                        "number": _txt(row["numero_registro"], 30, "N/I"),
                        "expiration": expiration,
                    },
                )
                conn.execute(
                    text("""
                        UPDATE profession
                        SET requires_registration = true
                        WHERE id = :id
                    """),
                    {"id": profession_id},
                )
                _save_mapping(
                    conn,
                    "qualificacao",
                    row["id"],
                    "professional_registration",
                    registration_id,
                )
            else:
                certification_id = _uuid()
                conn.execute(
                    text("""
                        INSERT INTO certification (
                            id, fk_technician, type, information, image
                        )
                        VALUES (:id, :technician, :type, :information, :image)
                    """),
                    {
                        "id": certification_id,
                        "technician": technician_id,
                        "type": _txt(
                            row["tipo_credencial"], 255, "QUALIFICACAO"
                        ),
                        "information": _certification_information(row),
                        "image": _txt(row["documento"]),
                    },
                )
                _save_mapping(
                    conn,
                    "qualificacao",
                    row["id"],
                    "certification",
                    certification_id,
                )
            total += 1

    logger.info("Qualificações migradas: %s", total)


def executar_migracao_complementar():
    # A ordem faz parte da regra: entidades-pai devem existir antes das FKs.
    migrar_telefones()
    migrar_perfis()
    migrar_enderecos()
    migrar_fornecedores()
    migrar_demandantes()
    migrar_unidades_locais()
    migrar_projetos_tecnicos()
    migrar_profissionais()
    migrar_planos()
    migrar_assinaturas()
    migrar_produtos()
    migrar_qualificacoes()


TABELAS_SEM_EQUIVALENTE_DIRETO = {
    "contato": "não há agenda/relacionamento de contatos no destino",
    "avaliacao": "não há tabela de avaliações no destino",
    "postagem": "não há módulo social/postagens no destino",
    "chat": "não há chat no destino",
    "mensagem": "não há mensagens no destino",
    "usuario_chat": "não há participantes de chat no destino",
    "midia": "depende de postagem/mensagem, que não existem no destino",
    "servico": "serviço ofertado não equivale a technical_service executado",
    "certificacao": "certificação de fornecedor não equivale à de técnico",
    "equipamento_certificacao": "relação sem equivalente no destino",
    "compromisso": "não há entidade de compromisso/tarefa no destino",
    "documento_projeto": "não há tabela genérica de documentos de projeto",
    "loja_filial": "não há hierarquia matriz/filial no destino",
    "admin": "administrador da plataforma não possui equivalente no destino",
    "telefone_admin": "depende de admin, que não possui equivalente",
    "log_acesso_admin": "não há log de autenticação equivalente",
    "historico_alteracoes": "audit_log exige UUID e autoria não ambígua",
}


DADOS_SEM_DESTINO_CORRESPONDENTE = {
    "perfil.descricao",
    "projeto.nome",
    "projeto.descricao",
    "usuario_projeto participantes que não são donos",
}
