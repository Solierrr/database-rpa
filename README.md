# database-rpa

ETL em Python que migrou usuários e dados de um banco legado ("banco simples", tabela `usuario`) para o `coredb` da Solaria. Lê a origem (`ORIGEM_DB_URL`, somente leitura), transforma e **grava direto no `coredb`** (`DESTINO_DB_URL`), controlando a idempotência na tabela `rpa_id_mapping` do destino.

<p>

[![License](https://img.shields.io/github/license/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/pulls)

</p>

## Status: em escopo, precisa ser adaptado ao schema atual

- **Origem:** o banco legado dos serviços Elos, que não faz parte do escopo da Solaria e **não deve ser alterado** (a conexão é somente leitura).
- **Destino:** o `coredb`. O que o legado não traz é preenchido com dados fictícios determinísticos (Faker, em `mock_data.py`), e as imagens podem vir do Cloudinary.
- **Pendente:** ele foi escrito para um schema antigo e **não roda contra o schema atual** (V29 do `database-console`): insere em `users` só `id` e `avatar`, mas `users.auth_id` e `users.username` são `NOT NULL`, e grava em 23 tabelas (`users`, `person`, `contact`, `company`, `supplier`, `offer`, `inventory` e outras) sem passar pelo `api-core`, o que pula as regras dele (cargo ADMIN, vínculo único usuário-empresa, status de empresa, `auth_user`).
- Não há implantação conhecida (não está no Render nem no `infra-gitops`). Não execute contra um banco real antes de adaptá-lo. O contexto está na spec `dados/acesso-ao-coredb` do VersioSpec.

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
