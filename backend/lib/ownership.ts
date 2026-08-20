import { prisma } from "@/backend/lib/prisma";

export async function refsBelongToRestaurant(restaurantId: string, refs: {
  categoryId?: string | null;
  accountId?: string | null;
  supplierId?: string | null;
  employeeId?: string | null;
}) {
  const checks: Promise<unknown>[] = [];
  if (refs.categoryId) checks.push(prisma.category.findFirst({ where: { id: refs.categoryId, restaurantId }, select: { id: true } }));
  if (refs.accountId) checks.push(prisma.account.findFirst({ where: { id: refs.accountId, restaurantId }, select: { id: true } }));
  if (refs.supplierId) checks.push(prisma.supplier.findFirst({ where: { id: refs.supplierId, restaurantId }, select: { id: true } }));
  if (refs.employeeId) checks.push(prisma.employee.findFirst({ where: { id: refs.employeeId, restaurantId }, select: { id: true } }));
  const results = await Promise.all(checks);
  return results.every(Boolean);
}
