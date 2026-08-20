import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { requireApiContext, decimalToNumber } from "@/backend/lib/http";

export async function GET() {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  const id = auth.ctx.restaurant.id;
  const [categories, accounts, suppliers, employees] = await Promise.all([
    prisma.category.findMany({ where: { restaurantId: id, active: true }, orderBy: { name: "asc" } }),
    prisma.account.findMany({ where: { restaurantId: id, active: true }, orderBy: { name: "asc" } }),
    prisma.supplier.findMany({ where: { restaurantId: id, active: true }, orderBy: { name: "asc" } }),
    prisma.employee.findMany({ where: { restaurantId: id, status: "ACTIVE" }, orderBy: { name: "asc" } }),
  ]);
  return NextResponse.json(decimalToNumber({ categories, accounts, suppliers, employees }));
}
