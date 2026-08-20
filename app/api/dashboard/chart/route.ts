import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { requireApiContext } from "@/backend/lib/http";

type RangeKey = "week" | "month" | "year" | "all";

type Bucket = {
  key: string;
  label: string;
  income: number;
  expense: number;
  balance: number;
};

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function dayKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function monthKey(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
}

function monthLabel(date: Date) {
  return date
    .toLocaleDateString("pt-BR", { month: "short", year: "2-digit" })
    .replace(" de ", "/");
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function makeDailyBuckets(days: number, now: Date): Bucket[] {
  return Array.from({ length: days }, (_, index) => {
    const date = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() - (days - 1 - index),
      12,
      0,
      0,
      0
    );

    return {
      key: dayKey(date),
      label: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      income: 0,
      expense: 0,
      balance: 0,
    };
  });
}

function makeMonthlyBuckets(start: Date, end: Date): Bucket[] {
  const result: Bucket[] = [];
  let cursor = new Date(start.getFullYear(), start.getMonth(), 1, 12, 0, 0, 0);
  const last = new Date(end.getFullYear(), end.getMonth(), 1, 12, 0, 0, 0);

  while (cursor <= last) {
    result.push({
      key: monthKey(cursor),
      label: monthLabel(cursor),
      income: 0,
      expense: 0,
      balance: 0,
    });
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1, 12, 0, 0, 0);
  }

  return result;
}

export async function GET(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;

  const url = new URL(request.url);
  const rawRange = url.searchParams.get("range");
  const range: RangeKey = ["week", "month", "year", "all"].includes(rawRange || "")
    ? (rawRange as RangeKey)
    : "month";

  const now = new Date();
  let start: Date | null = null;
  let buckets: Bucket[] = [];
  let grouping: "day" | "month" = "day";

  if (range === "week") {
    start = startOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6));
    buckets = makeDailyBuckets(7, now);
  } else if (range === "month") {
    start = startOfDay(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 29));
    buckets = makeDailyBuckets(30, now);
  } else if (range === "year") {
    grouping = "month";
    start = new Date(now.getFullYear(), now.getMonth() - 11, 1, 0, 0, 0, 0);
    buckets = makeMonthlyBuckets(start, now);
  } else {
    grouping = "month";
    const oldest = await prisma.transaction.findFirst({
      where: { restaurantId: auth.ctx.restaurant.id },
      orderBy: { occurredAt: "asc" },
      select: { occurredAt: true },
    });

    if (oldest) {
      start = new Date(oldest.occurredAt.getFullYear(), oldest.occurredAt.getMonth(), 1, 0, 0, 0, 0);
      buckets = makeMonthlyBuckets(start, now);
    } else {
      start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
      buckets = makeMonthlyBuckets(start, now);
    }
  }

  const transactions = await prisma.transaction.findMany({
    where: {
      restaurantId: auth.ctx.restaurant.id,
      ...(start ? { occurredAt: { gte: start } } : {}),
    },
    orderBy: { occurredAt: "asc" },
    select: {
      type: true,
      amount: true,
      occurredAt: true,
    },
  });

  const byKey = new Map(buckets.map((bucket) => [bucket.key, bucket]));

  for (const transaction of transactions) {
    const key = grouping === "month" ? monthKey(transaction.occurredAt) : dayKey(transaction.occurredAt);
    const bucket = byKey.get(key);
    if (!bucket) continue;

    const amount = Number(transaction.amount);
    if (transaction.type === "INCOME") bucket.income += amount;
    else bucket.expense += amount;

    bucket.balance = bucket.income - bucket.expense;
  }

  return NextResponse.json({
    range,
    grouping,
    points: buckets,
    generatedAt: new Date().toISOString(),
  });
}
