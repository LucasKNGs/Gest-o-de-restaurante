from pathlib import Path

ROOT = Path('.')

def write(rel: str, content: str):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f'[OK] {rel}')

# 1) API do gráfico: semana, mês, ano e tempo total
write('app/api/dashboard/chart/route.ts', r'''import { NextResponse } from "next/server";
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
''')

# 2) Componente do gráfico ao vivo
write('components/LiveCashChart.tsx', r'''"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RangeKey = "week" | "month" | "year" | "all";

type Point = {
  key: string;
  label: string;
  income: number;
  expense: number;
  balance: number;
};

type ApiResponse = {
  range: RangeKey;
  grouping: "day" | "month";
  points: Point[];
  generatedAt: string;
};

const WIDTH = 900;
const HEIGHT = 310;
const LEFT = 68;
const RIGHT = 20;
const TOP = 24;
const BOTTOM = 48;

const ranges: { value: RangeKey; label: string }[] = [
  { value: "week", label: "1 semana" },
  { value: "month", label: "1 mês" },
  { value: "year", label: "1 ano" },
  { value: "all", label: "Tempo total" },
];

function money(value: number) {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function compactMoney(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export default function LiveCashChart() {
  const [range, setRange] = useState<RangeKey>("month");
  const [points, setPoints] = useState<Point[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/chart?range=${range}`, {
        cache: "no-store",
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data: ApiResponse = await response.json();
      setPoints(data.points);
      setUpdatedAt(new Date(data.generatedAt));
      setError("");
    } catch (err) {
      console.error("Erro ao atualizar gráfico:", err);
      setError("Não foi possível atualizar o gráfico agora.");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    setLoading(true);
    load();
    const timer = window.setInterval(load, 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  const totals = useMemo(
    () =>
      points.reduce(
        (acc, point) => ({
          income: acc.income + point.income,
          expense: acc.expense + point.expense,
        }),
        { income: 0, expense: 0 }
      ),
    [points]
  );

  const chart = useMemo(() => {
    const plotWidth = WIDTH - LEFT - RIGHT;
    const plotHeight = HEIGHT - TOP - BOTTOM;
    const maxValue = Math.max(1, ...points.flatMap((point) => [point.income, point.expense]));
    const ceiling = maxValue * 1.12;

    const x = (index: number) =>
      points.length <= 1 ? LEFT : LEFT + (index / (points.length - 1)) * plotWidth;

    const y = (value: number) => TOP + plotHeight - (value / ceiling) * plotHeight;

    const incomeLine = points.map((point, index) => `${x(index)},${y(point.income)}`).join(" ");
    const expenseLine = points.map((point, index) => `${x(index)},${y(point.expense)}`).join(" ");

    const grid = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4;
      return {
        y: TOP + plotHeight * ratio,
        value: ceiling * (1 - ratio),
      };
    });

    return { x, y, incomeLine, expenseLine, grid };
  }, [points]);

  const labelStep = Math.max(1, Math.ceil(points.length / 8));
  const activeLabel = ranges.find((item) => item.value === range)?.label || "Período";

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 className="section-title" style={{ marginBottom: 5 }}>
            Fluxo de caixa ao vivo
          </h2>
          <div className="muted" style={{ fontSize: 13 }}>
            Entradas e saídas do período selecionado. Atualização automática a cada 10 segundos.
          </div>
        </div>

        <div className="field" style={{ minWidth: 170 }}>
          <label>Período</label>
          <select value={range} onChange={(event) => setRange(event.target.value as RangeKey)}>
            {ranges.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: 10,
          marginTop: 16,
        }}
      >
        <div style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12 }}>
          <div className="muted" style={{ fontSize: 12 }}>Entradas · {activeLabel}</div>
          <strong style={{ color: "var(--success)", fontSize: 18 }}>{money(totals.income)}</strong>
        </div>
        <div style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12 }}>
          <div className="muted" style={{ fontSize: 12 }}>Saídas · {activeLabel}</div>
          <strong style={{ color: "var(--danger)", fontSize: 18 }}>{money(totals.expense)}</strong>
        </div>
        <div style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12 }}>
          <div className="muted" style={{ fontSize: 12 }}>Saldo · {activeLabel}</div>
          <strong style={{ fontSize: 18 }}>{money(totals.income - totals.expense)}</strong>
        </div>
      </div>

      <div style={{ display: "flex", gap: 18, flexWrap: "wrap", marginTop: 14, fontSize: 13 }}>
        <span><span style={{ color: "var(--success)", fontWeight: 800 }}>●</span> Entradas</span>
        <span><span style={{ color: "var(--danger)", fontWeight: 800 }}>●</span> Saídas</span>
      </div>

      {error && <div className="notice error" style={{ marginTop: 12 }}>{error}</div>}

      <div
        style={{
          width: "100%",
          overflow: "hidden",
          minHeight: 260,
          display: "grid",
          placeItems: "center",
          marginTop: 6,
        }}
      >
        {loading && points.length === 0 ? (
          <div className="muted">Carregando gráfico...</div>
        ) : points.length === 0 ? (
          <div className="empty">Ainda não há movimentações para mostrar.</div>
        ) : (
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            role="img"
            aria-label={`Gráfico de entradas e saídas: ${activeLabel}`}
            style={{ width: "100%", height: "auto", display: "block", minHeight: 240 }}
          >
            {chart.grid.map((line, index) => (
              <g key={index}>
                <line
                  x1={LEFT}
                  x2={WIDTH - RIGHT}
                  y1={line.y}
                  y2={line.y}
                  stroke="var(--border)"
                  strokeWidth="1"
                />
                <text
                  x={LEFT - 10}
                  y={line.y + 4}
                  textAnchor="end"
                  fontSize="11"
                  fill="var(--muted)"
                >
                  {compactMoney(line.value)}
                </text>
              </g>
            ))}

            {points.map((point, index) => {
              if (index % labelStep !== 0 && index !== points.length - 1) return null;
              return (
                <text
                  key={point.key}
                  x={chart.x(index)}
                  y={HEIGHT - 13}
                  textAnchor="middle"
                  fontSize="11"
                  fill="var(--muted)"
                >
                  {point.label}
                </text>
              );
            })}

            <polyline
              points={chart.incomeLine}
              fill="none"
              stroke="var(--success)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            <polyline
              points={chart.expenseLine}
              fill="none"
              stroke="var(--danger)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {points.map((point, index) => (
              <g key={`${point.key}-dots`}>
                <circle
                  cx={chart.x(index)}
                  cy={chart.y(point.income)}
                  r="3.5"
                  fill="var(--surface)"
                  stroke="var(--success)"
                  strokeWidth="2"
                >
                  <title>{`${point.label} — Entradas: ${money(point.income)}`}</title>
                </circle>
                <circle
                  cx={chart.x(index)}
                  cy={chart.y(point.expense)}
                  r="3.5"
                  fill="var(--surface)"
                  stroke="var(--danger)"
                  strokeWidth="2"
                >
                  <title>{`${point.label} — Saídas: ${money(point.expense)}`}</title>
                </circle>
              </g>
            ))}
          </svg>
        )}
      </div>

      <div
        className="muted"
        style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", fontSize: 12 }}
      >
        <span>O gráfico atualiza sozinho quando novas movimentações são registradas.</span>
        <span>
          {updatedAt
            ? `Última atualização: ${updatedAt.toLocaleTimeString("pt-BR")}`
            : "Aguardando atualização..."}
        </span>
      </div>
    </div>
  );
}
''')

