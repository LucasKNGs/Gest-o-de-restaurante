import { Role } from "@prisma/client";
import { getSessionUser } from "@/backend/lib/session";
import { prisma } from "@/backend/lib/prisma";

export async function getRestaurantContext() {
  const user = await getSessionUser();
  if (!user) return null;
  const membership = await prisma.restaurantMember.findFirst({
    where: { userId: user.id, active: true },
    include: { restaurant: true },
    orderBy: { createdAt: "asc" },
  });
  if (!membership) return null;
  return { user, restaurant: membership.restaurant, membership };
}

export function canWrite(role: Role) {
  return [Role.OWNER, Role.ADMIN, Role.MANAGER, Role.OPERATOR].includes(role);
}

export function canManage(role: Role) {
  return [Role.OWNER, Role.ADMIN, Role.MANAGER].includes(role);
}

export function canAdmin(role: Role) {
  return [Role.OWNER, Role.ADMIN].includes(role);
}
