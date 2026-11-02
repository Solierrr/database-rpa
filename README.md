<p align="center">
  <img src="./assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

<p align="center">
  <img src="./assets/readme/stacks/python.png" width="100" hspace="8" alt="Python" title="Python">
</p>

# Migração de dados legados

[![License](https://img.shields.io/github/license/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/commits)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/database-rpa)](https://github.com/Solierrr/database-rpa/releases)

Esta rotina atende a equipe responsável por trazer os cadastros de uma base antiga para a plataforma. Ela importa pessoas, empresas, profissionais, planos, assinaturas e produtos, preservando relações entre os registros que têm correspondência. Campos obrigatórios ausentes recebem dados sintéticos ou padrões definidos no código. Essa escolha precisa ser revista antes de usar os cadastros importados em operação. <!-- PENDENTE: 2 -->

A execução usa Python para ler PostgreSQL e gravar diretamente no banco de negócio. O controle de correspondências permite retomar etapas já concluídas sem recriar os registros mapeados em uma execução sequencial. Um workflow do GitHub Actions permite iniciar a rotina manualmente ou habilitar sua execução diária. As imagens opcionais são associadas a partir de um catálogo existente no Cloudinary. O cadastro de contas de acesso continua separado da importação.

## Aprofunde-se no Projeto!

- [OVERVIEW.md](./docs/OVERVIEW.md), capacidades, regras e efeitos da migração.
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), etapas, mapeamento, integrações e transações.
- [RUNNING.md](./docs/RUNNING.md), configuração, execução local e verificações.
- [DEPLOY.md](./docs/DEPLOY.md), execução no GitHub Actions e configuração do agendamento.
- [STATUS.md](./docs/STATUS.md), cobertura e limitações atuais.
- [Fluxos](./flows/), importação, associação de imagens e execução agendada.
- [Banco de dados](./database/), tabela de correspondência mantida pela rotina.
- [PENDENCIAS.md](./PENDENCIAS.md), decisões que dependem do responsável.

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de commit, branch e Pull Request.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), como reportar uma vulnerabilidade.
