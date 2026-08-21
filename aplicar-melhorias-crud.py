#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Execute na raiz do projeto:
#   python aplicar-melhorias-crud.py
# Para desfazer:
#   python aplicar-melhorias-crud.py --restore

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "app"
COMPONENTS = ROOT / "components"
SCHEMA = ROOT / "database" / "prisma" / "schema.prisma"
STATE = ROOT / ".crud_patch_state.json"

EXCLUDE = {
    "id", "restaurantId", "createdAt", "updatedAt", "deletedAt",
    "createdById", "updatedById", "userId", "ownerId",
    "password", "passwordHash", "sessionId", "paidTransactionId",
}

LABELS = {
    "name": "Nome", "description": "Descrição", "document": "CNPJ/CPF",
    "phone": "Telefone", "email": "E-mail", "active": "Ativo",
    "status": "Status", "type": "Tipo", "amount": "Valor",
    "value": "Valor", "occurredAt": "Data", "date": "Data",
    "dueDate": "Vencimento", "paidAt": "Data de pagamento",
    "paymentMethod": "Forma de pagamento", "categoryId": "Categoria",
    "supplierId": "Fornecedor", "accountId": "Conta / Caixa",
    "quantity": "Quantidade", "minQuantity": "Estoque mínimo",
    "minimumQuantity": "Estoque mínimo", "unit": "Unidade",
    "unitCost": "Custo unitário", "averageCost": "Custo médio",
    "cost": "Custo", "sku": "SKU / Código", "location": "Localização",
    "role": "Cargo / Função", "position": "Cargo / Função",
    "salary": "Salário", "baseSalary": "Salário",
    "hireDate": "Data de admissão", "notes": "Observações",
    "observations": "Observações",
}

PRIMITIVES = {
    "String", "Int", "BigInt", "Float", "Decimal",
    "Boolean", "DateTime", "Json", "Bytes",
}


@dataclass
class Field:
    name: str
    type_name: str
    optional: bool
    is_list: bool
    attrs: str


@dataclass
class Model:
    name: str
    fields: list[Field]


def fail(message: str):
    print("\nERRO:", message)
    raise SystemExit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def backup(path: Path, backup_root: Path):
    if not path.exists():
        return
    rel = path.relative_to(ROOT)
    target = backup_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def code_files():
    result = []
    for base in (APP, COMPONENTS, ROOT / "backend"):
        if base.exists():
            result += list(base.rglob("*.ts"))
            result += list(base.rglob("*.tsx"))
    return result


def parse_schema(text: str):
    models = {}
    enums = {}

    for match in re.finditer(r"\bmodel\s+(\w+)\s*\{(.*?)\n\}", text, re.S):
        name, body = match.group(1), match.group(2)
        fields = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("@@"):
                continue
            fm = re.match(r"^(\w+)\s+([A-Za-z_]\w*)(\?|\[\])?\s*(.*)$", line)
            if fm:
                fname, ftype, suffix, attrs = fm.groups()
                fields.append(Field(fname, ftype, suffix == "?", suffix == "[]", attrs or ""))
        models[name] = Model(name, fields)

    for match in re.finditer(r"\benum\s+(\w+)\s*\{(.*?)\n\}", text, re.S):
        name, body = match.group(1), match.group(2)
        values = []
        for raw in body.splitlines():
            value = raw.strip().split(" ")[0]
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", value or ""):
                values.append(value)
        enums[name] = values

    return models, enums


def score_model(model: Model, kind: str):
    name = model.name.lower()
    fields = {f.name.lower() for f in model.fields}
    tokens = {
        "suppliers": ("supplier", "fornecedor", "vendor"),
        "transactions": ("transaction", "movement", "moviment"),
        "payables": ("payable", "bill", "contapagar"),
        "employees": ("employee", "funcionario", "staff"),
        "inventory": ("stockitem", "inventory", "stock", "estoque"),
    }[kind]
    wanted = {
        "suppliers": {"name", "document", "phone", "email"},
        "transactions": {"amount", "type", "categoryid", "accountid"},
        "payables": {"amount", "duedate", "supplierid", "status"},
        "employees": {"name", "salary", "role", "active"},
        "inventory": {"quantity", "unit", "minquantity", "minimumquantity"},
    }[kind]

    score = 0
    for token in tokens:
        if name == token:
            score += 30
        elif token in name:
            score += 12
    score += len(fields & wanted) * 4
    return score


def detect_model(models, kind):
    ranked = sorted(models.values(), key=lambda m: score_model(m, kind), reverse=True)
    if not ranked or score_model(ranked[0], kind) <= 0:
        return None
    return ranked[0]


