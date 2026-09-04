"""Migração complementar do banco legado para o schema Solaria.

Este módulo cobre tabelas com correspondência semanticamente segura no schema novo:
- telefone -> contact.phone
- perfil.foto_perfil -> users.avatar
- endereco -> address
- fornecedor -> business_contact + company + supplier
- empresa_demandante -> business_contact + company + requester
- profissional -> person.cpf + technician + profession + technician_affiliation
- plano -> company_plans
- assinatura -> subscription (quando o usuário é fornecedor)
- produto/equipamento_eletrico -> model + inventory + offer

As tabelas sem equivalente claro no schema destino ficam explicitamente fora da carga.
O rpa_id_mapping torna a execução idempotente e preserva as relações BIGINT -> UUID.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from faker import Faker
from sqlalchemy import text

from config import FAKER_LOCALE
from db import engine_origem, engine_destino

logger = logging.getLogger(__name__)
fake = Faker(FAKER_LOCALE)


def _uuid() -> str:
    return str(uuid.uuid4())


def _digits(value, max_len=None):
    if value is None or pd.isna(value):
        return None
    s = ''.join(ch for ch in str(value) if ch.isdigit())
    return s[:max_len] if max_len else s


def _txt(value, max_len=None, fallback=None):
    if value is None or pd.isna(value) or str(value).strip() == '':
        value = fallback
    if value is None:
        return None
    s = str(value).strip()
    return s[:max_len] if max_len else s


def _mapping(origem_tabela: str, origem_id, destino_tabela: str):
    with engine_destino.connect() as conn:
        return conn.execute(text("""
            SELECT destino_id
            FROM rpa_id_mapping
            WHERE origem_tabela=:ot AND origem_id=:oid AND destino_tabela=:dt
        """), {'ot': origem_tabela, 'oid': int(origem_id), 'dt': destino_tabela}).scalar()


def _save_mapping(conn, origem_tabela, origem_id, destino_tabela, destino_id):
    conn.execute(text("""
        INSERT INTO rpa_id_mapping(origem_tabela, origem_id, destino_tabela, destino_id)
        VALUES (:ot,:oid,:dt,:did)
        ON CONFLICT (origem_tabela, origem_id, destino_tabela) DO NOTHING
    """), {'ot': origem_tabela, 'oid': int(origem_id), 'dt': destino_tabela, 'did': destino_id})


def _person_ids(usuario_id):
    person_id = _mapping('usuario', usuario_id, 'person')
    if not person_id:
        return None, None, None
    with engine_destino.connect() as conn:
        row = conn.execute(text("SELECT id, fk_users, fk_contact FROM person WHERE id=:id"), {'id': person_id}).mappings().first()
    return (row['id'], row['fk_users'], row['fk_contact']) if row else (None, None, None)


def migrar_telefones():
    df = pd.read_sql("""
        SELECT id, id_usuario, telefone, principal
        FROM telefone
        ORDER BY principal DESC, id
    """, engine_origem)
    atualizados = 0
    vistos = set()
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            uid = int(r['id_usuario'])
            if uid in vistos:
                continue
            person_id = _mapping('usuario', uid, 'person')
            if not person_id:
                continue
            contact_id = conn.execute(text("SELECT fk_contact FROM person WHERE id=:id"), {'id': person_id}).scalar()
            phone = _digits(r['telefone'], 12)
            if contact_id and phone:
                conn.execute(text("UPDATE contact SET phone=:phone WHERE id=:id"), {'phone': phone, 'id': contact_id})
                _save_mapping(conn, 'telefone', r['id'], 'contact', contact_id)
                vistos.add(uid)
                atualizados += 1
    logger.info("Telefones migrados: %s", atualizados)


def migrar_perfis():
    df = pd.read_sql("SELECT id, id_usuario, foto_perfil FROM perfil ORDER BY id", engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('perfil', r['id'], 'users'):
                continue
            _, users_id, _ = _person_ids(r['id_usuario'])
            if not users_id:
                continue
            avatar = _txt(r['foto_perfil'])
            if avatar:
                conn.execute(text("UPDATE users SET avatar=:a WHERE id=:id"), {'a': avatar, 'id': users_id})
            _save_mapping(conn, 'perfil', r['id'], 'users', users_id)
            total += 1
    logger.info("Perfis migrados: %s", total)


def migrar_enderecos():
    df = pd.read_sql("""
        SELECT id, id_usuario, estado, cidade, bairro, cep, logradouro, numero, complemento
        FROM endereco ORDER BY id
    """, engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('endereco', r['id'], 'address'):
                continue
            aid = _uuid()
            conn.execute(text("""
                INSERT INTO address(id,state,city,neighborhood,zip_code,street,number)
                VALUES (:id,:state,:city,:neighborhood,:zip,:street,:number)
            """), {
                'id': aid,
                'state': _txt(r['estado'], 2, 'SP').upper(),
                'city': _txt(r['cidade'], fallback='São Paulo'),
                'neighborhood': _txt(r['bairro']),
                'zip': (_digits(r['cep'], 8) or fake.postcode().replace('-', '')[:8]).ljust(8, '0')[:8],
                'street': _txt(r['logradouro'], fallback='Endereço não informado'),
                'number': _txt(r['numero'], 10, 'S/N'),
            })
            _save_mapping(conn, 'endereco', r['id'], 'address', aid)
            total += 1
    logger.info("Endereços migrados: %s", total)


def _address_for_user(usuario_id):
    df = pd.read_sql(text("SELECT id FROM endereco WHERE id_usuario=:u ORDER BY id LIMIT 1"), engine_origem, params={'u': int(usuario_id)})
    if not df.empty:
        aid = _mapping('endereco', int(df.iloc[0]['id']), 'address')
        if aid:
            return aid
    # endereço obrigatório no destino: cria fallback apenas se realmente não existir origem
    aid = _uuid()
    with engine_destino.begin() as conn:
        conn.execute(text("""
            INSERT INTO address(id,state,city,neighborhood,zip_code,street,number)
            VALUES (:id,'SP','São Paulo',NULL,'00000000','Endereço não informado','S/N')
        """), {'id': aid})
    return aid


def _create_company_for_legacy(conn, origem_tabela, origem_id, usuario_id, cnpj, razao_social):
    existing = _mapping(origem_tabela, origem_id, 'company')
    if existing:
        return existing
    _, _, contact_id = _person_ids(usuario_id)
    email = None
    phone = None
    if contact_id:
        cr = conn.execute(text("SELECT email, phone FROM contact WHERE id=:id"), {'id': contact_id}).mappings().first()
        if cr:
            email, phone = cr['email'], cr['phone']
    bcid, cid = _uuid(), _uuid()
    company_email = _txt(email, 100, f'empresa{origem_id}@migracao.local')
    conn.execute(text("""
        INSERT INTO business_contact(id,company_email,phone,website)
        VALUES (:id,:email,:phone,NULL)
    """), {'id': bcid, 'email': company_email, 'phone': _txt(phone, 12)})
    aid = _address_for_user(usuario_id)
    corporate = _txt(razao_social, 120, f'Empresa migrada {origem_id}')
    conn.execute(text("""
        INSERT INTO company(id,fk_address,fk_business_contact,cnpj,trade_name,corporate_name)
        VALUES (:id,:addr,:bc,:cnpj,:trade,:corp)
    """), {
        'id': cid, 'addr': aid, 'bc': bcid,
        'cnpj': (_digits(cnpj, 14) or str(fake.random_number(digits=14, fix_len=True))).zfill(14)[:14],
        'trade': corporate, 'corp': corporate,
    })
    _save_mapping(conn, origem_tabela, origem_id, 'business_contact', bcid)
    _save_mapping(conn, origem_tabela, origem_id, 'company', cid)
    return cid


def migrar_fornecedores():
    df = pd.read_sql("SELECT id,id_usuario,tipo_fornecedor,cnpj,razao_social FROM fornecedor ORDER BY id", engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('fornecedor', r['id'], 'supplier'):
                continue
            cid = _create_company_for_legacy(conn, 'fornecedor', r['id'], r['id_usuario'], r['cnpj'], r['razao_social'])
            sid = _uuid()
            conn.execute(text("INSERT INTO supplier(id,fk_company,status,business_type) VALUES (:id,:c,'ACTIVE',:bt)"),
                         {'id': sid, 'c': cid, 'bt': _txt(r['tipo_fornecedor'], 40)})
            _save_mapping(conn, 'fornecedor', r['id'], 'supplier', sid)
            total += 1
    logger.info("Fornecedores migrados: %s", total)


def migrar_demandantes():
    df = pd.read_sql("SELECT id,id_usuario,cnpj,razao_social FROM empresa_demandante ORDER BY id", engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('empresa_demandante', r['id'], 'requester'):
                continue
            cid = _create_company_for_legacy(conn, 'empresa_demandante', r['id'], r['id_usuario'], r['cnpj'], r['razao_social'])
            rid = _uuid()
            conn.execute(text("INSERT INTO requester(id,fk_company,business_type) VALUES (:id,:c,:bt)"),
                         {'id': rid, 'c': cid, 'bt': 'REQUESTER'})
            _save_mapping(conn, 'empresa_demandante', r['id'], 'requester', rid)
            total += 1
    logger.info("Demandantes migrados: %s", total)


def migrar_profissionais():
    df = pd.read_sql("SELECT id,id_usuario,profissao,cpf,id_fornecedor FROM profissional ORDER BY id", engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('profissional', r['id'], 'technician'):
                continue
            person_id, _, _ = _person_ids(r['id_usuario'])
            if not person_id:
                continue
            cpf = _digits(r['cpf'], 11)
            if cpf and len(cpf) == 11:
                # usa o CPF real do legado no lugar do Faker criado na primeira etapa
                conflict = conn.execute(text("SELECT id FROM person WHERE cpf=:cpf AND id<>:id"), {'cpf': cpf, 'id': person_id}).scalar()
                if not conflict:
                    conn.execute(text("UPDATE person SET cpf=:cpf WHERE id=:id"), {'cpf': cpf, 'id': person_id})
            tid = _uuid()
            conn.execute(text("INSERT INTO technician(id,fk_person) VALUES (:id,:p)"), {'id': tid, 'p': person_id})
            _save_mapping(conn, 'profissional', r['id'], 'technician', tid)

            pname = _txt(r['profissao'], 100, 'Profissional')
            pid = conn.execute(text("SELECT id FROM profession WHERE name=:n"), {'n': pname}).scalar()
            if not pid:
                pid = _uuid()
                conn.execute(text("INSERT INTO profession(id,name,requires_registration) VALUES (:id,:n,false)"), {'id': pid, 'n': pname})
            _save_mapping(conn, 'profissional', r['id'], 'profession', pid)

            if r.get('id_fornecedor') is not None and not pd.isna(r.get('id_fornecedor')):
                company_id = _mapping('fornecedor', int(r['id_fornecedor']), 'company')
                if company_id:
                    taid = _uuid()
                    conn.execute(text("""
                        INSERT INTO technician_affiliation(id,fk_company,fk_technician,affiliation_type)
                        VALUES (:id,:c,:t,'AFFILIATED')
                        ON CONFLICT (fk_company,fk_technician) DO NOTHING
                    """), {'id': taid, 'c': company_id, 't': tid})
                    _save_mapping(conn, 'profissional', r['id'], 'technician_affiliation', taid)
            total += 1
    logger.info("Profissionais migrados: %s", total)


def _cycle(v):
    s = str(v or '').upper()
    if 'SEM' in s or 'WEEK' in s:
        return 'WEEKLY'
    if 'ANO' in s or 'ANU' in s or 'YEAR' in s:
        return 'YEARLY'
    return 'MONTHLY'


def migrar_planos():
    df = pd.read_sql("SELECT id,nome,valor,tipo_mensalidade FROM plano ORDER BY id", engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('plano', r['id'], 'company_plans'):
                continue
            pid = _uuid()
            conn.execute(text("INSERT INTO company_plans(id,name,value,cycle) VALUES (:id,:n,:v,:c)"), {
                'id': pid, 'n': _txt(r['nome'], fallback=f'Plano {r["id"]}'),
                'v': Decimal('0') if pd.isna(r['valor']) else Decimal(str(r['valor'])), 'c': _cycle(r['tipo_mensalidade'])
            })
            _save_mapping(conn, 'plano', r['id'], 'company_plans', pid)
            total += 1
    logger.info("Planos migrados: %s", total)


def _supplier_by_user(usuario_id):
    df = pd.read_sql(text("SELECT id FROM fornecedor WHERE id_usuario=:u LIMIT 1"), engine_origem, params={'u': int(usuario_id)})
    if df.empty:
        return None
    return _mapping('fornecedor', int(df.iloc[0]['id']), 'supplier')


def migrar_assinaturas():
    df = pd.read_sql("SELECT id,id_usuario,id_plano,status_assinatura,renovacao_automatica,data_inicio,validade FROM assinatura ORDER BY id", engine_origem)
    total = 0
    status_map = {'ATIVA':'PAID','PAGA':'PAID','INADIMPLENTE':'IN_DEBT','SUSPENSA':'SUSPENDED'}
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('assinatura', r['id'], 'subscription'):
                continue
            sid = _supplier_by_user(r['id_usuario'])
            plan_id = _mapping('plano', r['id_plano'], 'company_plans')
            if not sid or not plan_id:
                logger.warning("Assinatura %s ignorada: destino exige supplier e plano", r['id'])
                continue
            subid = _uuid()
            st = status_map.get(str(r['status_assinatura']).upper(), 'PAID')
            start = r['data_inicio'] if not pd.isna(r['data_inicio']) else pd.Timestamp.now()
            end = None if pd.isna(r['validade']) else r['validade']
            conn.execute(text("""
                INSERT INTO subscription(id,fk_supplier,fk_plan,status,auto_renewal,start_date,end_date)
                VALUES (:id,:s,:p,:st,:ar,:ini,:fim)
            """), {'id': subid, 's': sid, 'p': plan_id, 'st': st,
                   'ar': True if pd.isna(r['renovacao_automatica']) else bool(r['renovacao_automatica']), 'ini': start, 'fim': end})
            _save_mapping(conn, 'assinatura', r['id'], 'subscription', subid)
            total += 1
    logger.info("Assinaturas migradas: %s", total)


def migrar_produtos():
    df = pd.read_sql("""
        SELECT p.id,p.id_fornecedor,p.nome,p.quantidade_em_estoque,p.fabricante,p.descricao,p.categoria,p.sku,p.preco,
               e.altura_mm,e.largura_mm,e.comprimento_mm,e.potencia_w,e.peso_kg,e.eficiencia
        FROM produto p
        LEFT JOIN equipamento_eletrico e ON e.id_produto=p.id
        ORDER BY p.id
    """, engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('produto', r['id'], 'model'):
                continue
            supplier_id = _mapping('fornecedor', r['id_fornecedor'], 'supplier')
            if not supplier_id:
                continue
            mid = _uuid()
            h = float(r['altura_mm']) if not pd.isna(r['altura_mm']) else 1.0
            w = float(r['largura_mm']) if not pd.isna(r['largura_mm']) else 1.0
            l = float(r['comprimento_mm']) if not pd.isna(r['comprimento_mm']) else 1.0
            dimension = max((h*w*l)/1_000_000_000, 0.001)
            power = float(r['potencia_w']) if not pd.isna(r['potencia_w']) else 0.01
            weight = float(r['peso_kg']) if not pd.isna(r['peso_kg']) else 0.01
            eff = float(r['eficiencia']) if not pd.isna(r['eficiencia']) else 1.0
            eff = min(max(eff, 0), 100)
            conn.execute(text("""
                INSERT INTO model(id,brand,model,power_wp,efficiency,dimension,weight,status)
                VALUES (:id,:brand,:model,:power,:eff,:dim,:weight,'UNDER_ANALYSIS')
            """), {'id': mid, 'brand': _txt(r['fabricante'], fallback='Não informado'),
                   'model': _txt(r['nome'], fallback=f'Produto {r["id"]}'), 'power': power,
                   'eff': eff, 'dim': dimension, 'weight': weight})
            qty = 0 if pd.isna(r['quantidade_em_estoque']) else max(int(r['quantidade_em_estoque']), 0)
            iid, oid = _uuid(), _uuid()
            conn.execute(text("INSERT INTO inventory(id,fk_supplier,fk_model,quantity) VALUES (:id,:s,:m,:q)"),
                         {'id': iid, 's': supplier_id, 'm': mid, 'q': qty})
            price = Decimal('0') if pd.isna(r['preco']) else max(Decimal(str(r['preco'])), Decimal('0'))
            conn.execute(text("INSERT INTO offer(id,fk_supplier,fk_model,unit_price,availability) VALUES (:id,:s,:m,:p,:q)"),
                         {'id': oid, 's': supplier_id, 'm': mid, 'p': price, 'q': qty})
            _save_mapping(conn, 'produto', r['id'], 'model', mid)
            _save_mapping(conn, 'produto', r['id'], 'inventory', iid)
            _save_mapping(conn, 'produto', r['id'], 'offer', oid)
            total += 1
    logger.info("Produtos migrados: %s", total)


def migrar_qualificacoes():
    df = pd.read_sql("""
        SELECT id,id_profissional,orgao_expeditor,nome,tipo_credencial,validade,numero_registro,documento
        FROM qualificacao ORDER BY id
    """, engine_origem)
    total = 0
    with engine_destino.begin() as conn:
        for r in df.to_dict('records'):
            if _mapping('qualificacao', r['id'], 'certification') or _mapping('qualificacao', r['id'], 'professional_registration'):
                continue
            tid = _mapping('profissional', r['id_profissional'], 'technician')
            if not tid:
                continue
            number = _txt(r['numero_registro'], 30)
            if number:
                prof_id = _mapping('profissional', r['id_profissional'], 'profession')
                prid = _uuid()
                exp = r['validade'] if not pd.isna(r['validade']) else date.today() + timedelta(days=365)
                conn.execute(text("""
                    INSERT INTO professional_registration(id,fk_technician,fk_profession,council,number,expiration_date)
                    VALUES (:id,:t,:p,:c,:n,:e)
                """), {'id': prid, 't': tid, 'p': prof_id,
                       'c': _txt(r['orgao_expeditor'], 60, 'Não informado'), 'n': number, 'e': exp})
                _save_mapping(conn, 'qualificacao', r['id'], 'professional_registration', prid)
            else:
                cid = _uuid()
                conn.execute(text("""
                    INSERT INTO certification(id,fk_technician,type,information,image)
                    VALUES (:id,:t,:ty,:info,:img)
                """), {'id': cid, 't': tid, 'ty': _txt(r['tipo_credencial'], 255, 'QUALIFICACAO'),
                       'info': _txt(r['nome'], fallback='Qualificação migrada'), 'img': _txt(r['documento'])})
                _save_mapping(conn, 'qualificacao', r['id'], 'certification', cid)
            total += 1
    logger.info("Qualificações migradas: %s", total)


def executar_migracao_complementar():
    # A ordem é parte da regra de negócio: pais antes dos filhos/FKs.
    migrar_telefones()
    migrar_perfis()
    migrar_enderecos()
    migrar_fornecedores()
    migrar_demandantes()
    migrar_profissionais()
    migrar_planos()
    migrar_assinaturas()
    migrar_produtos()
    migrar_qualificacoes()


TABELAS_SEM_EQUIVALENTE_DIRETO = {
    'contato': 'não há agenda/relacionamento de contatos no destino',
    'avaliacao': 'não há tabela de avaliações no destino',
    'postagem': 'não há módulo social/postagens no destino',
    'chat': 'não há chat no destino',
    'mensagem': 'não há mensagens no destino',
    'usuario_chat': 'não há participantes de chat no destino',
    'midia': 'depende de postagem/mensagem, que não existem no destino',
    'servico': 'serviço legado do fornecedor não equivale a technical_service, que exige technical_project',
    'certificacao': 'certificação do fornecedor não equivale à certification de técnico',
    'equipamento_certificacao': 'a relação de certificação de equipamento não existe no destino',
    'projeto': 'o destino exige requester + local_unit e o legado não tem equivalência 1:1',
    'usuario_projeto': 'participação genérica não tem equivalente direto no destino',
    'compromisso': 'não há entidade de compromisso/tarefa no destino',
    'documento_projeto': 'não há tabela genérica de documentos de projeto',
    'loja_filial': 'não há hierarquia matriz/filial no destino',
}
