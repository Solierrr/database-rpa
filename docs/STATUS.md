<p align="center">
  <img src="../assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

# Situação da migração

O levantamento abaixo foi feito na main em 2026-10-30. Os testes de integração mencionados no README de origem são um registro anterior do projeto e não foram reexecutados nesta documentação.

## Presente no código

- A rotina importa usuários e executa doze etapas complementares, seguidas da associação opcional de imagens (2026-10-30).
- A carga básica grava `users`, `contact`, `person` e seus mapeamentos na mesma transação. As etapas complementares consultam correspondências para reaproveitar registros (2026-10-30).
- As regras locais tratam usernames, slugs, marcas legadas, dimensões em metros, preço positivo e cargos dos responsáveis (2026-10-30).
- O Actions permite disparo manual e evento diário condicionado a variável. O checklist descrevia somente execução manual (2026-10-30). <!-- PENDENTE: 1 -->
- O CI executa byte compilation e unittest. O workflow de qualidade executa Ruff. Os testes unitários cobrem helpers de schema e imagens, sem bancos (2026-10-30).

## Limitações operacionais

- Não há confirmação dos bancos autorizados, da localização dos segredos ou da ativação do cron. `VAULT_FOLDERS` está vazio no Makefile (2026-10-30). <!-- PENDENTE: 1 -->
- Não há dry run, rollback automático, controle de versão do schema de destino ou uma única transação para a execução inteira (2026-10-30).
- A origem é lida por SQL, mas o engine não impõe modo somente leitura. A restrição precisa vir do usuário PostgreSQL (2026-10-30).
- A concorrência é controlada apenas no workflow. Processos locais simultâneos não compartilham esse bloqueio (2026-10-30).
- A tabela de mapeamento é criada pelo ETL dentro do `coredb`, embora o checklist previsse ausência de estrutura própria. Falta definir sua manutenção junto ao schema de negócio (2026-10-30). <!-- PENDENTE: 3 -->
- Reexecução não sincroniza alterações em todos os cadastros já importados. Telefones podem ser atualizados novamente, enquanto várias outras etapas pulam registros mapeados. Remover linhas de domínio sem revisar os mapeamentos pode deixar correspondências inválidas (2026-10-30).
- A leitura dos usuários carrega todos os registros da origem antes do filtro. Não há processamento incremental por data nem paginação (2026-10-30).
- As tabelas `projeto` e `usuario_projeto` são consultadas diretamente. Se não existem, ocorre erro SQL, sem omissão automática da etapa (2026-10-30).
- Segredos ausentes fazem o workflow pular a execução com aviso. Saída sem erro não comprova que houve importação nem que todos os registros foram aproveitados (2026-10-30).

## Dados que exigem revisão

- Campos obrigatórios ausentes recebem dados sintéticos ou padrões, incluindo documentos, nascimento, endereço, preço e datas. Situação de assinatura desconhecida vira `PAID`, e validade ausente de registro usa emissão acrescida de 3.650 dias. Não há etapa automática de aprovação desses preenchimentos (2026-10-30). <!-- PENDENTE: 2 -->
- `auth_id` é criado sem conta no `authdb`. A senha legada não é reutilizada. O procedimento de provisionamento continua externo (2026-10-30). <!-- PENDENTE: 4 -->
- Reutilizar empresa por CNPJ não altera seu tipo. Um usuário já vinculado a outra empresa pode deixar a nova empresa sem o vínculo pretendido de responsável (2026-10-30). <!-- PENDENTE: 5 -->
- Produtos sem equipamento elétrico e registros sem pais correspondentes podem ser ignorados. As contagens e os avisos precisam ser revisados após a execução (2026-10-30).
- A seleção de imagens é determinística para a chave do registro persistido. Os UUIDs novos não são determinísticos. Empresa ou modelo com qualquer foto é excluído da seleção, por isso conjuntos parciais não são completados nessa etapa (2026-10-30).

## Informações sem importador correspondente

As exclusões são declaradas nas constantes ao fim de `extended_migration.py`. Elas descrevem o escopo desta migração, sem afirmar que a plataforma inteira não tem funcionalidades equivalentes (2026-10-30).

| Grupo | Fontes não importadas |
|---|---|
| Interação e conteúdo | `contato`, `avaliacao`, `postagem`, `chat`, `mensagem`, `usuario_chat`, `midia` |
| Serviços e agenda | `servico`, `compromisso` |
| Qualificação de fornecedor | `certificacao`, `equipamento_certificacao` |
| Projeto e organização | `documento_projeto`, `loja_filial` |
| Administração e auditoria | `admin`, `telefone_admin`, `log_acessos_admin`, `historico_alteracoes` |

A descrição do perfil, o nome e a descrição do projeto e os participantes que não são donos também ficam de fora. Uma `qualificacao` de profissional é tratada pela rotina, mesmo que a fonte distinta `certificacao` de fornecedor não tenha importador (2026-10-30).