def find_page(kind: str):
    path_tokens = {
        "dashboard": ("dashboard",),
        "suppliers": ("suppliers", "fornecedores"),
        "transactions": ("transactions", "movements", "movimentacoes"),
        "payables": ("payables", "contas-a-pagar", "accounts-payable"),
        "employees": ("employees", "funcionarios"),
        "inventory": ("inventory", "stock", "estoque"),
    }[kind]
    text_tokens = {
        "dashboard": ("dashboard",),
        "suppliers": ("fornecedores",),
        "transactions": ("movimentações", "movimentacoes"),
        "payables": ("contas a pagar",),
        "employees": ("funcionários", "funcionarios"),
        "inventory": ("estoque",),
    }[kind]

    ranked = []
    for path in APP.rglob("page.tsx"):
        p = str(path).lower().replace("\\", "/")
        source = read(path).lower()
        score = 0
        for token in path_tokens:
            if f"/{token}/" in p:
                score += 20
            elif token in p:
                score += 10
        for token in text_tokens:
            if token in source:
                score += 4
        if score:
            ranked.append((score, len(path.parts), path))

    if not ranked:
        return None
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked[0][2]


def api_from_route(route: Path):
    rel = route.relative_to(APP / "api")
    parts = []
    for part in rel.parts[:-1]:
        if part.startswith("["):
            break
        parts.append(part)
    return "/api/" + "/".join(parts)


def detect_api(model: Model | None, kind: str, page: Path | None):
    terms = {
        "suppliers": ("supplier", "suppliers", "fornecedor"),
        "transactions": ("transaction", "transactions", "movement"),
        "payables": ("payable", "payables", "bill"),
        "employees": ("employee", "employees", "funcionario"),
        "inventory": ("inventory", "stock", "estoque"),
    }[kind]

    if page:
        source = read(page)
        urls = re.findall(r"fetch\s*\(\s*[`\"'](/api/[^`\"'?${]+)", source)
        for url in urls:
            if any(term in url.lower() for term in terms):
                return url.rstrip("/")

    candidates = []
    for route in (APP / "api").rglob("route.ts"):
        source = read(route)
        score = 0
        low_path = str(route).lower()
        low_source = source.lower()

        if model:
            prisma_name = model.name[:1].lower() + model.name[1:]
            if f"prisma.{prisma_name}" in source:
                score += 30

        for term in terms:
            if term in low_path:
                score += 10
            if term in low_source:
                score += 2

        if score:
            candidates.append((score, route))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return api_from_route(candidates[0][1]).rstrip("/")

    return {
        "suppliers": "/api/suppliers",
        "transactions": "/api/transactions",
        "payables": "/api/payables",
        "employees": "/api/employees",
        "inventory": "/api/inventory",
    }[kind]


def relation(name: str):
    return {
        "supplierId": ("/api/suppliers", "supplier"),
        "categoryId": ("/api/categories", "category"),
        "accountId": ("/api/accounts", "account"),
        "employeeId": ("/api/employees", "employee"),
    }.get(name, (None, None))


def label(name: str):
    if name in LABELS:
        return LABELS[name]
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return value[:1].upper() + value[1:]


def field_kind(field: Field, enums):
    if field.name.endswith("Id") and relation(field.name)[0]:
        return "relation"
    if field.type_name == "Boolean":
        return "checkbox"
    if field.type_name == "DateTime" or "date" in field.name.lower() or field.name.lower().endswith("at"):
        return "date"
    if field.type_name in {"Int", "Float", "Decimal"}:
        return "number"
    if field.type_name in enums:
        return "select"
    if any(x in field.name.lower() for x in ("note", "observ", "description")):
        return "textarea"
    return "text"


def editable_fields(model: Model, models, enums):
    model_names = set(models)
    result = []

    for field in model.fields:
        if field.name in EXCLUDE or field.is_list:
            continue
        if field.type_name in model_names:
            continue
        if field.name.endswith("Id") and relation(field.name)[0] is None:
            continue
        if field.type_name not in PRIMITIVES and field.type_name not in enums:
            continue
        if field.type_name in {"Json", "Bytes", "BigInt"}:
            continue

        kind = field_kind(field, enums)
        rel_api, rel_name = relation(field.name)
        has_default = "@default" in field.attrs
        low = field.name.lower()

        result.append({
            "name": field.name,
            "label": label(field.name),
            "kind": kind,
            "required": not field.optional and not has_default and kind != "checkbox",
            "options": enums.get(field.type_name, []),
            "relationApi": rel_api,
            "relationName": rel_name,
            "prismaType": field.type_name,
            "currency": any(x in low for x in ("amount", "value", "cost", "salary", "price", "valor")),
        })

    return result[:14]


