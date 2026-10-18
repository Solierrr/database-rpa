# database-rpa

ETL em Python que migrou usuários e dados de um banco legado ("banco simples", tabela `usuario`) para o `coredb` da Solaria. Lê a origem (`ORIGEM_DB_URL`, somente leitura), transforma e **grava direto no `coredb`** (`DESTINO_DB_URL`), controlando a idempotência na tabela `rpa_id_mapping` do destino.

<p>

[![License](https://img.shields.io/github/license/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/pulls)

</p>

## Status: adaptado ao schema V29 do `coredb`

- **Origem:** o banco legado dos serviços Elos, que não faz parte do escopo da Solaria e **não deve ser alterado** (a conexão é somente leitura).
- **Destino:** o `coredb`. O que o legado não traz é preenchido com dados fictícios determinísticos (Faker, em `mock_data.py`).
- **O que o ETL respeita no V29** (regras em `schema_v29.py`): `users.auth_id` e `users.username` (`^[a-z0-9_]{3,30}$`, único, derivado do e-mail), `company.type` (`SUPPLIER` ou `DEMANDANT`) e `slug` único, `technician.slug` e `offer.slug` únicos, marca do modelo em `brand` (`legacy = true`), largura e comprimento do modelo em metros, tipo `MONOCRYSTALLINE`, preço da oferta maior que zero, vínculo do dono da empresa com o cargo `ADMIN` e um único vínculo por usuário.
- **Limites conhecidos:** `users.auth_id` é um id sem conta no authdb, porque o ETL não escreve no authdb; os usuários migrados só entram depois que uma conta com esse id for criada (a senha do legado não é reaproveitada). As imagens do Cloudinary ainda não são ligadas aos registros migrados. Os projetos técnicos só migram se o legado tiver `projeto` e `usuario_projeto`.
- Foi verificado contra um `coredb` novo (migrações V1 a V29) e um legado de teste, incluindo uma segunda execução sem duplicar nada. Não há implantação conhecida (não está no Render nem no `infra-gitops`); não execute contra um banco real sem antes revisar os dados.

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
