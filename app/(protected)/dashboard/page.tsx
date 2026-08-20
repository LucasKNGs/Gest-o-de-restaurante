import { prisma } from "@/backend/lib/prisma";
import { getRestaurantContext } from "@/backend/lib/context";
import { redirect } from "next/navigation";

function brl(n: number) { return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

export default async function DashboardPage() {
  const ctx = await getRestaurantContext();
  if (!ctx) redirect("/login");
  const now = new Date();
  const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const nextDay = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  const [dayIn, dayOut, monthIn, monthOut, payables, recent] = await Promise.all([
    prisma.transaction.aggregate({ where: { restaurantId: ctx.restaurant.id, type: "INCOME", occurredAt: { gte: dayStart, lt: nextDay } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: ctx.restaurant.id, type: "EXPENSE", occurredAt: { gte: dayStart, lt: nextDay } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: ctx.restaurant.id, type: "INCOME", occurredAt: { gte: monthStart, lt: nextMonth } }, _sum: { amount: true } }),
    prisma.transaction.aggregate({ where: { restaurantId: ctx.restaurant.id, type: "EXPENSE", occurredAt: { gte: monthStart, lt: nextMonth } }, _sum: { amount: true } }),
    prisma.accountsPayable.aggregate({ where: { restaurantId: ctx.restaurant.id, status: { in: ["PENDING", "OVERDUE"] } }, _sum: { amount: true }, _count: true }),
    prisma.transaction.findMany({ where: { restaurantId: ctx.restaurant.id }, orderBy: { occurredAt: "desc" }, take: 10, include: { category: true, account: true } }),
  ]);
  const di = Number(dayIn._sum.amount || 0), de = Number(dayOut._sum.amount || 0), mi = Number(monthIn._sum.amount || 0), me = Number(monthOut._sum.amount || 0);
  return (
    <main className="content">
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Visão de caixa. Resultado contábil e fluxo de caixa não são a mesma coisa.</p>
      <div className="grid grid-4">
        <div className="card"><div className="kpi-label">Entradas hoje</div><div className="kpi-value success">{brl(di)}</div></div>
        <div className="card"><div className="kpi-label">Saídas hoje</div><div className="kpi-value danger">{brl(de)}</div></div>
        <div className="card"><div className="kpi-label">Saldo do dia</div><div className="kpi-value">{brl(di - de)}</div></div>
        <div className="card"><div className="kpi-label">Contas pendentes</div><div className="kpi-value">{brl(Number(payables._sum.amount || 0))}</div><small className="muted">{payables._count} lançamentos</small></div>
      </div>
      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="card"><h2 className="section-title">Mês atual</h2><p>Entradas: <strong>{brl(mi)}</strong></p><p>Saídas: <strong>{brl(me)}</strong></p><p>Saldo de caixa do período: <strong>{brl(mi-me)}</strong></p></div>
        <div className="card"><h2 className="section-title">Regra importante</h2><p className="muted">Este painel mede movimentação financeira. Para “lucro” contábil real, estoque, competência, impostos e CMV precisam ser tratados corretamente.</p></div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h2 className="section-title">Últimas movimentações</h2>
        <div className="table-wrap"><table><thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Conta</th><th>Tipo</th><th className="right">Valor</th></tr></thead><tbody>
          {recent.map((r) => <tr key={r.id}><td>{r.occurredAt.toLocaleDateString("pt-BR")}</td><td>{r.description}</td><td>{r.category?.name || "—"}</td><td>{r.account?.name || "—"}</td><td><span className={`badge ${r.type === "INCOME" ? "income" : "expense"}`}>{r.type === "INCOME" ? "Entrada" : "Saída"}</span></td><td className="right">{brl(Number(r.amount))}</td></tr>)}
        </tbody></table></div>
      </div>
    </main>
  );
}
