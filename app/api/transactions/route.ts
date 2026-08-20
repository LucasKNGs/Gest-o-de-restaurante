import { NextResponse } from "next/server";
import { PaymentMethod, TransactionType } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canWrite } from "@/backend/lib/context";
import { audit } from "@/backend/lib/audit";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { refsBelongToRestaurant } from "@/backend/lib/ownership";

const createSchema = z.object({
  type: z.enum(TransactionType),
  description: z.string().min(2).max(180),
  amount: z.coerce.number().positive(),
  occurredAt: z.coerce.date(),
  paymentMethod: z.enum(PaymentMethod),
  categoryId: z.string().nullable().optional(),
  accountId: z.string().nullable().optional(),
  notes: z.string().max(1000).nullable().optional(),
});

export async function GET(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  const url = new URL(request.url);
  const type = url.searchParams.get("type");
  const from = url.searchParams.get("from");
  const to = url.searchParams.get("to");

  const rows = await prisma.transaction.findMany({
    where: {
      restaurantId: auth.ctx.restaurant.id,
      ...(type === "INCOME" || type === "EXPENSE" ? { type } : {}),
      ...(from || to ? { occurredAt: { ...(from ? { gte: new Date(from) } : {}), ...(to ? { lte: new Date(to + "T23:59:59") } : {}) } } : {}),
    },
    orderBy: [{ occurredAt: "desc" }, { createdAt: "desc" }],
    take: 500,
    include: { category: true, account: true, creator: { select: { name: true } } },
  });
  return NextResponse.json(decimalToNumber(rows));
}

export async function POST(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canWrite(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);
  const parsed = createSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados da movimentação inválidos");
  const d = parsed.data;
  if (!(await refsBelongToRestaurant(auth.ctx.restaurant.id, { categoryId: d.categoryId, accountId: d.accountId }))) return jsonError("Categoria ou conta não pertence ao restaurante", 403);

  const row = await prisma.transaction.create({
    data: {
      restaurantId: auth.ctx.restaurant.id,
      createdByUserId: auth.ctx.user.id,
      type: d.type,
      description: d.description,
      amount: d.amount,
      occurredAt: d.occurredAt,
      paymentMethod: d.paymentMethod,
      categoryId: d.categoryId || null,
      accountId: d.accountId || null,
      notes: d.notes || null,
    },
    include: { category: true, account: true, creator: { select: { name: true } } },
  });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "CREATE", entity: "Transaction", entityId: row.id, data: d });
  return NextResponse.json(decimalToNumber(row), { status: 201 });
}