def columns(fields):
    preferred = [
        "name", "description", "document", "phone", "email", "type",
        "amount", "value", "dueDate", "occurredAt", "supplierId",
        "categoryId", "quantity", "unit", "minQuantity",
        "minimumQuantity", "cost", "unitCost", "averageCost",
        "status", "role", "salary", "active",
    ]
    names = [f["name"] for f in fields]
    result = [name for name in preferred if name in names]
    for name in names:
        if name not in result and len(result) < 7 and name not in {"notes", "observations"}:
            result.append(name)
    return result[:7]


CRUD_COMPONENT = r'''"use client";

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
'''


def page_source(kind, api, fields, cols):
    title, subtitle = {
        "suppliers": ("Fornecedores", "Cadastre, edite, pesquise e gerencie fornecedores."),
        "transactions": ("Movimentações", "Controle entradas e saídas com acesso rápido às ações."),
        "payables": ("Contas a pagar", "Gerencie vencimentos, alterações, baixas e exclusões."),
        "inventory": ("Estoque", "Gerencie itens, quantidades, custos e estoque mínimo."),
    }[kind]

    clean_fields = [{k: v for k, v in field.items() if v is not None} for field in fields]

    return f'''import CrudManager, {{ type CrudField }} from "@/components/CrudManager";

const fields: CrudField[] = {json.dumps(clean_fields, ensure_ascii=False, indent=2)};
const columns = {json.dumps(cols, ensure_ascii=False)};

export default function Page() {{
  return (
    <CrudManager
      title={json.dumps(title, ensure_ascii=False)}
      subtitle={json.dumps(subtitle, ensure_ascii=False)}
      apiBase={json.dumps(api)}
      fields={{fields}}
      columns={{columns}}
      payableMode={{{"true" if kind == "payables" else "false"}}}
    />
  );
}}
'''


def patch_dates(backup_root):
    changed = 0
    for path in code_files():
        source = read(path)
        old = source
        source = re.sub(r'\.toLocaleDateString\(\s*\)', '.toLocaleDateString("pt-BR")', source)
        source = re.sub(r'\.toLocaleDateString\(\s*["\'](?:en|en-US|pt|pt-PT)["\']\s*\)', '.toLocaleDateString("pt-BR")', source)
        if source != old:
            backup(path, backup_root)
            write(path, source)
            changed += 1

    layout = APP / "layout.tsx"
    if layout.exists():
        source = read(layout)
        old = source
        source = re.sub(r'<html\s+lang=["\'][^"\']+["\']', '<html lang="pt-BR"', source, count=1)
        if re.search(r"<html(?![^>]*\blang=)", source):
            source = re.sub(r"<html", '<html lang="pt-BR"', source, count=1)
        if source != old:
            backup(layout, backup_root)
            write(layout, source)
            changed += 1

    return changed


def patch_dashboard(backup_root):
    touched = []
    for path in code_files():
        source = read(path)
        low = source.lower()
        if not (("semana" in low or "week" in low) and ("mês" in low or "month" in low) and ("ano" in low or "year" in low)):
            continue
        if re.search(r'["\']Dia["\']', source) or re.search(r'["\']day["\']', source):
            continue

        old = source

        match = re.search(r'(\{[^{}]{0,250}(?:label|title|text)\s*:\s*["\']Semana["\'][^{}]{0,250}\})', source, re.I)
        if match:
            week = match.group(1)
            day = re.sub(r'(["\'])Semana\1', r'\1Dia\1', week, flags=re.I)
            day = re.sub(r'(["\'])week\1', r'\1day\1', day, flags=re.I)
            source = source[:match.start()] + day + ",\n" + source[match.start():]

        if source == old:
            source = re.sub(r'(\[\s*)(["\']Semana["\']\s*,)', r'\1"Dia", \2', source, count=1, flags=re.I)

        if source == old:
            source = re.sub(r'(\[\s*)(["\']week["\']\s*,)', r'\1"day", \2', source, count=1, flags=re.I)

        if source != old:
            backup(path, backup_root)
            write(path, source)
            touched.append(path)

    return touched


