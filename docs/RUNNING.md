<p align="center">
  <img src="../assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

# Execução local

O preparo do ambiente virtual segue o [PYTHON.md](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md), mas neste repositório o `make dev` executa uma migração e encerra, sem iniciar um servidor de desenvolvimento.

## Pré-requisitos

O CI e a rotina agendada usam Python 3.14. As dependências de execução têm versões fixadas em [`requirements.txt`](https://github.com/Solierrr/database-rpa/blob/main/requirements.txt).

- Python 3.14, Git, `make` e shell compatível com `sh`.
- Acesso PostgreSQL de leitura à origem e de escrita ao destino.
- Schema legado com as tabelas consultadas e destino compatível com as regras V29.
- Manifesto de imagens disponível localmente, caso a associação de fotos seja necessária.

Use bases isoladas para conferir a transformação e os relacionamentos antes da execução no destino autorizado. O código não oferece dry run e confirma transações durante a migração.

## Variáveis

`config.py` carrega `.env` e interrompe a importação se faltam as duas conexões obrigatórias. Obtenha os valores pelo canal de segredos autorizado, sem copiá-los para documentos ou commits.

| Nome | Uso |
|---|---|
| `ORIGEM_DB_URL` | conexão SQLAlchemy PostgreSQL para a base legada |
| `DESTINO_DB_URL` | conexão SQLAlchemy PostgreSQL para o banco de negócio |
| `CLOUDINARY_CLOUD_NAME` | habilita a montagem das referências de imagens |
| `MOCKS_MANIFEST` | caminho do manifesto JSON |
| `MOCKS_PUBLIC_PREFIX` | prefixo dos identificadores públicos de imagens |

O alvo `make vault` existe, mas `VAULT_FOLDERS` está vazio, e sem as pastas autorizadas o comando falha sem gerar o `.env`, por isso o local correto dos segredos ainda precisa ser confirmado. <!-- PENDENTE: 1 --> O procedimento compartilhado está no [guia de segredos](https://github.com/Solierrr/docs-warehouse/blob/main/readme/infisical/README.md).

## Comandos

Execute na raiz do checkout destinado ao desenvolvimento.

```bash
make doctor
make install
make test
make lint
make build
```

O Makefile usa o ambiente virtual em Windows e Unix.

| Comando | Resultado |
|---|---|
| `make install` | cria `.venv` e instala dependências e Ruff |
| `make test` | executa unittest em `tests/` |
| `make lint` | Ruff com regras de erros e imports definidas no Makefile |
| `make build` | byte compilation dos fontes |
| `make ci` | lint, testes e build |
| `make dev` | executa `main.py` e grava no destino configurado |
| `make format` | informa que não há comando configurado |

Não há alvo `make openapi`, pois a rotina não expõe API. Com o ambiente virtual ativo, `python inspecionar.py` lista tabelas e colunas dos bancos, sem executar a migração.

Depois de revisar as conexões e os dados, `make dev` inicia a carga. A base de destino deve aceitar criação de `rpa_id_mapping`, leitura de cadastros e as escritas das etapas. O repositório não instala as migrations do `coredb`.

## Como conferir o resultado

Os testes unitários cobrem helpers de username, slug e catálogo de imagens. Não validam o ETL contra um banco nem comprovam compatibilidade com uma versão posterior à V29.

Em bases isoladas, compare as contagens e as relações com a origem, confira os avisos de registros ignorados e repita a execução preservando o mapeamento. Verifique se os registros já importados foram reaproveitados. A reexecução não é uma atualização geral dos dados, e o telefone é atualizado novamente em sua etapa.

O retorno zero informa término sem exceção, mas pode incluir registros ignorados e imagens não associadas. Os detalhes estão em `rpa_etl.log` e em [STATUS.md](./STATUS.md).

## Problemas conhecidos

Sem conexão obrigatória, o processo falha durante a importação da configuração. Tabela ou coluna incompatível provoca erro SQL. As tabelas `projeto` e `usuario_projeto` são consultadas sem teste de existência, portanto sua ausência interrompe a execução.

Sem cloud ou manifesto, a etapa de imagens registra um aviso e é pulada. Manifesto inválido pode produzir exceção. Registros sem relações exigidas podem ser ignorados. Se uma etapa falha, as anteriores já confirmadas continuam no destino e a retomada depende do mapeamento preservado.
