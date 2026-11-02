<p align="center">
  <img src="../assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

# Execução pelo workflow

O workflow recebe um disparo manual ou o evento diário às 06:00 UTC. Ele verifica a habilitação e as conexões antes de instalar dependências e executar a migração.

```mermaid
flowchart TD
    Evento[Evento do Actions] --> Manual{Disparo manual?}
    Manual -->|sim| Segredos{Duas conexões presentes?}
    Manual -->|não| Ativo{Agendamento habilitado?}
    Ativo -->|não| Ignorar[Não executar job de migração]
    Ativo -->|sim| Segredos
    Segredos -->|não| Aviso[Registrar aviso e pular a migração]
    Segredos -->|sim| Checkout[Obter código e manifesto]
    Checkout --> Instalar[Instalar Python 3.14 e dependências]
    Instalar --> Rodar[Executar python main.py]
    Rodar --> Resultado{Processo concluiu?}
    Resultado -->|sim| Sucesso[Registrar sucesso do comando]
    Resultado -->|não| Falha[Marcar falha ou timeout]
    Sucesso --> Artefato[Tentar guardar log por quatorze dias]
    Falha --> Artefato
```

A variável `RPA_SCHEDULE_ENABLED` controla apenas o evento agendado. A execução manual ignora essa condição, mas continua dependendo das duas conexões. O grupo de concorrência serializa execuções desse workflow, com timeout de trinta minutos por job.

## Casos de erro

- Secrets ausentes não provocam falha de migração, pois o comando não chega a ser executado.
- Falha de checkout, acesso ao manifesto ou instalação impede iniciar o ETL.
- Exceção no programa faz o comando falhar. As transações anteriores podem ter sido confirmadas.
- Timeout interrompe o job, sem desfazer etapas de banco já concluídas.
- Log ausente é ignorado pelo upload. O artefato não substitui uma conferência das contagens e avisos.

Os destinos e a configuração autorizada estão em [DEPLOY.md](../docs/DEPLOY.md), com as dúvidas de ambiente registradas na pendência 1.
