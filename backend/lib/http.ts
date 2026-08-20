import { NextResponse } from "next/server";
import { getRestaurantContext } from "@/backend/lib/context";

export function jsonError(message: string, status = 400) {
  return NextResponse.json({ error: message }, { status });
}

export async function requireApiContext() {
  const ctx = await getRestaurantContext();
  if (!ctx) return { error: jsonError("Não autenticado", 401) } as const;
  return { ctx } as const;
}

export function decimalToNumber<T>(value: T): T {
  if (value && typeof value === "object") {
    if (value instanceof Date) return value;
    if (Array.isArray(value)) return value.map(decimalToNumber) as T;
    if ("toNumber" in (value as object) && typeof (value as { toNumber?: unknown }).toNumber === "function") {
      return (value as unknown as { toNumber: () => number }).toNumber() as T;
    }
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([k, v]) => [k, decimalToNumber(v)])) as T;
  }
  return value;
}
