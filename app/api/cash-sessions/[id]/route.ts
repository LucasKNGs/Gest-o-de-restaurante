import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canWrite } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const schema = z.object({ closingCounted: z.coerce.number().nonnegative(), notes: z.string().max(500).nullable().optional() });

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canWrite(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados inválidos");
  const { id } = await params;
  const row = await prisma.cashSession.findFirst({ where: { id, restaurantId: auth.ctx.restaurant.id } });
  if (!row) return jsonError("Caixa não encontrado", 404);
  if (row.status === "CLOSED") return jsonError("Caixa já fechado", 409);
  const closedAt = new Date();
  const [income, expense] = await Promise.all([
    prisma.transaction.aggregate({ where: { restaurantId: auth.ctx.restaurant.id, accountId: row.accountId, type: "INCOME", occurredAt: { gte: row.openedAt, lte: closedAt } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: auth.ctx.restaurant.id, accountId: row.accountId, type: "EXPENSE", occurredAt: { gte: row.openedAt, lte: closedAt } }, _sum: { amount: true } }),
  ]);
  const expected = Number(row.openingBalance) + Number(income._sum.amount || 0) - Number(expense._sum.amount || 0);
  const updated = await prisma.cashSession.update({ where: { id }, data: { status: "CLOSED", closingCounted: parsed.data.closingCounted, closedAt, closedByUserId: auth.ctx.user.id, notes: parsed.data.notes ?? row.notes }, include: { account: true, openedBy: { select: { name: true } }, closedBy: { select: { name: true } } } });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "CLOSE", entity: "CashSession", entityId: id, data: { counted: parsed.data.closingCounted, expected, difference: parsed.data.closingCounted - expected } });
  return NextResponse.json(decimalToNumber({ ...updated, expectedBalance: expected, difference: parsed.data.closingCounted - expected }));
}
