import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canWrite } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { refsBelongToRestaurant } from "@/backend/lib/ownership";
import { audit } from "@/backend/lib/audit";

const openSchema = z.object({
  accountId: z.string(),
  openingBalance: z.coerce.number().nonnegative(),
  notes: z.string().max(500).nullable().optional(),
});

async function withExpected(restaurantId: string, row: any) {
  const until = row.closedAt ?? new Date();
  const [income, expense] = await Promise.all([
    prisma.transaction.aggregate({ where: { restaurantId, accountId: row.accountId, type: "INCOME", occurredAt: { gte: row.openedAt, lte: until } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId, accountId: row.accountId, type: "EXPENSE", occurredAt: { gte: row.openedAt, lte: until } }, _sum: { amount: true } }),
  ]);
  const expected = Number(row.openingBalance) + Number(income._sum.amount || 0) - Number(expense._sum.amount || 0);
  const counted = row.closingCounted == null ? null : Number(row.closingCounted);
  return { ...row, expectedBalance: expected, difference: counted == null ? null : counted - expected };
}

export async function GET() {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  const rows = await prisma.cashSession.findMany({
    where: { restaurantId: auth.ctx.restaurant.id },
    orderBy: { openedAt: "desc" },
    take: 50,
    include: { account: true, openedBy: { select: { name: true } }, closedBy: { select: { name: true } } },
  });
  return NextResponse.json(decimalToNumber(await Promise.all(rows.map(r => withExpected(auth.ctx.restaurant.id, r)))));
}

export async function POST(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canWrite(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);
  const parsed = openSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados inválidos");
  if (!(await refsBelongToRestaurant(auth.ctx.restaurant.id, { accountId: parsed.data.accountId }))) return jsonError("Conta inválida", 403);
  const account = await prisma.account.findFirst({ where: { id: parsed.data.accountId, restaurantId: auth.ctx.restaurant.id } });
  if (!account || account.type !== "CASH") return jsonError("Abertura de caixa exige uma conta do tipo CASH");
  const existing = await prisma.cashSession.findFirst({ where: { restaurantId: auth.ctx.restaurant.id, accountId: account.id, status: "OPEN" } });
  if (existing) return jsonError("Já existe um caixa aberto para esta conta", 409);
  const row = await prisma.cashSession.create({ data: { restaurantId: auth.ctx.restaurant.id, accountId: account.id, openedByUserId: auth.ctx.user.id, openingBalance: parsed.data.openingBalance, notes: parsed.data.notes || null }, include: { account: true, openedBy: { select: { name: true } }, closedBy: { select: { name: true } } } });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "OPEN", entity: "CashSession", entityId: row.id, data: parsed.data });
  return NextResponse.json(decimalToNumber(await withExpected(auth.ctx.restaurant.id, row)), { status: 201 });
}
