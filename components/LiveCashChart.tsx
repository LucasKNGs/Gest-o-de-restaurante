"use client";

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
