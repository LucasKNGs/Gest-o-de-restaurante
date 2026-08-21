"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

export type CrudField = {
  name: string;
  label: string;
  kind: "text" | "textarea" | "number" | "date" | "checkbox" | "select" | "relation";
  required?: boolean;
  options?: string[];
  relationApi?: string | null;
  relationName?: string | null;
  prismaType?: string;
  currency?: boolean;
};

type Props = {
  title: string;
  subtitle: string;
  apiBase: string;
  fields: CrudField[];
  columns: string[];
  payableMode?: boolean;
};

type Row = Record<string, any>;

const enumPt: Record<string, string> = {
  INCOME: "Entrada", EXPENSE: "Saída", ENTRY: "Entrada", EXIT: "Saída",
  ADJUSTMENT: "Ajuste", PENDING: "Pendente", PAID: "Pago",
  OVERDUE: "Atrasado", CANCELED: "Cancelado", CANCELLED: "Cancelado",
  ACTIVE: "Ativo", INACTIVE: "Inativo", CASH: "Dinheiro", PIX: "Pix",
  CARD: "Cartão", CREDIT_CARD: "Cartão de crédito",
  DEBIT_CARD: "Cartão de débito", BANK_TRANSFER: "Transferência",
  TRANSFER: "Transferência", BOLETO: "Boleto",
};

function rowsFrom(data: any): Row[] {
  if (Array.isArray(data)) return data;
  if (!data || typeof data !== "object") return [];
  const keys = ["items", "data", "rows", "suppliers", "transactions", "payables", "employees", "inventory", "stockItems"];
  for (const key of keys) if (Array.isArray(data[key])) return data[key];
  for (const value of Object.values(data)) if (Array.isArray(value)) return value as Row[];
  return [];
}

async function body(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try { return JSON.parse(text); } catch { return { message: text }; }
}

function message(data: any, fallback: string) {
  return data?.error || data?.message || data?.details || fallback;
}

function dateInput(value: any) {
  if (!value) return "";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) return `${match[1]}-${match[2]}-${match[3]}`;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

function dateBR(value: any) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric"
  }).format(d);
}

function moneyBR(value: any) {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "—");
  return new Intl.NumberFormat("pt-BR", {
    style: "currency", currency: "BRL"
  }).format(n);
}

function empty(fields: CrudField[]) {
  const result: Record<string, any> = {};
  for (const field of fields) result[field.name] = field.kind === "checkbox" ? false : "";
  return result;
}

function display(row: Row, field: CrudField) {
  if (field.relationName && row[field.relationName]) {
    const rel = row[field.relationName];
    return String(rel.name || rel.nome || rel.description || rel.email || rel.id || "—");
  }
  const value = row[field.name];
  if (value === null || value === undefined || value === "") return "—";
  if (field.kind === "date") return dateBR(value);
  if (field.kind === "checkbox") return value ? "Ativo" : "Inativo";
  if (field.currency) return moneyBR(value);
  return enumPt[String(value)] || String(value);
}

