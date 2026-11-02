<p align="center">
  <img src="../assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

# Execução no GitHub Actions

A rotina é distribuída como código Python e executada em lote. O caminho publicado no repositório é o workflow [`scheduled-migration.yml`](https://github.com/Solierrr/database-rpa/blob/main/.github/workflows/scheduled-migration.yml). Não há Dockerfile, serviço HTTP ou configuração de deploy no Render neste repositório.

Os processos compartilhados de publicação ficam no [catálogo de deploy](https://github.com/Solierrr/docs-warehouse/tree/main/readme/deploy/). Para esta rotina, a configuração específica é a execução do workflow, sem a pipeline de imagem e servidor descrita nos guias de QA e produção.

## Ambientes e acesso

O destino da carga é determinado pelas conexões, não pelo nome do job.

| Execução | Onde | Endereço ou entrada |
|---|---|---|
| Local | processo Python na máquina do operador | `make dev`, sem endereço HTTP |
| Manual no Actions | runner Ubuntu | [Scheduled migration](https://github.com/Solierrr/database-rpa/actions/workflows/scheduled-migration.yml) |
| Agendada no Actions | mesmo workflow | cron diário às 06:00 UTC |

O código não identifica quais instâncias de origem e destino estão autorizadas, nem comprova que o agendamento está habilitado no repositório. A hipótese usada é de execução controlada pelo responsável, com secrets e autorização de ambiente definidos fora do código. <!-- PENDENTE: 1 -->

## Configuração do workflow

O workflow recebe as conexões por GitHub secrets e o agendamento por variável de repositório.

| Nome | Local | Papel |
|---|---|---|
| `ORIGEM_DB_URL`, `DESTINO_DB_URL` | secrets | conexões obrigatórias |
| `CLOUDINARY_CLOUD_NAME` | secret | habilitação opcional das imagens |
| `RPA_SCHEDULE_ENABLED` | variável do repositório | habilita o evento agendado quando o conteúdo é `true` |
| `MOCKS_MANIFEST` | ambiente definido pelo workflow | caminho do manifesto no checkout do runner |

O disparo manual por `workflow_dispatch` não depende de `RPA_SCHEDULE_ENABLED`. Sem uma das conexões, a verificação inicial registra aviso e pula checkout, instalação e migração. O workflow pode terminar sem erro mesmo sem importar dados.

Com as conexões presentes, o runner faz checkout do código e somente do manifesto do `mocks-warehouse`, instala Python 3.14 e as dependências, e executa `python main.py`. A permissão declarada é `contents: read`. O acesso ao outro repositório depende das permissões disponíveis ao checkout.

O grupo de concorrência `scheduled-migration` impede duas execuções simultâneas desse workflow, sem cancelar a que está em andamento quando uma nova começa, e o job tem limite de trinta minutos. Essa proteção não alcança processos iniciados fora do GitHub Actions.

## Resultado e recuperação

Falha da migração é relançada e faz o comando falhar. O passo de artefato tenta guardar `rpa_etl.log` mesmo em falha, desde que a verificação das conexões tenha permitido o início. A retenção do artefato é de quatorze dias.

O ETL confirma transações por etapa. Reverter o código ou repetir o workflow não desfaz a carga anterior. Uma nova execução retoma pelos mapeamentos, e uma reversão de dados exige procedimento sobre o destino. O repositório não fornece comando de rollback nem backup automático.

O acesso da pessoa importada depende do provisionamento separado da conta de autenticação. A execução do workflow não realiza essa etapa. <!-- PENDENTE: 4 -->
