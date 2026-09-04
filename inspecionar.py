"""
Utilitário: lista todas as tabelas e colunas dos dois bancos, pra você
confirmar os nomes reais e ajustar MAPA_COLUNAS em transform.py.

Uso:
    python inspecionar.py
"""
from sqlalchemy import inspect
from db import engine_origem, engine_destino

for nome, engine in [("ORIGEM (banco simples)", engine_origem), ("DESTINO (Solaria)", engine_destino)]:
    insp = inspect(engine)
    print(f"\n{'='*60}\n{nome}\n{'='*60}")
    for tabela in insp.get_table_names():
        print(f"\nTabela: {tabela}")
        for col in insp.get_columns(tabela):
            nulo = "" if col["nullable"] else " NOT NULL"
            print(f"  - {col['name']}: {col['type']}{nulo}")