# Garante o gráfico no dashboard, sem duplicar
DASH = ROOT / 'app/(protected)/dashboard/page.tsx'
if DASH.exists():
    text = DASH.read_text(encoding='utf-8')
    imp = 'import LiveCashChart from "@/components/LiveCashChart";\n'
    if imp not in text:
        marker = 'import { redirect } from "next/navigation";\n'
        text = text.replace(marker, marker + imp, 1) if marker in text else imp + text
    if '<LiveCashChart />' not in text:
        marker = '      <div className="grid grid-2" style={{ marginTop: 16 }}>'
        if marker in text:
            text = text.replace(marker, '      <LiveCashChart />\n' + marker, 1)
        else:
            print('[AVISO] Não achei o ponto automático para inserir o gráfico no dashboard.')
    DASH.write_text(text, encoding='utf-8')
    print('[OK] app/(protected)/dashboard/page.tsx')
else:
    print('[AVISO] Dashboard não encontrado.')

# 3) API de funcionários: CREATE + READ
write('app/api/employees/route.ts', r'''import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { canManage } from "@/backend/lib/context";
import { requireApiContext, jsonError, decimalToNumber } from "@/backend/lib/http";
import { audit } from "@/backend/lib/audit";

const schema = z.object({
  name: z.string().min(2).max(120),
  roleName: z.string().max(80).nullable().optional(),
  document: z.string().max(30).nullable().optional(),
  monthlySalary: z.coerce.number().nonnegative().nullable().optional(),
  hiredAt: z.coerce.date().nullable().optional(),
});

export async function GET() {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;

  const rows = await prisma.employee.findMany({
    where: { restaurantId: auth.ctx.restaurant.id },
    orderBy: [{ status: "asc" }, { name: "asc" }],
  });

  return NextResponse.json(decimalToNumber(rows));
}

export async function POST(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;
  if (!canManage(auth.ctx.membership.role)) return jsonError("Sem permissão", 403);

  const parsed = schema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return jsonError("Dados inválidos");

  const row = await prisma.employee.create({
    data: {
      restaurantId: auth.ctx.restaurant.id,
      ...parsed.data,
    },
  });

  await audit({
    restaurantId: auth.ctx.restaurant.id,
    actorUserId: auth.ctx.user.id,
    action: "CREATE",
    entity: "Employee",
    entityId: row.id,
    data: parsed.data,
  });

  return NextResponse.json(decimalToNumber(row), { status: 201 });
}
''')

