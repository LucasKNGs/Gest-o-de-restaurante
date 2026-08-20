from pathlib import Path

root = Path(".")

api_file = root / "app/api/dashboard/chart/route.ts"
component_file = root / "components/LiveCashChart.tsx"
dashboard_file = root / "app/(protected)/dashboard/page.tsx"

api_file.parent.mkdir(parents=True, exist_ok=True)
component_file.parent.mkdir(parents=True, exist_ok=True)

api_file.write_text("""import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { requireApiContext } from "@/backend/lib/http";

function dateKey(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export async function GET(request: Request) {
  const auth = await requireApiContext();
  if ("error" in auth) return auth.error;

  const url = new URL(request.url);
  const requestedDays = Number(url.searchParams.get("days") || 14);
  const days = Math.min(30, Math.max(7, Number.isFinite(requestedDays) ? requestedDays : 14));

  const now = new Date();
  const start = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() - (days - 1),
    0,
    0,
    0,
    0
  );

  const transactions = await prisma.transaction.findMany({
    where: {
      restaurantId: auth.ctx.restaurant.id,
      occurredAt: { gte: start },
    },
    orderBy: { occurredAt: "asc" },
    select: {
      type: true,
      amount: true,
      occurredAt: true,
    },
  });

  const points = Array.from({ length: days }, (_, index) => {
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
      date: dateKey(date),
      label: date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
      }),
      income: 0,
      expense: 0,
      balance: 0,
    };
  });

  const byDate = new Map(points.map((point) => [point.date, point]));

  for (const transaction of transactions) {
    const point = byDate.get(dateKey(transaction.occurredAt));
    if (!point) continue;

    const amount = Number(transaction.amount);

    if (transaction.type === "INCOME") {
      point.income += amount;
    } else {
      point.expense += amount;
    }

    point.balance = point.income - point.expense;
  }

  return NextResponse.json({
    points,
    generatedAt: new Date().toISOString(),
  });
}
""", encoding="utf-8")

