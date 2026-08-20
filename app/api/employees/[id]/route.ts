import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const updateSchema = z.object({
  name: z.string().min(2).max(120).optional(),
  roleName: z.string().max(80).nullable().optional(),
  document: z.string().max(30).nullable().optional(),
  monthlySalary: z.coerce.number().nonnegative().nullable().optional(),
  hiredAt: z.coerce.date().nullable().optional(),
  status: z.enum(["ACTIVE", "INACTIVE"]).optional(),
});

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canManage(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);

  const { id } = await params;
  const current = await prisma.employee.findFirst({
    where: { id, restaurantId: auth.ctx.restaurant.id },
  });
  if (!current) return jsonError("Funcionário não encontrado", 404);

  const parsed = updateSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados inválidos");

  const updated = await prisma.employee.update({
    where: { id },
    data: parsed.data,
  });

  await audit({
    restaurantId: auth.ctx.restaurant.id,
    actorUserId: auth.ctx.user.id,
    action: "UPDATE",
    entity: "Employee",
    entityId: id,
    data: parsed.data,
  });

  return NextResponse.json(decimalToNumber(updated));
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canManage(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);

  const { id } = await params;
  const current = await prisma.employee.findFirst({
    where: { id, restaurantId: auth.ctx.restaurant.id },
  });
  if (!current) return jsonError("Funcionário não encontrado", 404);

  const payrollCount = await prisma.payrollEntry.count({
    where: { restaurantId: auth.ctx.restaurant.id, employeeId: id },
  });

  if (payrollCount > 0) {
    return jsonError(
      "Este funcionário possui folhas de pagamento registradas. Para preservar o histórico financeiro, desative o funcionário em vez de excluí-lo.",
      409
    );
  }

  await prisma.employee.delete({ where: { id } });

  await audit({
    restaurantId: auth.ctx.restaurant.id,
    actorUserId: auth.ctx.user.id,
    action: "DELETE",
    entity: "Employee",
    entityId: id,
    data: { name: current.name },
  });

  return NextResponse.json({ ok: true });
}