# 4) API de funcionário individual: UPDATE + DELETE
write('app/api/employees/[id]/route.ts', r'''import { NextResponse } from "next/server";
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
''')

# 5) Tela de funcionários com subabas e CRUD
write('app/(protected)/employees/EmployeesClient.tsx', r'''"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Employee = {
  id: string;
  name: string;
  roleName?: string | null;
  document?: string | null;
  monthlySalary?: number | null;
  status: "ACTIVE" | "INACTIVE";
  hiredAt?: string | null;
};

type Payroll = {
  id: string;
  referenceMonth: string;
  grossAmount: number;
  deductions: number;
  netAmount: number;
  dueDate: string;
  status: "PENDING" | "PAID" | "CANCELED";
  employee: Employee;
};

type Tab = "employees" | "payroll";

const paymentOptions = [
  { value: "CASH", label: "Dinheiro" },
  { value: "PIX", label: "Pix" },
  { value: "DEBIT_CARD", label: "Cartão de débito" },
  { value: "CREDIT_CARD", label: "Cartão de crédito" },
  { value: "BANK_TRANSFER", label: "Transferência bancária" },
  { value: "BOLETO", label: "Boleto" },
  { value: "OTHER", label: "Outro" },
];

function brl(value?: number | null) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function payrollStatus(status: string) {
  return (
    {
      PENDING: "Pendente",
      PAID: "Pago",
      CANCELED: "Cancelado",
    }[status] || status
  );
}

export default function EmployeesClient() {
  const [tab, setTab] = useState<Tab>("employees");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [payroll, setPayroll] = useState<Payroll[]>([]);
  const [accounts, setAccounts] = useState<{ id: string; name: string }[]>([]);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [employeesRes, payrollRes, refsRes] = await Promise.all([
      fetch("/api/employees"),
      fetch("/api/payroll"),
      fetch("/api/reference"),
    ]);

    if (employeesRes.ok) setEmployees(await employeesRes.json());
    if (payrollRes.ok) setPayroll(await payrollRes.json());
    if (refsRes.ok) setAccounts((await refsRes.json()).accounts);
  }

  useEffect(() => {
    load();
  }, []);

  const activeEmployees = useMemo(
    () => employees.filter((employee) => employee.status === "ACTIVE"),
    [employees]
  );

  async function saveEmployee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const form = event.currentTarget;
    const data = new FormData(form);
    const body = {
      name: data.get("name"),
      roleName: data.get("roleName") || null,
      document: data.get("document") || null,
      monthlySalary: data.get("monthlySalary") || null,
      hiredAt: data.get("hiredAt") ? `${data.get("hiredAt")}T12:00:00` : null,
    };

    const url = editing ? `/api/employees/${editing.id}` : "/api/employees";
    const method = editing ? "PATCH" : "POST";

    const response = await fetch(url, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível salvar o funcionário.");
      return;
    }

    setMessage(editing ? "Funcionário atualizado." : "Funcionário cadastrado.");
    setEditing(null);
    form.reset();
    await load();
  }

  async function changeStatus(employee: Employee) {
    setError("");
    setMessage("");
    const nextStatus = employee.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";

    const response = await fetch(`/api/employees/${employee.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível alterar o status.");
      return;
    }

    setMessage(nextStatus === "ACTIVE" ? "Funcionário reativado." : "Funcionário desativado.");
    if (editing?.id === employee.id) setEditing(null);
    await load();
  }

  async function removeEmployee(employee: Employee) {
    setError("");
    setMessage("");

    if (!confirm(`Excluir definitivamente o funcionário ${employee.name}?`)) return;

    const response = await fetch(`/api/employees/${employee.id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível excluir o funcionário.");
      return;
    }

    setMessage("Funcionário excluído.");
    if (editing?.id === employee.id) setEditing(null);
    await load();
  }

  async function addPayroll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const form = event.currentTarget;
    const data = new FormData(form);

    const response = await fetch("/api/payroll", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        employeeId: data.get("employeeId"),
        referenceMonth: data.get("referenceMonth"),
        grossAmount: data.get("grossAmount"),
        deductions: data.get("deductions") || 0,
        dueDate: `${data.get("dueDate")}T12:00:00`,
        notes: data.get("notes") || null,
      }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível gerar a folha.");
      return;
    }

    setMessage("Folha gerada com sucesso.");
    form.reset();
    await load();
  }

  async function payPayroll(id: string) {
    const accountList = accounts.map((account, index) => `${index + 1}. ${account.name}`).join("\n");
    const accountChoice = prompt(`Escolha a conta pelo número:\n${accountList}`, "1");
    if (accountChoice == null) return;

    const account = accounts[Number(accountChoice) - 1];
    if (!account) {
      alert("Conta inválida.");
      return;
    }

    const methodList = paymentOptions.map((item, index) => `${index + 1}. ${item.label}`).join("\n");
    const methodChoice = prompt(`Escolha a forma de pagamento:\n${methodList}`, "2");
    if (methodChoice == null) return;

    const method = paymentOptions[Number(methodChoice) - 1];
    if (!method) {
      alert("Forma de pagamento inválida.");
      return;
    }

    const response = await fetch(`/api/payroll/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        paymentMethod: method.value,
        accountId: account.id,
      }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível pagar a folha.");
      return;
    }

    setMessage("Folha paga e saída financeira registrada.");
    await load();
  }

  return (
    <main className="content">
      <h1 className="page-title">Funcionários</h1>
      <p className="page-subtitle">
        Cadastre a equipe e mantenha a geração de folhas em uma área separada.
      </p>

      <div
        className="card"
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          padding: 10,
          marginBottom: 16,
        }}
        role="tablist"
        aria-label="Seções de funcionários"
      >
        <button
          type="button"
          className={`btn ${tab === "employees" ? "primary" : ""}`}
          onClick={() => setTab("employees")}
          role="tab"
          aria-selected={tab === "employees"}
        >
          Cadastro de funcionários
        </button>
        <button
          type="button"
          className={`btn ${tab === "payroll" ? "primary" : ""}`}
          onClick={() => setTab("payroll")}
          role="tab"
          aria-selected={tab === "payroll"}
        >
          Folhas de pagamento
        </button>
      </div>

      {message && <div className="notice" style={{ marginBottom: 16 }}>{message}</div>}
      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      {tab === "employees" && (
        <>
          <div className="card">
            <h2 className="section-title">
              {editing ? `Editar ${editing.name}` : "Cadastrar funcionário"}
            </h2>

            <form
              className="form-grid"
              onSubmit={saveEmployee}
              key={editing?.id || "new-employee"}
            >
              <div className="field span-2">
                <label>Nome</label>
                <input name="name" required defaultValue={editing?.name || ""} />
              </div>

              <div className="field">
                <label>Cargo</label>
                <input name="roleName" defaultValue={editing?.roleName || ""} />
              </div>

              <div className="field">
                <label>CPF / Documento</label>
                <input name="document" defaultValue={editing?.document || ""} />
              </div>

              <div className="field">
                <label>Salário mensal</label>
                <input
                  name="monthlySalary"
                  type="number"
                  step="0.01"
                  min="0"
                  defaultValue={editing?.monthlySalary ?? ""}
                />
              </div>

              <div className="field">
                <label>Data de admissão</label>
                <input
                  name="hiredAt"
                  type="date"
                  defaultValue={editing?.hiredAt ? editing.hiredAt.slice(0, 10) : ""}
                />
              </div>

              <div className="span-4" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button className="btn primary">
                  {editing ? "Salvar alterações" : "Cadastrar funcionário"}
                </button>
                {editing && (
                  <button type="button" className="btn" onClick={() => setEditing(null)}>
                    Cancelar edição
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="section-title">Funcionários cadastrados</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Cargo</th>
                    <th>Documento</th>
                    <th>Admissão</th>
                    <th>Salário</th>
                    <th>Status</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((employee) => (
                    <tr key={employee.id}>
                      <td><strong>{employee.name}</strong></td>
                      <td>{employee.roleName || "—"}</td>
                      <td>{employee.document || "—"}</td>
                      <td>
                        {employee.hiredAt
                          ? new Date(employee.hiredAt).toLocaleDateString("pt-BR")
                          : "—"}
                      </td>
                      <td>{employee.monthlySalary == null ? "—" : brl(employee.monthlySalary)}</td>
                      <td>
                        <span className={`badge ${employee.status === "ACTIVE" ? "paid" : "pending"}`}>
                          {employee.status === "ACTIVE" ? "Ativo" : "Inativo"}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button type="button" className="btn small" onClick={() => setEditing(employee)}>
                            Editar
                          </button>
                          <button
                            type="button"
                            className="btn small"
                            onClick={() => changeStatus(employee)}
                          >
                            {employee.status === "ACTIVE" ? "Desativar" : "Reativar"}
                          </button>
                          <button
                            type="button"
                            className="btn small danger"
                            onClick={() => removeEmployee(employee)}
                          >
                            Excluir
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
              Funcionários com folhas já registradas não podem ser excluídos definitivamente; nesse caso, desative o cadastro para manter o histórico financeiro.
            </p>
          </div>
        </>
      )}

      {tab === "payroll" && (
        <>
          <div className="card">
            <h2 className="section-title">Gerar folha de pagamento</h2>
            <form className="form-grid" onSubmit={addPayroll}>
              <div className="field span-2">
                <label>Funcionário</label>
                <select name="employeeId" required>
                  <option value="">Selecione</option>
                  {activeEmployees.map((employee) => (
                    <option value={employee.id} key={employee.id}>
                      {employee.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Competência</label>
                <input name="referenceMonth" type="month" required />
              </div>

              <div className="field">
                <label>Vencimento</label>
                <input name="dueDate" type="date" required />
              </div>

              <div className="field">
                <label>Salário bruto</label>
                <input name="grossAmount" type="number" step="0.01" min="0.01" required />
              </div>

              <div className="field">
                <label>Descontos</label>
                <input name="deductions" type="number" step="0.01" min="0" defaultValue="0" />
              </div>

              <div className="field span-2">
                <label>Observação</label>
                <input name="notes" />
              </div>

              <div className="span-4">
                <button className="btn primary">Gerar folha</button>
              </div>
            </form>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="section-title">Folhas cadastradas</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Competência</th>
                    <th>Funcionário</th>
                    <th>Vencimento</th>
                    <th>Bruto</th>
                    <th>Descontos</th>
                    <th>Líquido</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {payroll.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.referenceMonth}</td>
                      <td>{entry.employee.name}</td>
                      <td>{new Date(entry.dueDate).toLocaleDateString("pt-BR")}</td>
                      <td>{brl(entry.grossAmount)}</td>
                      <td>{brl(entry.deductions)}</td>
                      <td><strong>{brl(entry.netAmount)}</strong></td>
                      <td>{payrollStatus(entry.status)}</td>
                      <td>
                        {entry.status === "PENDING" && (
                          <button
                            type="button"
                            className="btn small primary"
                            onClick={() => payPayroll(entry.id)}
                          >
                            Pagar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
''')

print('\nAlterações concluídas.')
print('- Gráfico: 1 semana, 1 mês, 1 ano e tempo total')
print('- Funcionários: subabas Cadastro de funcionários / Folhas de pagamento')
print('- CRUD: criar, listar, editar e excluir; com desativar/reativar')
print('- Exclusão protegida quando já existem folhas de pagamento')
print('\nAgora rode: npm run dev')