def patch_employee_button(page, backup_root):
    if not page:
        return False

    source = read(page)
    old = source

    pattern = r'(<button\b[^>]*)(>)(\s*(?:Cadastrar|Adicionar|Novo)\s+funcion[aá]rio\s*)(</button>)'

    def repl(match):
        opening = match.group(1)
        if "aria-label=" not in opening:
            opening += ' aria-label="Adicionar funcionário" title="Adicionar funcionário"'
        if "style=" not in opening:
            opening += ' style={{ backgroundColor: "#16a34a", color: "#fff", width: 44, height: 44, borderRadius: 12, border: 0, fontSize: 28, cursor: "pointer" }}'
        return opening + match.group(2) + "+" + match.group(4)

    source, count = re.subn(pattern, repl, source, count=1, flags=re.I)

    if count:
        backup(page, backup_root)
        write(page, source)
        return True

    return False


def restore():
    if not STATE.exists():
        fail("Não encontrei o arquivo de estado do último backup.")

    state = json.loads(read(STATE))
    backup_root = Path(state["backup"])

    if not backup_root.exists():
        fail(f"Backup não encontrado: {backup_root}")

    count = 0
    for source in backup_root.rglob("*"):
        if source.is_file():
            rel = source.relative_to(backup_root)
            target = ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1

    print(f"Restaurados {count} arquivo(s).")
    print("Reinicie com: npm run dev")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    if args.restore:
        restore()
        return

    if not (ROOT / "package.json").exists() or not APP.exists():
        fail("Execute o script na raiz do projeto, onde ficam package.json e app/.")

    if not SCHEMA.exists():
        fail("Não encontrei database/prisma/schema.prisma.")

    models, enums = parse_schema(read(SCHEMA))
    kinds = ("suppliers", "transactions", "payables", "employees", "inventory")
    detected = {kind: detect_model(models, kind) for kind in kinds}

    pages = {
        "dashboard": find_page("dashboard"),
        "suppliers": find_page("suppliers"),
        "transactions": find_page("transactions"),
        "payables": find_page("payables"),
        "employees": find_page("employees"),
        "inventory": find_page("inventory"),
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / f"backup_crud_{stamp}"
    backup_root.mkdir(exist_ok=True)

    print("\nMODELOS:")
    for kind, model in detected.items():
        print(f"  {kind:13} -> {model.name if model else 'não encontrado'}")

    print("\nPÁGINAS:")
    for kind, page in pages.items():
        print(f"  {kind:13} -> {page.relative_to(ROOT) if page else 'não encontrada'}")

    component = COMPONENTS / "CrudManager.tsx"
    backup(component, backup_root)
    write(component, CRUD_COMPONENT)

    replaced = []

    for kind in ("suppliers", "transactions", "payables", "inventory"):
        model = detected[kind]
        page = pages[kind]

        if not model or not page:
            print(f"AVISO: {kind} não foi substituído porque model/página não foi detectado.")
            continue

        fields = editable_fields(model, models, enums)
        if not fields:
            print(f"AVISO: {kind} não possui campos editáveis detectados.")
            continue

        api = detect_api(model, kind, page)
        backup(page, backup_root)
        write(page, page_source(kind, api, fields, columns(fields)))
        replaced.append(str(page.relative_to(ROOT)))
        print(f"OK: {kind} -> {page.relative_to(ROOT)} | API {api}")

    if patch_employee_button(pages["employees"], backup_root):
        print("OK: botão de Funcionários alterado para '+' verde.")
    else:
        print("AVISO: botão de Funcionários não foi alterado automaticamente; a página foi preservada.")

    dashboard_files = patch_dashboard(backup_root)
    if dashboard_files:
        print("OK: período Dia adicionado ao dashboard em:")
        for path in dashboard_files:
            print("   ", path.relative_to(ROOT))
    else:
        print("AVISO: configuração do período do dashboard não foi reconhecida; gráfico preservado.")

    date_count = patch_dates(backup_root)
    print(f"OK: datas pt-BR ajustadas em {date_count} arquivo(s).")

    write(STATE, json.dumps({
        "backup": str(backup_root),
        "createdAt": datetime.now().isoformat(),
        "replaced": replaced,
    }, indent=2, ensure_ascii=False))

    print("\n==============================================")
    print("PRONTO")
    print("Backup:", backup_root.name)
    print("Agora rode:")
    print("  npm run dev")
    print("\nPara desfazer:")
    print(f"  python {Path(__file__).name} --restore")
    print("\nDepois de testar:")
    print("  git add .")
    print('  git commit -m "melhora CRUD e datas"')
    print("  git push")
    print("==============================================\n")


if __name__ == "__main__":
    main()
