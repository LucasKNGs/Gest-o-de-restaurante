# Como aproveitar o `finance-web`

Este pacote foi montado como uma V1 independente porque o ambiente usado para gerar os arquivos conseguiu ler o repositório público no GitHub, mas não conseguiu cloná-lo integralmente.

A arquitetura segue a mesma base: Next.js, TypeScript, Prisma e PostgreSQL. O ponto principal da mudança é deixar de modelar tudo diretamente por `userId` e passar a usar `restaurantId` + membros/papéis.

Se você quiser reaproveitar o visual do `finance-web`, o caminho mais seguro é:

1. Use este projeto como backend/modelo de dados de referência.
2. Copie componentes visuais do projeto antigo para `components/`.
3. Adapte as páginas antigas para consumir as APIs desta V1.
4. Não copie de volta o schema antigo de `Income`/`Expense` por usuário, porque ele reintroduz o problema multiusuário.
5. Antes de uso comercial, confirme a licença/permissão do código original.

O arquivo crítico desta V1 é `database/prisma/schema.prisma`. Ele representa o novo domínio empresarial.