component_file.write_text("""\"use client\";

import { useCallback, useEffect, useMemo, useState } from "react";

type Point = {
  date: string;
  label: string;
  income: number;
  expense: number;
  balance: number;
};

type ApiResponse = {
  points: Point[];
  generatedAt: string;
};

const WIDTH = 900;
const HEIGHT = 300;
const LEFT = 64;
const RIGHT = 20;
const TOP = 24;
const BOTTOM = 42;

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
  const [days, setDays] = useState(14);
  const [points, setPoints] = useState<Point[]>([]);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/chart?days=${days}`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

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
  }, [days]);

  useEffect(() => {
    setLoading(true);
    load();

    const timer = window.setInterval(load, 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  const chart = useMemo(() => {
    const plotWidth = WIDTH - LEFT - RIGHT;
    const plotHeight = HEIGHT - TOP - BOTTOM;

    const maxValue = Math.max(
      1,
      ...points.flatMap((point) => [point.income, point.expense])
    );

    const ceiling = maxValue * 1.12;

    const x = (index: number) =>
      points.length <= 1
        ? LEFT
        : LEFT + (index / (points.length - 1)) * plotWidth;

    const y = (value: number) =>
      TOP + plotHeight - (value / ceiling) * plotHeight;

    const incomeLine = points
      .map((point, index) => `${x(index)},${y(point.income)}`)
      .join(" ");

    const expenseLine = points
      .map((point, index) => `${x(index)},${y(point.expense)}`)
      .join(" ");

    const grid = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4;
      const value = ceiling * (1 - ratio);
      return {
        y: TOP + plotHeight * ratio,
        value,
      };
    });

    return { x, y, incomeLine, expenseLine, grid };
  }, [points]);

  const today = points.at(-1);
  const labelStep = points.length >= 25 ? 4 : points.length >= 12 ? 2 : 1;

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
            Entradas e saídas. Atualização automática a cada 10 segundos.
          </div>
        </div>

        <div className="field" style={{ minWidth: 150 }}>
          <label>Período</label>
          <select
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={14}>Últimos 14 dias</option>
            <option value={30}>Últimos 30 dias</option>
          </select>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 18,
          flexWrap: "wrap",
          marginTop: 16,
          marginBottom: 8,
          fontSize: 13,
        }}
      >
        <span>
          <span style={{ color: "var(--success)", fontWeight: 800 }}>●</span>{" "}
          Entradas
        </span>
        <span>
          <span style={{ color: "var(--danger)", fontWeight: 800 }}>●</span>{" "}
          Saídas
        </span>
        {today && (
          <span className="muted">
            Hoje: {money(today.income)} entrando · {money(today.expense)} saindo
          </span>
        )}
      </div>

      {error && <div className="notice error">{error}</div>}

      <div
        style={{
          width: "100%",
          overflow: "hidden",
          minHeight: 260,
          display: "grid",
          placeItems: "center",
        }}
      >
        {loading && points.length === 0 ? (
          <div className="muted">Carregando gráfico...</div>
        ) : points.length === 0 ? (
          <div className="empty">Ainda não há dados para mostrar.</div>
        ) : (
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            role="img"
            aria-label={`Gráfico de entradas e saídas dos últimos ${days} dias`}
            style={{
              width: "100%",
              height: "auto",
              display: "block",
              minHeight: 240,
            }}
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
              if (index % labelStep !== 0 && index !== points.length - 1) {
                return null;
              }

              return (
                <text
                  key={point.date}
                  x={chart.x(index)}
                  y={HEIGHT - 12}
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
              <g key={`${point.date}-dots`}>
                <circle
                  cx={chart.x(index)}
                  cy={chart.y(point.income)}
                  r="3.5"
                  fill="var(--surface)"
                  stroke="var(--success)"
                  strokeWidth="2"
                >
                  <title>
                    {`${point.label} — Entradas: ${money(point.income)}`}
                  </title>
                </circle>
                <circle
                  cx={chart.x(index)}
                  cy={chart.y(point.expense)}
                  r="3.5"
                  fill="var(--surface)"
                  stroke="var(--danger)"
                  strokeWidth="2"
                >
                  <title>
                    {`${point.label} — Saídas: ${money(point.expense)}`}
                  </title>
                </circle>
              </g>
            ))}
          </svg>
        )}
      </div>

      <div
        className="muted"
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
          fontSize: 12,
          marginTop: 4,
        }}
      >
        <span>
          O gráfico muda sozinho quando novas movimentações entram no sistema.
        </span>
        <span>
          {updatedAt
            ? `Última atualização: ${updatedAt.toLocaleTimeString("pt-BR")}`
            : "Aguardando atualização..."}
        </span>
      </div>
    </div>
  );
}
""", encoding="utf-8")

if not dashboard_file.exists():
    raise SystemExit(
        "ERRO: não encontrei app/(protected)/dashboard/page.tsx. "
        "Execute este arquivo na raiz do projeto."
    )

dashboard = dashboard_file.read_text(encoding="utf-8")

import_line = 'import LiveCashChart from "@/components/LiveCashChart";\n'
if import_line not in dashboard:
    marker = 'import { redirect } from "next/navigation";\n'
    if marker in dashboard:
        dashboard = dashboard.replace(marker, marker + import_line, 1)
    else:
        dashboard = import_line + dashboard

if "<LiveCashChart />" not in dashboard:
    marker = '      <div className="grid grid-2" style={{ marginTop: 16 }}>'
    if marker not in dashboard:
        raise SystemExit(
            "ERRO: não encontrei o ponto de inserção no dashboard. "
            "O arquivo pode ter sido alterado."
        )
    dashboard = dashboard.replace(
        marker,
        '      <LiveCashChart />\n' + marker,
        1,
    )

dashboard_file.write_text(dashboard, encoding="utf-8")

print("Gráfico ao vivo adicionado com sucesso.")
print()
print("O que foi criado:")
print(" - components/LiveCashChart.tsx")
print(" - app/api/dashboard/chart/route.ts")
print(" - dashboard atualizado para exibir o gráfico")
print()
print("Recursos:")
print(" - Entradas x saídas")
print(" - Períodos de 7, 14 ou 30 dias")
print(" - Atualização automática a cada 10 segundos")
print(" - Funciona no celular")
print(" - Não precisa instalar biblioteca nova")
print()
print("Agora rode: npm run dev")
