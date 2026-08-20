import { prisma } from "@/backend/lib/prisma";

export async function audit(input: {
  restaurantId: string;
  actorUserId: string;
  action: string;
  entity: string;
  entityId?: string;
  data?: unknown;
}) {
  await prisma.auditLog.create({
    data: {
      restaurantId: input.restaurantId,
      actorUserId: input.actorUserId,
      action: input.action,
      entity: input.entity,
      entityId: input.entityId,
      data: input.data as never,
    },
  });
}
