<p align="center">
  <img src="../assets/readme/banners/postgresql.png" alt="PostgreSQL" width="100%">
</p>

# Visão de produto

A rotina importa cadastros de uma base antiga para a plataforma. Seu público é a equipe que prepara e acompanha essa transferência. Não há uma tela de migração para a pessoa usuária. O resultado aparece nos cadastros de negócio, sujeito às regras de acesso e publicação da plataforma.

## O que é transferido

A importação cobre os cadastros com correspondência implementada.

- Pessoas, informações de contato e endereços.
- Empresas fornecedoras e compradoras, com vínculos dos responsáveis.
- Unidades e projetos técnicos que tenham os relacionamentos exigidos.
- Profissionais, profissões, afiliações e qualificações.
- Planos e assinaturas vinculadas a fornecedores.
- Modelos de placas, ofertas e estoque de produtos com especificações elétricas.
- Fotos de demonstração associadas aos cadastros que ainda não têm as imagens verificadas pela rotina.

## Regras da transferência

A origem é consultada e não recebe alterações da rotina. O destino recebe os registros novos e as correspondências usadas nas próximas execuções. Essa correspondência permite retomar uma importação, mas não significa que toda mudança posterior na base antiga será copiada.

Os dados obrigatórios que não existem na origem recebem valores sintéticos ou padrões. Isso inclui documentos pessoais, datas, endereço incompleto e preço ausente ou não positivo. A hipótese adotada é que a equipe revisa esses campos antes de colocar os cadastros em operação. O código não implementa uma etapa de aprovação dessa revisão. <!-- PENDENTE: 2 -->

Uma empresa pode ser reaproveitada pelo documento empresarial. O responsável recebe vínculo de administrador quando não está ligado a outra empresa. Quando já há outro vínculo, a rotina mantém o existente e ignora o novo vínculo. A regra de escolha entre esses casos depende de confirmação. <!-- PENDENTE: 5 -->

Produtos sem especificações elétricas não são importados. Projetos dependem de um dono comprador e de uma unidade correspondente. Os projetos criados ficam abertos, e os modelos de placa entram em análise. A importação não transfere todas as informações históricas, como mensagens, postagens e participantes de projeto que não são donos.

## Acesso das pessoas importadas

Importar uma pessoa não cria sua conta de acesso. A senha antiga não é reaproveitada. O cadastro recebe um identificador que precisa corresponder a uma conta criada separadamente. A hipótese é que o responsável fará esse provisionamento antes de disponibilizar o acesso, mas o procedimento ainda não está definido neste repositório. <!-- PENDENTE: 4 -->

## Relação com a plataforma

O cadastro central recebe as informações de negócio. O serviço de autenticação continua responsável pelas contas. O catálogo de imagens fornece as referências opcionais de fotos já publicadas. A equipe pode executar a rotina manualmente e também pode habilitar a execução diária, conforme os ambientes autorizados. <!-- PENDENTE: 1 -->