export default function CrudManager({
  title, subtitle, apiBase, fields, columns, payableMode = false
}: Props) {
  const [rows, setRows] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const [values, setValues] = useState<Record<string, any>>(() => empty(fields));
  const [relations, setRelations] = useState<Record<string, Row[]>>({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const fieldMap = useMemo(
    () => Object.fromEntries(fields.map((field) => [field.name, field])),
    [fields]
  );

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(apiBase, { cache: "no-store", credentials: "include" });
      const data = await body(res);
      if (!res.ok) throw new Error(message(data, "Erro ao carregar os dados."));
      setRows(rowsFrom(data));
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar os dados.");
    } finally {
      setLoading(false);
    }
  }

  async function loadRelations() {
    const entries = await Promise.all(
      fields.filter((field) => field.kind === "relation" && field.relationApi)
        .map(async (field) => {
          try {
            const res = await fetch(field.relationApi!, { cache: "no-store", credentials: "include" });
            const data = await body(res);
            return [field.name, res.ok ? rowsFrom(data) : []] as const;
          } catch {
            return [field.name, []] as const;
          }
        })
    );
    setRelations(Object.fromEntries(entries));
  }

  useEffect(() => {
    load();
    loadRelations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  const filtered = useMemo(() => {
    const q = query.trim().toLocaleLowerCase("pt-BR");
    if (!q) return rows;
    return rows.filter((row) => JSON.stringify(row).toLocaleLowerCase("pt-BR").includes(q));
  }, [rows, query]);

  function newItem() {
    setEditing(null);
    setValues(empty(fields));
    setError("");
    setModal(true);
  }

  function edit(row: Row) {
    const next = empty(fields);
    for (const field of fields) {
      const raw = row[field.name];
      next[field.name] =
        field.kind === "date" ? dateInput(raw) :
        field.kind === "checkbox" ? Boolean(raw) :
        raw ?? "";
    }
    setEditing(row);
    setValues(next);
    setError("");
    setModal(true);
  }

  function payload() {
    const result: Record<string, any> = {};
    for (const field of fields) {
      let value = values[field.name];

      if (field.kind === "number") {
        value = value === "" || value == null ? null : Number(String(value).replace(",", "."));
      }
      if (field.kind === "checkbox") value = Boolean(value);
      if (field.kind === "relation" && value === "") value = null;
      if (!field.required && value === "") value = null;

      if (field.kind === "date") {
        if (!value) value = null;
        else if (field.prismaType === "DateTime") value = new Date(`${value}T12:00:00`).toISOString();
      }

      result[field.name] = value;
    }
    return result;
  }

  async function tryMany(
    requests: Array<{ url: string; method: string; data?: any }>,
    fallback: string
  ) {
    let last: any = null;
    for (const request of requests) {
      const res = await fetch(request.url, {
        method: request.method,
        credentials: "include",
        headers: request.data !== undefined ? { "Content-Type": "application/json" } : undefined,
        body: request.data !== undefined ? JSON.stringify(request.data) : undefined,
      });
      const data = await body(res);
      if (res.ok) return data;
      last = data;
      if (![404, 405].includes(res.status)) throw new Error(message(data, fallback));
    }
    throw new Error(message(last, fallback));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");

    try {
      const data = payload();

      if (!editing) {
        await tryMany([{ url: apiBase, method: "POST", data }], "Não foi possível cadastrar.");
      } else {
        const id = editing.id;
        await tryMany([
          { url: `${apiBase}/${id}`, method: "PATCH", data },
          { url: `${apiBase}/${id}`, method: "PUT", data },
          { url: `${apiBase}?id=${encodeURIComponent(id)}`, method: "PATCH", data },
          { url: apiBase, method: "PATCH", data: { id, ...data } },
          { url: apiBase, method: "PUT", data: { id, ...data } },
        ], "Não foi possível editar.");
      }

      setModal(false);
      await load();
    } catch (e: any) {
      setError(e?.message || "Erro ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(row: Row) {
    if (!confirm("Tem certeza que deseja excluir este registro?")) return;
    try {
      const id = row.id;
      await tryMany([
        { url: `${apiBase}/${id}`, method: "DELETE" },
        { url: `${apiBase}?id=${encodeURIComponent(id)}`, method: "DELETE" },
        { url: apiBase, method: "DELETE", data: { id } },
      ], "Não foi possível excluir.");
      await load();
    } catch (e: any) {
      setError(e?.message || "Erro ao excluir.");
    }
  }

  async function pay(row: Row) {
    if (!confirm("Confirmar o pagamento desta conta?")) return;
    try {
      const id = row.id;
      const paidAt = new Date().toISOString();
      await tryMany([
        { url: `${apiBase}/${id}/pay`, method: "POST", data: {} },
        { url: `${apiBase}/${id}/settle`, method: "POST", data: {} },
        { url: `${apiBase}/${id}/mark-paid`, method: "POST", data: {} },
        { url: `${apiBase}/${id}`, method: "PATCH", data: { status: "PAID", paidAt } },
        { url: apiBase, method: "PATCH", data: { id, status: "PAID", paidAt } },
      ], "Não foi possível dar baixa.");
      await load();
    } catch (e: any) {
      setError(e?.message || "Erro ao dar baixa.");
    }
  }

  const tableFields = columns.map((name) => fieldMap[name]).filter(Boolean) as CrudField[];

  return (
    <section className="crud-page">
      <header className="crud-header">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <button className="crud-plus" type="button" onClick={newItem} aria-label="Adicionar" title="Adicionar">+</button>
      </header>

      <div className="crud-toolbar">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Pesquisar..." />
        <button type="button" onClick={load}>Atualizar</button>
      </div>

      {error ? <div className="crud-error">{error}</div> : null}

      <div className="crud-card">
        {loading ? (
          <div className="crud-empty">Carregando...</div>
        ) : filtered.length === 0 ? (
          <div className="crud-empty">Nenhum registro encontrado.</div>
        ) : (
          <div className="crud-scroll">
            <table className="crud-table">
              <thead>
                <tr>
                  {tableFields.map((field) => <th key={field.name}>{field.label}</th>)}
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, index) => (
                  <tr key={row.id ?? index}>
                    {tableFields.map((field) => <td key={field.name}>{display(row, field)}</td>)}
                    <td className="crud-actions">
                      {payableMode && String(row.status || "").toUpperCase() !== "PAID" ? (
                        <button className="pay" onClick={() => pay(row)}>Dar baixa</button>
                      ) : null}
                      <button className="edit" onClick={() => edit(row)}>Editar</button>
                      <button className="delete" onClick={() => remove(row)}>Excluir</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal ? (
        <div className="crud-overlay" onMouseDown={(e) => {
          if (e.target === e.currentTarget && !saving) setModal(false);
        }}>
          <div className="crud-modal" role="dialog" aria-modal="true">
            <div className="crud-modal-title">
              <h2>{editing ? "Editar registro" : "Novo registro"}</h2>
              <button type="button" onClick={() => setModal(false)}>×</button>
            </div>

            <form onSubmit={submit}>
              <div className="crud-grid">
                {fields.map((field) => (
                  <label key={field.name} className={field.kind === "textarea" ? "wide" : ""}>
                    <span>{field.label}{field.required ? " *" : ""}</span>

                    {field.kind === "textarea" ? (
                      <textarea
                        value={values[field.name] ?? ""}
                        required={field.required}
                        onChange={(e) => setValues((old) => ({ ...old, [field.name]: e.target.value }))}
                      />
                    ) : field.kind === "checkbox" ? (
                      <input
                        type="checkbox"
                        checked={Boolean(values[field.name])}
                        onChange={(e) => setValues((old) => ({ ...old, [field.name]: e.target.checked }))}
                      />
                    ) : field.kind === "select" ? (
                      <select
                        value={values[field.name] ?? ""}
                        required={field.required}
                        onChange={(e) => setValues((old) => ({ ...old, [field.name]: e.target.value }))}
                      >
                        <option value="">Selecione</option>
                        {(field.options || []).map((option) => (
                          <option key={option} value={option}>{enumPt[option] || option}</option>
                        ))}
                      </select>
                    ) : field.kind === "relation" ? (
                      <select
                        value={values[field.name] ?? ""}
                        required={field.required}
                        onChange={(e) => setValues((old) => ({ ...old, [field.name]: e.target.value }))}
                      >
                        <option value="">Selecione</option>
                        {(relations[field.name] || []).map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.name || option.nome || option.description || option.email || option.id}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={field.kind === "number" ? "number" : field.kind === "date" ? "date" : "text"}
                        lang={field.kind === "date" ? "pt-BR" : undefined}
                        step={field.kind === "number" ? "0.01" : undefined}
                        placeholder={field.kind === "date" ? "dd/mm/aaaa" : undefined}
                        value={values[field.name] ?? ""}
                        required={field.required}
                        onChange={(e) => setValues((old) => ({ ...old, [field.name]: e.target.value }))}
                      />
                    )}
                  </label>
                ))}
              </div>

              <div className="crud-form-actions">
                <button type="button" className="cancel" onClick={() => setModal(false)}>Cancelar</button>
                <button type="submit" className="save" disabled={saving}>
                  {saving ? "Salvando..." : editing ? "Salvar alterações" : "Cadastrar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <style jsx global>{`
        .crud-page { width: 100%; }
        .crud-header { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:18px; }
        .crud-header h1 { margin:0; font-size:30px; color:#111827; }
        .crud-header p { margin:6px 0 0; color:#64748b; }
        .crud-plus { width:46px; height:46px; border:0; border-radius:12px; background:#16a34a; color:white; font-size:31px; cursor:pointer; box-shadow:0 8px 20px rgba(22,163,74,.22); }
        .crud-plus:hover { background:#15803d; }
        .crud-toolbar { display:flex; gap:10px; margin-bottom:14px; }
        .crud-toolbar input { flex:1; max-width:440px; border:1px solid #dbe1ea; border-radius:10px; padding:11px 13px; }
        .crud-toolbar button { border:0; border-radius:9px; padding:11px 14px; cursor:pointer; background:#e2e8f0; }
        .crud-card { background:white; border:1px solid #e2e8f0; border-radius:15px; overflow:hidden; }
        .crud-scroll { overflow:auto; }
        .crud-table { width:100%; min-width:760px; border-collapse:collapse; }
        .crud-table th { text-align:left; padding:14px 16px; font-size:12px; color:#64748b; text-transform:uppercase; background:#f8fafc; border-bottom:1px solid #e2e8f0; }
        .crud-table td { padding:14px 16px; border-bottom:1px solid #eef2f7; color:#1e293b; }
        .crud-table tbody tr:hover { background:#fafafa; }
        .crud-actions { display:flex; gap:7px; justify-content:flex-end; }
        .crud-actions button { border:0; border-radius:8px; padding:8px 10px; cursor:pointer; font-weight:650; }
        .crud-actions .edit { background:#e0f2fe; color:#075985; }
        .crud-actions .delete { background:#fee2e2; color:#991b1b; }
        .crud-actions .pay { background:#dcfce7; color:#166534; }
        .crud-empty { padding:34px; text-align:center; color:#64748b; }
        .crud-error { margin:10px 0; padding:11px 13px; border-radius:10px; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
        .crud-overlay { position:fixed; z-index:1000; inset:0; display:grid; place-items:center; padding:20px; background:rgba(15,23,42,.52); }
        .crud-modal { width:min(760px,100%); max-height:90vh; overflow:auto; background:white; border-radius:18px; box-shadow:0 24px 70px rgba(15,23,42,.3); }
        .crud-modal-title { display:flex; justify-content:space-between; align-items:center; padding:20px 22px; border-bottom:1px solid #e5e7eb; }
        .crud-modal-title h2 { margin:0; font-size:21px; }
        .crud-modal-title button { width:36px; height:36px; border:0; border-radius:9px; font-size:25px; cursor:pointer; background:#f1f5f9; }
        .crud-modal form { padding:20px 22px; }
        .crud-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:15px; }
        .crud-grid label { display:flex; flex-direction:column; gap:6px; color:#334155; font-size:13px; }
        .crud-grid label span { font-weight:600; }
        .crud-grid input:not([type="checkbox"]), .crud-grid select, .crud-grid textarea { width:100%; min-height:42px; box-sizing:border-box; border:1px solid #dbe1ea; border-radius:9px; padding:9px 11px; background:white; }
        .crud-grid textarea { min-height:92px; resize:vertical; }
        .crud-grid .wide { grid-column:1/-1; }
        .crud-form-actions { display:flex; justify-content:flex-end; gap:10px; margin-top:20px; padding-top:16px; border-top:1px solid #e5e7eb; }
        .crud-form-actions button { border:0; border-radius:9px; padding:11px 16px; cursor:pointer; font-weight:650; }
        .crud-form-actions .save { background:#16a34a; color:white; }
        .crud-form-actions .cancel { background:#e2e8f0; color:#0f172a; }
        @media (max-width:720px) {
          .crud-grid { grid-template-columns:1fr; }
          .crud-grid .wide { grid-column:auto; }
          .crud-header h1 { font-size:25px; }
          .crud-actions { flex-wrap:wrap; }
        }
      `}</style>
    </section>
  );
}
