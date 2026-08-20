import { NextResponse } from "next/server";
import { PaymentMethod, TransactionType } from "@prisma/client";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage, canWrite } from "@/backend/lib/context";
import { audit } from "@/backend/lib/audit";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { refsBelongToRestaurant } from "@/backend/lib/ownership";

const schema = z.object({
  type: z.enum(TransactionType).optional(),
  description: z.string().min(2).max(180).optional(),
  amount: z.coerce.number().positive().optional(),
  occurredAt: z.coerce.date().optional(),
  paymentMethod: z.enum(PaymentMethod).optional(),
  categoryId: z.string().nullable().optional(),
  accountId: z.string().nullable().optional(),
  notes: z.string().max(1000).nullable().optional(),
});

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canWrite(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);
  const { id } = await params;
  const current = await prisma.transaction.findFirst({ where: { id, restaurantId: auth.ctx.restaurant.id } });
  if (!current) return jsonError("Movimentação não encontrada", 404);
  if (current.reference?.startsWith("PAYABLE:") || current.reference?.startsWith("PAYROLL:")) return jsonError("Movimentação automática não pode ser editada diretamente", 409);
  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados inválidos");
  if (!(await refsBelongToRestaurant(auth.ctx.restaurant.id, { categoryId: parsed.data.categoryId, accountId: parsed.data.accountId }))) return jsonError("Categoria ou conta não pertence ao restaurante", 403);
  const row = await prisma.transaction.update({ where: { id }, data: parsed.data, include: { category: true, account: true, creator: { select: { name: true } } } });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "UPDATE", entity: "Transaction", entityId: id, data: { before: decimalToNumber(current), after: parsed.data } });
  return NextResponse.json(decimalToNumber(row));
}

export async function DELETE(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canManage(auth.ctx.membership.role)) return jsonError("Somente gerente/admin pode excluir", 403);
  const { id } = await params;
  const current = await prisma.transaction.findFirst({ where: { id, restaurantId: auth.ctx.restaurant.id } });
  if (!current) return jsonError("Movimentação não encontrada", 404);
  if (current.reference?.startsWith("PAYABLE:") || current.reference?.startsWith("PAYROLL:")) return jsonError("Movimentação automática não pode ser excluída diretamente; faça um estorno controlado", 409);
  await prisma.transaction.delete({ where: { id } });
  await audit({ restaurantId: auth.ctx.restaurant.id, actorUserId: auth.ctx.user.id, action: "DELETE", entity: "Transaction", entityId: id, data: decimalToNumber(current) });
  return NextResponse.json({ ok: true });
}
