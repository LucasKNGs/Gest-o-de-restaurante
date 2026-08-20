import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { requireApiContext, decimalToNumber } from "@/backend/lib/http";

export async function GET() {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  const { restaurant } = auth.ctx;
  const now = new Date();
  const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const nextDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);

  const [dayIncome, dayExpense, monthIncome, monthExpense, pendingPayables, recent, accounts] = await Promise.all([
    prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, type: "INCOME", occurredAt: { gte: dayStart, lt: nextDay } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, type: "EXPENSE", occurredAt: { gte: dayStart, lt: nextDay } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, type: "INCOME", occurredAt: { gte: monthStart, lt: nextMonth } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, type: "EXPENSE", occurredAt: { gte: monthStart, lt: nextMonth } }, _sum: { amount: true } }),
    prisma.accountsPayable.aggregate({ where: { restaurantId: restaurant.id, status: { in: ["PENDING", "OVERDUE"] } }, _sum: { amount: true }, _count: true }),
    prisma.transaction.findMany({ where: { restaurantId: restaurant.id }, orderBy: { occurredAt: "desc" }, take: 8, include: { category: true, account: true, creator: { select: { name: true } } } }),
    prisma.account.findMany({ where: { restaurantId: restaurant.id, active: true }, orderBy: { name: "asc" } }),
  ]);

  const accountBalances = await Promise.all(accounts.map(async (account) => {
    const [income, expense] = await Promise.all([
      prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, accountId: account.id, type: "INCOME" }, _sum: { amount: true } }),
      prisma.transaction.aggregate({ where: { restaurantId: restaurant.id, accountId: account.id, type: "EXPENSE" }, _sum: { amount: true } }),
    ]);
    return {
      id: account.id,
      name: account.name,
      type: account.type,
      balance: Number(account.initialBalance) + Number(income._sum.amount || 0) - Number(expense._sum.amount || 0),
    };
  }));

  const data = {
    day: { income: Number(dayIncome._sum.amount || 0), expense: Number(dayExpense._sum.amount || 0) },
    month: { income: Number(monthIncome._sum.amount || 0), expense: Number(monthExpense._sum.amount || 0) },
    pendingPayables: { amount: Number(pendingPayables._sum.amount || 0), count: pendingPayables._count },
    recent,
    accountBalances,
  };
  return NextResponse.json(decimalToNumber(data));
}
