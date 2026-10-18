# database-rpa

ETL em Python que migrou usuários e dados de um banco legado ("banco simples", tabela `usuario`) para o `coredb` da Solaria. Lê a origem (`ORIGEM_DB_URL`, somente leitura), transforma e **grava direto no `coredb`** (`DESTINO_DB_URL`), controlando a idempotência na tabela `rpa_id_mapping` do destino.

<p>

[![License](https://img.shields.io/github/license/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/pulls)

</p>

## Status: descontinuado (decisão de 2026-10-18, aguardando confirmação do dono para arquivar)

- **Não roda contra o schema atual do `coredb`.** Ele insere em `users` só `id` e `avatar`, mas `users.auth_id` e `users.username` são `NOT NULL` no schema atual do `database-console`; além disso grava em 23 tabelas (`users`, `person`, `contact`, `company`, `supplier`, `offer`, `inventory` e outras) sem passar pelo `api-core`, o que pula as regras dele (cargo ADMIN, vínculo único usuário-empresa, status de empresa, `auth_user`).
- **A carga de dados tem outros caminhos:** o `seed` do `database-console` (desenvolvimento e QA) e `anexos/carga-dados-prod-v29.py` do VersioSpec (produção).
- Não há implantação conhecida (não está no Render nem no `infra-gitops`). A decisão e o motivo estão na spec `dados/acesso-ao-coredb` do VersioSpec.
- O código fica aqui para consulta enquanto o repositório não é arquivado. **Não execute contra um banco real.**

## Arquivos

| Arquivo | Papel |
|---|---|
| `main.py` | Orquestra a execução e registra em `rpa_etl.log` |
| `extract.py`, `transform.py`, `load.py` | Extrai os usuários novos da origem, transforma e grava `users`, `contact` e `person` no destino |
| `extended_migration.py` | Migração complementar (empresas, endereços, ofertas, estoque e outras tabelas) |
| `mock_data.py`, `inspecionar.py` | Dados fictícios com Faker e inspeção do banco |

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), como reportar vulnerabilidades de segurança.
