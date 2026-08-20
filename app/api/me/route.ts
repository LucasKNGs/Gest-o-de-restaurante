import { NextResponse } from "next/server";
import { getRestaurantContext } from "@/backend/lib/context";

export async function GET() {
  const ctx = await getRestaurantContext();
  if (!ctx) return NextResponse.json({ error: "Não autenticado" }, { status: 401 });
  return NextResponse.json({
    user: { id: ctx.user.id, name: ctx.user.name, email: ctx.user.email },
    restaurant: { id: ctx.restaurant.id, name: ctx.restaurant.name, currency: ctx.restaurant.currency },
    role: ctx.membership.role,
  });
}
