# database-rpa

ETL em Python que migrou usuários e dados de um banco legado ("banco simples", tabela `usuario`) para o `coredb` da Solaria. Lê a origem (`ORIGEM_DB_URL`, somente leitura), transforma e **grava direto no `coredb`** (`DESTINO_DB_URL`). A idempotência é controlada por um mapeamento de IDs em um arquivo SQLite local.

<p>

[![License](https://img.shields.io/github/license/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/commits)
[![GitHub Issues](https://img.shields.io/github/issues/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/pulls)

</p>

## Exceção documentada ao dono único

O `coredb` pertence ao `api-core`, mas este ETL continua escrevendo direto nele, como a única exceção formal a essa regra. Escrever pela API exigiria dezenas de endpoints de importação só para um job de migração pontual.

- **Ambiente:** somente QA. Nunca com a credencial administradora nem em produção.
- **Papel:** `rpa_writer`, com login próprio, definido no `database-console`. Precisa apenas de `SELECT`, `INSERT` e `UPDATE` nas tabelas abaixo, e nenhum `CREATE` (o ETL não cria mais tabela no `coredb`).
- **Tabelas:** `user_account`, `contact`, `person`, `address`, `business_contact`, `company`, `job_position`, `company_position`, `user_company`, `supplier`, `requester`, `local_unit`, `technical_project`, `technician`, `profession`, `technician_affiliation`, `company_plan`, `subscription`, `brand`, `model`, `inventory`, `offer`, `professional_registration`, `certification`, `user_photo`, `company_photo`, `model_photo`. `UPDATE` só é usado em `contact`, `user_account` e `profession`.
- **Origem:** o banco legado dos serviços Elos, fora do escopo da Solaria, é só leitura.
- **Mapeamento de IDs:** o de-para legado para novo fica no SQLite local (`RPA_MAPPING_DB`, padrão `rpa_id_mapping.sqlite`, ignorado pelo Git), não mais no `coredb`. As gravações no mapeamento só são confirmadas depois do commit no destino. Se o QA for recriado, apague o arquivo para o ETL reprocessar tudo.

## Status: nomes finais do `coredb`

O SQL usa os nomes do baseline novo (`rename-map.csv` em `arquitetura-de-dados`): `user_account`, `job_position`, `company_position`, `company_plan`, FKs `<tabela>_id`, `is_registration_required`, `is_legacy`, `starts_at`, `ends_at`, `expires_at`, `model_name`, `price`, entre outros.

- **O que o legado não traz** é preenchido com dados fictícios determinísticos (Faker, em `mock_data.py`).
- **Regras do schema** (em `schema_v29.py`): `user_account.auth_id` e `user_account.username` (`^[a-z0-9_]{3,30}$`, único, derivado do e-mail), `company.type` (`SUPPLIER` ou `REQUESTER`) e `slug` único, `technician.slug` e `offer.slug` únicos, marca do modelo em `brand` (`is_legacy = true`), largura e comprimento do modelo em metros, tipo `MONOCRYSTALLINE`, preço da oferta maior que zero, vínculo do dono da empresa com o cargo `ADMIN`.
- **Imagens:** com `CLOUDINARY_CLOUD_NAME` definido, usuários, empresas e modelos migrados recebem fotos do `mocks-warehouse` (`user_photo`, `company_photo` e `model_photo`); `MOCKS_MANIFEST` aponta o `manifest.json` e `MOCKS_PUBLIC_PREFIX` o prefixo. Sem a cloud ou o manifest, o passo é pulado com um aviso. Só entram registros que ainda não têm foto.
- **Limites conhecidos:** `user_account.auth_id` é um id sem conta no authdb, porque o ETL não escreve no authdb; os usuários migrados só entram depois que uma conta com esse id for criada (a senha do legado não é reaproveitada). Os projetos técnicos só migram se o legado tiver `projeto` e `usuario_projeto`.
- Não há implantação conhecida; o fluxo completo contra o QA recriado é verificação manual. Configure as variáveis a partir do `.env.example`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `main.py` | Orquestra a execução e registra em `rpa_etl.log` |
| `extract.py`, `transform.py`, `load.py` | Extrai os usuários novos da origem, transforma e grava `user_account`, `contact` e `person` no destino |
| `extended_migration.py` | Migração complementar (empresas, endereços, ofertas, estoque e outras tabelas) |
| `id_mapping.py` | Mapeamento de IDs legado para novo em SQLite local |
| `mock_data.py`, `inspecionar.py` | Dados fictícios com Faker e inspeção do banco |

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta do projeto.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), como reportar vulnerabilidades de segurança.
