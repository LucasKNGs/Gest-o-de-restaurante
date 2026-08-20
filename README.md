# Restaurante Financeiro V1

Sistema web de gestão financeira para um restaurante, baseado na mesma linha tecnológica do projeto `finance-web`: Next.js + TypeScript + Prisma + PostgreSQL.

## O que esta V1 já faz

- Login com sessão segura em cookie `httpOnly`.
- Um restaurante compartilhado por vários usuários.
- Papéis: `OWNER`, `ADMIN`, `MANAGER`, `OPERATOR`, `VIEWER`.
- Dashboard com entradas, saídas, saldo de caixa e contas pendentes.
- Entradas e saídas com categoria, conta/caixa, forma de pagamento e usuário responsável.
- Categorias de receita/despesa.
- Contas/caixas separados: dinheiro, banco, Pix, cartões etc.
- Abertura e fechamento de caixa com saldo esperado, contado e diferença.
- Fornecedores.
- Contas a pagar; ao dar baixa, gera automaticamente uma saída financeira.
- Funcionários e folha operacional; ao pagar, gera automaticamente uma saída.
- Estoque básico com entrada, saída, ajuste, estoque mínimo e custo informado.
- Equipe de acesso ao sistema.
- Auditoria das principais ações.
- Exportação das movimentações para Excel.
- Isolamento por `restaurantId` e validação dos IDs relacionados para evitar cruzamento entre empresas.

## O que NÃO está incluído

- Integração automática com banco/Pix/maquininhas.
- Conciliação bancária automática.
- Emissão fiscal/NF-e/NFC-e.
- Folha trabalhista oficial, eSocial ou cálculo de encargos.
- Contabilidade completa por regime de competência.
- Ficha técnica de pratos/CMV automático.

Esses itens exigem integrações, regras fiscais/contábeis ou dados específicos do restaurante e devem ser uma segunda etapa.

## Pré-requisitos

- Node.js 22 ou compatível.
- Docker Desktop (forma mais simples para subir PostgreSQL localmente) ou um PostgreSQL próprio.

## Rodar localmente

### 1. Banco de dados

Na raiz do projeto:

```bash
docker compose -f database/docker-compose.yml up -d
```

### 2. Variáveis de ambiente

Copie:

```bash
cp .env.example .env
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

A configuração padrão já aponta para o PostgreSQL do Docker.

### 3. Instalar dependências

```bash
npm install
```

### 4. Criar banco e Prisma Client

```bash
npm run db:generate
npm run db:push
```

### 5. Popular dados iniciais

```bash
npm run db:seed
```

Usuário inicial:

- E-mail: `admin@restaurante.local`
- Senha: `admin123`

**Troque essa senha antes de usar em produção.**

### 6. Rodar

```bash
npm run dev
```

Abra `http://localhost:3000`.

## Produção

Uma combinação simples é:

- Frontend/backend Next.js: Vercel.
- PostgreSQL: Neon, Supabase, Railway ou outro PostgreSQL gerenciado.

Em produção, configure `DATABASE_URL` no provedor, rode `npm run db:generate` durante build e aplique o schema com uma estratégia de migração controlada. Para um primeiro protótipo, `db:push` é aceitável; para produção real, prefira `prisma migrate` e backups.

## Estrutura importante

```text
app/
  (auth)/login/             Login
  (protected)/              Telas autenticadas
  api/                      APIs
backend/lib/
  context.ts                Restaurante atual + papel do usuário
  ownership.ts              Proteção contra IDs de outra empresa
  session.ts                Sessões
  audit.ts                  Auditoria
database/prisma/schema.prisma
                            Modelo completo de dados
```

## Segurança e regras

- Toda API sensível exige sessão.
- Escrita respeita papéis.
- Exclusões financeiras são mais restritas que lançamentos.
- Contas pagas não são simplesmente apagadas.
- Referências como `categoryId`, `accountId` e `supplierId` são validadas contra o restaurante atual.
- Logs de auditoria registram criações, alterações, exclusões e baixas relevantes.

## Observação financeira importante

O dashboard mostra **fluxo de caixa** (dinheiro que entrou e saiu). Isso não deve ser apresentado ao cliente como “lucro contábil” sem tratamento de estoque, competência, CMV, impostos e demais ajustes contábeis.

## Próxima evolução recomendada

1. Troca/recuperação de senha e convites por e-mail.
2. Fechamento de caixa por turno.
3. Importação de extrato OFX/CSV.
4. Conciliação de Pix e cartão.
5. Ficha técnica + baixa automática de estoque por venda.
6. Dashboard de CMV e margem por produto.
7. Backups, monitoramento e testes automatizados.
