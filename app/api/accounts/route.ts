import { NextResponse } from "next/server";
import { AccountType } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const schema = z.object({ name: z.string().min(2).max(80), type: z.enum(AccountType), initialBalance: z.coerce.number().default(0) });

export async function GET() {
  const auth = await requireApiContext(); if ("error" in auth) return auth.error;
  const accounts = await prisma.account.findMany({ where: { restaurantId: auth.ctx.restaurant.id }, orderBy: { name: "asc" } });
  const data = await Promise.all(accounts.map(async a => {
    const [inc, exp] = await Promise.all([
      prisma.transaction.aggregate({ where: { restaurantId: auth.ctx.restaurant.id, accountId: a.id, type: "INCOME" }, _sum: { amount: true } }),
      prisma.transaction.aggregate({ where: { restaurantId: auth.ctx.restaurant.id, accountId: a.id, type: "EXPENSE" }, _sum: { amount: true } }),
    ]);
    return { ...a, balance: Number(a.initialBalance) + Number(inc._sum.amount || 0) - Number(exp._sum.amount || 0) };
  }));
  return NextResponse.json(decimalToNumber(data));
}

export async function POST(request: Request) {
  const auth = await requireApiContext(); if ("error" in auth) return auth.error;
  if (!canManage(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);
  const parsed = schema.safeParse(await request.json().catch(() => null)); if (!parsed.success) return jsonError("Dados inválidos");
  const row = await prisma.account.create({ data: { restaurantId: auth.ctx.restaurant.id, ...parsed.data } });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "CREATE", entity: "Account", entityId: row.id, data: parsed.data });
  return NextResponse.json(decimalToNumber(row), { status: 201 });
}
