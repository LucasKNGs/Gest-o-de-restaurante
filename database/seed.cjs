const bcrypt = require("bcryptjs");
const { PrismaClient, Role, CategoryType, AccountType, TransactionType, PaymentMethod } = require("@prisma/client");

const prisma = new PrismaClient();

async function main() {
  const adminEmail = process.env.SEED_ADMIN_EMAIL || "admin@restaurante.local";
  const adminPassword = process.env.SEED_ADMIN_PASSWORD || "admin123";
  const restaurantName = process.env.SEED_RESTAURANT_NAME || "Restaurante Demo";
  const passwordHash = await bcrypt.hash(adminPassword, 12);

  const user = await prisma.user.upsert({
    where: { email: adminEmail },
    update: { name: "Administrador" },
    create: { name: "Administrador", email: adminEmail, passwordHash },
  });

  let restaurant = await prisma.restaurant.findFirst({ where: { name: restaurantName } });
  if (!restaurant) restaurant = await prisma.restaurant.create({ data: { name: restaurantName } });

  await prisma.restaurantMember.upsert({
    where: { restaurantId_userId: { restaurantId: restaurant.id, userId: user.id } },
    update: { role: Role.OWNER, active: true },
    create: { restaurantId: restaurant.id, userId: user.id, role: Role.OWNER },
  });

  const categories = [
    ["Vendas", "vendas", CategoryType.INCOME],
    ["Delivery", "delivery", CategoryType.INCOME],
    ["Fornecedores", "fornecedores", CategoryType.EXPENSE],
    ["Aluguel", "aluguel", CategoryType.EXPENSE],
    ["Energia", "energia", CategoryType.EXPENSE],
    ["Água", "agua", CategoryType.EXPENSE],
    ["Folha de pagamento", "folha", CategoryType.EXPENSE],
    ["Impostos", "impostos", CategoryType.EXPENSE],
    ["Manutenção", "manutencao", CategoryType.EXPENSE],
    ["Outros", "outros", CategoryType.BOTH],
  ];
  for (const [name, slug, type] of categories) {
    await prisma.category.upsert({
      where: { restaurantId_slug: { restaurantId: restaurant.id, slug } },
      update: { name, type, active: true },
      create: { restaurantId: restaurant.id, name, slug, type },
    });
  }

  const accountNames = [
    ["Caixa físico", AccountType.CASH],
    ["Conta bancária", AccountType.BANK],
    ["Pix", AccountType.PIX],
    ["Cartões a receber", AccountType.CARD_CLEARING],
  ];
  for (const [name, type] of accountNames) {
    await prisma.account.upsert({
      where: { restaurantId_name: { restaurantId: restaurant.id, name } },
      update: { type, active: true },
      create: { restaurantId: restaurant.id, name, type },
    });
  }

  const count = await prisma.transaction.count({ where: { restaurantId: restaurant.id } });
  if (count === 0) {
    const sales = await prisma.category.findUnique({ where: { restaurantId_slug: { restaurantId: restaurant.id, slug: "vendas" } } });
    const suppliers = await prisma.category.findUnique({ where: { restaurantId_slug: { restaurantId: restaurant.id, slug: "fornecedores" } } });
    const cash = await prisma.account.findUnique({ where: { restaurantId_name: { restaurantId: restaurant.id, name: "Caixa físico" } } });
    const pix = await prisma.account.findUnique({ where: { restaurantId_name: { restaurantId: restaurant.id, name: "Pix" } } });

    await prisma.transaction.createMany({ data: [
      { restaurantId: restaurant.id, createdByUserId: user.id, categoryId: sales?.id, accountId: cash?.id, type: TransactionType.INCOME, description: "Vendas balcão", amount: 1850, occurredAt: new Date(), paymentMethod: PaymentMethod.CASH },
      { restaurantId: restaurant.id, createdByUserId: user.id, categoryId: sales?.id, accountId: pix?.id, type: TransactionType.INCOME, description: "Vendas Pix", amount: 2400, occurredAt: new Date(), paymentMethod: PaymentMethod.PIX },
      { restaurantId: restaurant.id, createdByUserId: user.id, categoryId: suppliers?.id, accountId: cash?.id, type: TransactionType.EXPENSE, description: "Compra de hortifruti", amount: 620, occurredAt: new Date(), paymentMethod: PaymentMethod.CASH },
    ] });
  }

  console.log("Seed concluído.");
  console.log(`Login: ${adminEmail} / ${adminPassword}`);
}

main().catch((e) => { console.error(e); process.exit(1); }).finally(() => prisma.$disconnect());
