#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Adiciona painel de detecção de possíveis desvios/anomalias financeiras.
# Execute na raiz:
#   python adicionar-deteccao-desvios.py
# Desfazer:
#   python adicionar-deteccao-desvios.py --restore

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
APP = ROOT / "app"
COMPONENTS = ROOT / "components"
SCHEMA = ROOT / "database" / "prisma" / "schema.prisma"
STATE = ROOT / ".desvios_patch_state.json"


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

    @property
    def names(self) -> set[str]:
        return {f.name for f in self.fields}


def fail(msg: str):
    print(f"\nERRO: {msg}")
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


def parse_schema(text: str) -> dict[str, Model]:
    models: dict[str, Model] = {}

    for match in re.finditer(r"\bmodel\s+(\w+)\s*\{(.*?)\n\}", text, re.S):
        name, body = match.group(1), match.group(2)
        fields: list[Field] = []

        for raw in body.splitlines():
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("@@"):
                continue

            fm = re.match(r"^(\w+)\s+([A-Za-z_]\w*)(\?|\[\])?\s*(.*)$", line)
            if not fm:
                continue

            fname, ftype, suffix, attrs = fm.groups()
            fields.append(
                Field(
                    name=fname,
                    type_name=ftype,
                    optional=suffix == "?",
                    is_list=suffix == "[]",
                    attrs=attrs or "",
                )
            )

        models[name] = Model(name, fields)

    return models


def delegate(model_name: str) -> str:
    return model_name[0].lower() + model_name[1:]


def first_field(model: Model | None, candidates: tuple[str, ...]) -> str | None:
    if not model:
        return None

    by_lower = {name.lower(): name for name in model.names}

    for candidate in candidates:
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]

    return None


def score_model(model: Model, kind: str) -> int:
    n = model.name.lower()
    fields = {x.lower() for x in model.names}

    tokens = {
        "cash": ("cashsession", "cashregister", "cashclose", "caixa", "registersession"),
        "transaction": ("transaction", "financialtransaction", "movement", "moviment"),
        "audit": ("auditlog", "audit", "activitylog"),
        "payable": ("payable", "accountpayable", "bill", "contapagar"),
        "stock": ("stockmovement", "inventorymovement", "estoquemov", "stock"),
    }[kind]

    wanted = {
        "cash": {
            "expectedbalance", "expectedamount", "expectedcash",
            "countedbalance", "countedamount", "countedcash",
            "difference", "variance", "closedat",
        },
        "transaction": {
            "amount", "value", "type", "categoryid",
            "accountid", "paymentmethod", "occurredat",
        },
        "audit": {"action", "entity", "entitytype", "createdat", "userid"},
        "payable": {"amount", "duedate", "supplierid", "status"},
        "stock": {"quantity", "type", "unitcost", "cost", "createdat"},
    }[kind]

    score = 0

    for token in tokens:
        if n == token:
            score += 30
        elif token in n:
            score += 14

    score += len(fields & wanted) * 4
    return score


def detect_model(models: dict[str, Model], kind: str) -> Model | None:
    ranked = sorted(
        models.values(),
        key=lambda model: score_model(model, kind),
        reverse=True,
    )

    if not ranked or score_model(ranked[0], kind) <= 0:
        return None

    return ranked[0]


def build_source(model: Model | None, kind: str) -> dict:
    if not model:
        return {"enabled": False}

    date_field = first_field(
        model,
        (
            "occurredAt", "createdAt", "closedAt", "date",
            "transactionDate", "dueDate", "updatedAt",
        ),
    )

    config = {
        "enabled": True,
        "model": model.name,
        "delegate": delegate(model.name),
        "date": date_field,
        "restaurant": first_field(model, ("restaurantId",)),
    }

    if kind == "cash":
        config.update({
            "difference": first_field(
                model,
                ("difference", "variance", "cashDifference", "balanceDifference"),
            ),
            "expected": first_field(
                model,
                (
                    "expectedBalance", "expectedAmount", "expectedCash",
                    "expectedClosingBalance", "systemBalance",
                ),
            ),
            "counted": first_field(
                model,
                (
                    "countedBalance", "countedAmount", "countedCash",
                    "actualBalance", "closingBalance",
                ),
            ),
            "user": first_field(
                model,
                ("closedById", "userId", "createdById", "operatorId"),
            ),
        })

    elif kind == "transaction":
        config.update({
            "amount": first_field(model, ("amount", "value", "valor", "total")),
            "type": first_field(model, ("type", "transactionType", "kind")),
            "description": first_field(
                model,
                ("description", "descricao", "notes", "note", "memo"),
            ),
            "user": first_field(
                model,
                ("createdById", "userId", "employeeId", "operatorId"),
            ),
            "category": first_field(model, ("categoryId",)),
            "account": first_field(model, ("accountId",)),
            "payment": first_field(model, ("paymentMethod", "method")),
        })

    elif kind == "audit":
        config.update({
            "action": first_field(model, ("action", "event", "operation")),
            "entity": first_field(
                model,
                ("entity", "entityType", "resource", "model", "tableName"),
            ),
            "user": first_field(
                model,
                ("userId", "actorId", "createdById"),
            ),
        })

    elif kind == "payable":
        config.update({
            "amount": first_field(model, ("amount", "value", "valor", "total")),
            "supplier": first_field(model, ("supplierId",)),
            "status": first_field(model, ("status",)),
            "due": first_field(model, ("dueDate", "dueAt", "vencimento")),
        })

    elif kind == "stock":
        config.update({
            "quantity": first_field(
                model,
                ("quantity", "qty", "amount", "delta", "change"),
            ),
            "type": first_field(model, ("type", "movementType", "kind")),
            "cost": first_field(
                model,
                ("unitCost", "cost", "averageCost", "totalCost"),
            ),
            "user": first_field(
                model,
                ("createdById", "userId", "employeeId", "operatorId"),
            ),
        })

    return config


def create_fetch_block(config: dict, var_name: str) -> str:
    if not config.get("enabled"):
        return f"const {var_name}: AnyRow[] = [];"

    delegate_name = config["delegate"]
    conditions = []

    if config.get("restaurant"):
        conditions.append(f'{config["restaurant"]}: restaurantId')

    if config.get("date"):
        conditions.append(f'{config["date"]}: {{ gte: since }}')

    where = "{ " + ", ".join(conditions) + " }" if conditions else "{}"

    if config.get("date"):
        order_by = f'{{ {config["date"]}: "desc" }}'
    else:
        order_by = "undefined"

    return f'''const {var_name}: AnyRow[] = await (prisma.{delegate_name} as any).findMany({{
      where: {where},
      orderBy: {order_by},
      take: 2000,
    }});'''


API_TEMPLATE = r'''import { NextResponse } from "next/server";
import { prisma } from "@/backend/lib/prisma";
import { getRestaurantContext } from "@/backend/lib/context";

type AnyRow = Record<string, any>;

type Alert = {
  id: string;
  level: "CRITICO" | "ALTO" | "MEDIO" | "BAIXO";
  score: number;
  rule: string;
  title: string;
  description: string;
  amount: number;
  userId?: string | null;
  date?: string | null;
  entityId?: string | null;
};

const CONFIG = __CONFIG__;

function n(value: any) {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function text(value: any) {
  return value == null ? "" : String(value);
}

function upper(value: any) {
  return text(value).trim().toUpperCase();
}

function dateValue(value: any) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function iso(value: any) {
  const date = dateValue(value);
  return date ? date.toISOString() : null;
}

function median(values: number[]) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2) return sorted[middle];
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

function add(alerts: Alert[], input: Omit<Alert, "id">) {
  alerts.push({
    id: `${input.rule}-${input.entityId || "x"}-${alerts.length}`,
    ...input,
  });
}

function level(score: number): Alert["level"] {
  if (score >= 80) return "CRITICO";
  if (score >= 60) return "ALTO";
  if (score >= 35) return "MEDIO";
  return "BAIXO";
}

export async function GET() {
  try {
    const ctx = await getRestaurantContext();
    const restaurantId =
      (ctx as any).restaurantId ??
      (ctx as any).restaurant?.id ??
      (ctx as any).restaurant?.restaurantId;

    if (!restaurantId) {
      return NextResponse.json(
        { error: "Restaurante não identificado." },
        { status: 401 }
      );
    }

    const role =
      (ctx as any).role ??
      (ctx as any).membership?.role ??
      (ctx as any).user?.role;

    if (role !== "OPERATOR") {
      return NextResponse.json(
        { error: "Acesso restrito ao operador." },
        { status: 403 }
      );
    }

    const since = new Date();
    since.setDate(since.getDate() - 90);

    __FETCH_CASH__
    __FETCH_TRANSACTIONS__
    __FETCH_AUDIT__
    __FETCH_PAYABLES__
    __FETCH_STOCK__

    const alerts: Alert[] = [];

    // 1) Diferenças de caixa
    if (CONFIG.cash.enabled) {
      for (const row of cashRows) {
        const cfg = CONFIG.cash;
        let difference = cfg.difference ? n(row[cfg.difference]) : 0;

        if (!cfg.difference && cfg.expected && cfg.counted) {
          difference = n(row[cfg.counted]) - n(row[cfg.expected]);
        }

        const abs = Math.abs(difference);

        if (abs >= 20) {
          let score =
            abs >= 500 ? 95 :
            abs >= 200 ? 80 :
            abs >= 100 ? 65 :
            abs >= 50 ? 45 : 30;

          if (difference < 0) score += 5;
          score = Math.min(100, score);

          add(alerts, {
            level: level(score),
            score,
            rule: "DIFERENCA_CAIXA",
            title:
              difference < 0
                ? "Falta de dinheiro no fechamento"
                : "Sobra de dinheiro no fechamento",
            description:
              `Fechamento com diferença de ${difference.toLocaleString("pt-BR", {
                style: "currency",
                currency: "BRL",
              })}. Confira caixa, comprovantes e responsável pelo turno.`,
            amount: abs,
            userId: cfg.user ? text(row[cfg.user]) || null : null,
            date: cfg.date ? iso(row[cfg.date]) : null,
            entityId: text(row.id) || null,
          });
        }
      }

      const grouped = new Map<string, { count: number; amount: number }>();

      for (const row of cashRows) {
        const cfg = CONFIG.cash;
        if (!cfg.user) continue;

        let difference = cfg.difference ? n(row[cfg.difference]) : 0;

        if (!cfg.difference && cfg.expected && cfg.counted) {
          difference = n(row[cfg.counted]) - n(row[cfg.expected]);
        }

        if (difference >= -20) continue;

        const user = text(row[cfg.user]);
        if (!user) continue;

        const current = grouped.get(user) || { count: 0, amount: 0 };
        current.count += 1;
        current.amount += Math.abs(difference);
        grouped.set(user, current);
      }

      for (const [userId, data] of grouped) {
        if (data.count < 3) continue;

        const score = Math.min(100, 55 + data.count * 8);

        add(alerts, {
          level: level(score),
          score,
          rule: "RECORRENCIA_CAIXA",
          title: "Diferenças recorrentes no mesmo responsável",
          description:
            `${data.count} fechamentos com falta de caixa foram identificados nos últimos 90 dias. ` +
            `O padrão deve ser revisado antes de qualquer conclusão sobre a causa.`,
          amount: data.amount,
          userId,
          date: null,
          entityId: userId,
        });
      }
    }

    // 2) Movimentações fora do padrão
    if (CONFIG.transaction.enabled && CONFIG.transaction.amount) {
      const cfg = CONFIG.transaction;

      const expenseRows = transactionRows.filter((row) => {
        const amount = n(row[cfg.amount]);
        const type = cfg.type ? upper(row[cfg.type]) : "";

        return (
          amount < 0 ||
          type.includes("EXPENSE") ||
          type.includes("SAIDA") ||
          type.includes("SAÍDA") ||
          type.includes("OUT")
        );
      });

      const amounts = expenseRows
        .map((row) => Math.abs(n(row[cfg.amount])))
        .filter((value) => value > 0);

      const med = median(amounts);

      for (const row of expenseRows) {
        const amount = Math.abs(n(row[cfg.amount]));
        if (!amount) continue;

        const unusual =
          (med > 0 && amount >= med * 4 && amount >= 150) ||
          amount >= 1500;

        if (!unusual) continue;

        const ratio = med > 0 ? amount / med : 1;

        const score = Math.min(
          95,
          amount >= 5000 ? 90 :
          amount >= 2000 ? 78 :
          ratio >= 8 ? 75 :
          ratio >= 4 ? 60 : 45
        );

        add(alerts, {
          level: level(score),
          score,
          rule: "DESPESA_FORA_PADRAO",
          title: "Despesa muito acima do padrão",
          description:
            med > 0
              ? `Movimentação de ${amount.toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}, aproximadamente ${ratio.toFixed(1)}x a mediana das saídas recentes.`
              : `Movimentação de alto valor registrada: ${amount.toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}.`,
          amount,
          userId: cfg.user ? text(row[cfg.user]) || null : null,
          date: cfg.date ? iso(row[cfg.date]) : null,
          entityId: text(row.id) || null,
        });
      }

      const duplicateMap = new Map<string, AnyRow[]>();

      for (const row of expenseRows) {
        const amount = Math.abs(n(row[cfg.amount]));
        if (!amount) continue;

        const description = cfg.description
          ? upper(row[cfg.description]).replace(/\s+/g, " ").slice(0, 80)
          : "";

        const day =
          cfg.date && row[cfg.date]
            ? text(row[cfg.date]).slice(0, 10)
            : "sem-data";

        const category = cfg.category ? text(row[cfg.category]) : "";
        const key = `${amount.toFixed(2)}|${description}|${category}|${day}`;

        const list = duplicateMap.get(key) || [];
        list.push(row);
        duplicateMap.set(key, list);
      }

      for (const rows of duplicateMap.values()) {
        if (rows.length < 2) continue;

        const sample = rows[0];
        const amount = Math.abs(n(sample[cfg.amount]));
        const score = amount >= 1000 ? 80 : amount >= 300 ? 65 : 45;

        add(alerts, {
          level: level(score),
          score,
          rule: "POSSIVEL_DUPLICIDADE",
          title: "Possível lançamento duplicado",
          description:
            `${rows.length} saídas semelhantes foram registradas com o mesmo valor no mesmo dia. ` +
            `Confira nota, comprovante e fornecedor.`,
          amount: amount * rows.length,
          userId: cfg.user ? text(sample[cfg.user]) || null : null,
          date: cfg.date ? iso(sample[cfg.date]) : null,
          entityId: text(sample.id) || null,
        });
      }

      for (const row of expenseRows) {
        if (!cfg.date) continue;

        const date = dateValue(row[cfg.date]);
        if (!date) continue;

        const hour = date.getHours();
        const amount = Math.abs(n(row[cfg.amount]));

        if (hour >= 0 && hour < 5 && amount >= 100) {
          const score = amount >= 1000 ? 70 : 45;

          add(alerts, {
            level: level(score),
            score,
            rule: "HORARIO_INCOMUM",
            title: "Movimentação em horário incomum",
            description:
              `Saída registrada às ${String(hour).padStart(2, "0")}:${String(
                date.getMinutes()
              ).padStart(2, "0")}. O alerta serve para revisão.`,
            amount,
            userId: cfg.user ? text(row[cfg.user]) || null : null,
            date: date.toISOString(),
            entityId: text(row.id) || null,
          });
        }
      }
    }

    // 3) Alterações/exclusões sensíveis
    if (CONFIG.audit.enabled && CONFIG.audit.action) {
      const cfg = CONFIG.audit;

      for (const row of auditRows) {
        const action = upper(row[cfg.action]);
        const entity = cfg.entity ? upper(row[cfg.entity]) : "";

        const sensitiveEntity =
          !entity ||
          entity.includes("TRANSACTION") ||
          entity.includes("MOVIMENT") ||
          entity.includes("PAYABLE") ||
          entity.includes("CONTA") ||
          entity.includes("CASH") ||
          entity.includes("CAIXA") ||
          entity.includes("STOCK") ||
          entity.includes("ESTOQUE");

        if (!sensitiveEntity) continue;

        const deleted =
          action.includes("DELETE") ||
          action.includes("EXCL") ||
          action.includes("REMOVE");

        const edited =
          action.includes("UPDATE") ||
          action.includes("EDIT") ||
          action.includes("ALTER");

        if (!deleted && !edited) continue;

        const score = deleted ? 70 : 38;

        add(alerts, {
          level: level(score),
          score,
          rule: deleted ? "EXCLUSAO_SENSIVEL" : "ALTERACAO_SENSIVEL",
          title:
            deleted
              ? "Exclusão de registro financeiro/operacional"
              : "Alteração em registro financeiro/operacional",
          description:
            `${action || "Ação"} em ${entity || "registro sensível"}. ` +
            `Revise o histórico da auditoria e o motivo da alteração.`,
          amount: 0,
          userId: cfg.user ? text(row[cfg.user]) || null : null,
          date: cfg.date ? iso(row[cfg.date]) : null,
          entityId: text(row.id) || null,
        });
      }
    }

    // 4) Contas a pagar duplicadas
    if (
      CONFIG.payable.enabled &&
      CONFIG.payable.amount &&
      CONFIG.payable.supplier
    ) {
      const cfg = CONFIG.payable;
      const groups = new Map<string, AnyRow[]>();

      for (const row of payableRows) {
        const amount = Math.abs(n(row[cfg.amount]));
        const supplier = text(row[cfg.supplier]);

        if (!amount || !supplier) continue;

        const due =
          cfg.due && row[cfg.due]
            ? text(row[cfg.due]).slice(0, 10)
            : "sem-vencimento";

        const key = `${supplier}|${amount.toFixed(2)}|${due}`;

        const current = groups.get(key) || [];
        current.push(row);
        groups.set(key, current);
      }

      for (const rows of groups.values()) {
        if (rows.length < 2) continue;

        const sample = rows[0];
        const amount = Math.abs(n(sample[cfg.amount]));
        const score = amount >= 1000 ? 85 : amount >= 300 ? 65 : 50;

        add(alerts, {
          level: level(score),
          score,
          rule: "CONTA_PAGAR_DUPLICADA",
          title: "Possível conta a pagar duplicada",
          description:
            `${rows.length} contas possuem mesmo fornecedor, valor e vencimento. ` +
            `Confira documentos antes do pagamento.`,
          amount: amount * rows.length,
          userId: null,
          date: cfg.due ? iso(sample[cfg.due]) : null,
          entityId: text(sample.id) || null,
        });
      }
    }

    // 5) Ajustes/saídas de estoque
    if (CONFIG.stock.enabled && CONFIG.stock.quantity) {
      const cfg = CONFIG.stock;

      for (const row of stockRows) {
        const qty = n(row[cfg.quantity]);
        const movementType = cfg.type ? upper(row[cfg.type]) : "";

        const negative =
          qty < 0 ||
          movementType.includes("OUT") ||
          movementType.includes("SAIDA") ||
          movementType.includes("SAÍDA") ||
          movementType.includes("LOSS") ||
          movementType.includes("PERDA");

        const adjustment =
          movementType.includes("ADJUST") ||
          movementType.includes("AJUST");

        if (!negative || (!adjustment && Math.abs(qty) < 5)) continue;

        const unitCost = cfg.cost ? Math.abs(n(row[cfg.cost])) : 0;
        const estimated = unitCost > 0 ? Math.abs(qty) * unitCost : 0;
        const score = estimated >= 500 ? 65 : estimated >= 150 ? 48 : 30;

        add(alerts, {
          level: level(score),
          score,
          rule: "AJUSTE_ESTOQUE_NEGATIVO",
          title: "Saída/ajuste de estoque para revisão",
          description:
            `Movimentação negativa de estoque (${qty}). Compare com perdas justificadas, compras e inventário físico.`,
          amount: estimated,
          userId: cfg.user ? text(row[cfg.user]) || null : null,
          date: cfg.date ? iso(row[cfg.date]) : null,
          entityId: text(row.id) || null,
        });
      }
    }

    alerts.sort((a, b) => b.score - a.score || b.amount - a.amount);

    const topAlerts = alerts.slice(0, 120);
    const critical = topAlerts.filter((item) => item.level === "CRITICO").length;
    const high = topAlerts.filter((item) => item.level === "ALTO").length;
    const medium = topAlerts.filter((item) => item.level === "MEDIO").length;

    const amountAtRisk = topAlerts.reduce(
      (sum, item) => sum + Math.max(0, item.amount || 0),
      0
    );

    const weighted =
      critical * 20 +
      high * 10 +
      medium * 4 +
      Math.min(30, amountAtRisk / 500);

    const overallRisk = Math.min(100, Math.round(weighted));

    return NextResponse.json({
      generatedAt: new Date().toISOString(),
      periodDays: 90,
      overallRisk,
      summary: {
        totalAlerts: topAlerts.length,
        critical,
        high,
        medium,
        amountAtRisk,
      },
      alerts: topAlerts,
      sources: {
        cash: CONFIG.cash.enabled,
        transactions: CONFIG.transaction.enabled,
        audit: CONFIG.audit.enabled,
        payables: CONFIG.payable.enabled,
        stock: CONFIG.stock.enabled,
      },
      disclaimer:
        "Os alertas indicam anomalias para revisão. Não constituem prova de fraude ou desvio.",
    });
  } catch (error) {
    console.error("Erro ao analisar possíveis desvios:", error);

    return NextResponse.json(
      {
        error: "Não foi possível analisar os dados do restaurante.",
        details:
          process.env.NODE_ENV === "development"
            ? String(error)
            : undefined,
      },
      { status: 500 }
    );
  }
}
'''


PAGE_SOURCE = r'''"use client";

import { useEffect, useMemo, useState } from "react";

type AlertItem = {
  id: string;
  level: "CRITICO" | "ALTO" | "MEDIO" | "BAIXO";
  score: number;
  rule: string;
  title: string;
  description: string;
  amount: number;
  userId?: string | null;
  date?: string | null;
};

type ApiData = {
  generatedAt: string;
  periodDays: number;
  overallRisk: number;
  summary: {
    totalAlerts: number;
    critical: number;
    high: number;
    medium: number;
    amountAtRisk: number;
  };
  alerts: AlertItem[];
  sources: Record<string, boolean>;
  disclaimer: string;
};

function money(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value || 0));
}

function dateBR(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function levelText(level: AlertItem["level"]) {
  return {
    CRITICO: "Crítico",
    ALTO: "Alto",
    MEDIO: "Médio",
    BAIXO: "Baixo",
  }[level];
}

export default function DesviosClient() {
  const [data, setData] = useState<ApiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [level, setLevel] = useState("TODOS");
  const [query, setQuery] = useState("");

  async function load() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/desvios", {
        cache: "no-store",
        credentials: "include",
      });

      const body = await response.json();

      if (!response.ok) {
        throw new Error(body?.error || "Erro ao carregar análise.");
      }

      setData(body);
    } catch (e: any) {
      setError(e?.message || "Erro ao carregar análise.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];

    const q = query.trim().toLocaleLowerCase("pt-BR");

    return data.alerts.filter((item) => {
      const levelOk = level === "TODOS" || item.level === level;

      const queryOk =
        !q ||
        item.title.toLocaleLowerCase("pt-BR").includes(q) ||
        item.description.toLocaleLowerCase("pt-BR").includes(q) ||
        String(item.userId || "").toLocaleLowerCase("pt-BR").includes(q);

      return levelOk && queryOk;
    });
  }, [data, level, query]);

  const riskClass =
    !data ? "low" :
    data.overallRisk >= 75 ? "critical" :
    data.overallRisk >= 50 ? "high" :
    data.overallRisk >= 25 ? "medium" : "low";

  return (
    <section className="deviation-page">
      <header className="deviation-header">
        <div>
          <h1>Detecção de desvios</h1>
          <p>
            Análise de diferenças de caixa, movimentações incomuns,
            duplicidades, auditoria e ajustes de estoque.
          </p>
        </div>

        <button type="button" onClick={load} disabled={loading}>
          {loading ? "Analisando..." : "Atualizar análise"}
        </button>
      </header>

      <div className="deviation-warning">
        <strong>Importante:</strong> um alerta não significa que houve roubo.
        Ele indica uma situação que merece conferência de comprovantes,
        fechamento de caixa, fornecedor e responsável.
      </div>

      {error ? <div className="deviation-error">{error}</div> : null}

      {data ? (
        <>
          <div className="risk-grid">
            <article className={`risk-card score ${riskClass}`}>
              <span>Risco geral</span>
              <strong>{data.overallRisk}/100</strong>
              <small>Últimos {data.periodDays} dias</small>
            </article>

            <article className="risk-card">
              <span>Alertas críticos</span>
              <strong>{data.summary.critical}</strong>
              <small>{data.summary.high} de risco alto</small>
            </article>

            <article className="risk-card">
              <span>Valor sob atenção</span>
              <strong>{money(data.summary.amountAtRisk)}</strong>
              <small>Não representa perda confirmada</small>
            </article>

            <article className="risk-card">
              <span>Total de alertas</span>
              <strong>{data.summary.totalAlerts}</strong>
              <small>Análise automática</small>
            </article>
          </div>

          <div className="source-strip">
            <span>Fontes analisadas:</span>
            <b className={data.sources.cash ? "on" : "off"}>Caixa</b>
            <b className={data.sources.transactions ? "on" : "off"}>Movimentações</b>
            <b className={data.sources.audit ? "on" : "off"}>Auditoria</b>
            <b className={data.sources.payables ? "on" : "off"}>Contas a pagar</b>
            <b className={data.sources.stock ? "on" : "off"}>Estoque</b>
          </div>

          <div className="deviation-toolbar">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Pesquisar alerta ou responsável..."
            />

            <select value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="TODOS">Todos os níveis</option>
              <option value="CRITICO">Crítico</option>
              <option value="ALTO">Alto</option>
              <option value="MEDIO">Médio</option>
              <option value="BAIXO">Baixo</option>
            </select>
          </div>

          <div className="alert-list">
            {filtered.length === 0 ? (
              <div className="empty-alerts">
                Nenhum alerta encontrado com os filtros atuais.
              </div>
            ) : (
              filtered.map((item) => (
                <article className="alert-card" key={item.id}>
                  <div className="alert-top">
                    <div>
                      <span className={`badge ${item.level.toLowerCase()}`}>
                        {levelText(item.level)}
                      </span>
                      <span className="rule">
                        {item.rule.replaceAll("_", " ")}
                      </span>
                    </div>

                    <strong className="alert-score">{item.score}/100</strong>
                  </div>

                  <h3>{item.title}</h3>
                  <p>{item.description}</p>

                  <div className="alert-meta">
                    {item.amount > 0 ? (
                      <span>
                        Valor relacionado: <b>{money(item.amount)}</b>
                      </span>
                    ) : null}

                    <span>
                      Data: <b>{dateBR(item.date)}</b>
                    </span>

                    {item.userId ? (
                      <span>
                        Responsável/usuário: <b>{item.userId}</b>
                      </span>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>
        </>
      ) : loading ? (
        <div className="loading-analysis">
          Analisando informações financeiras...
        </div>
      ) : null}

      <style jsx global>{`
        .deviation-page { width:100%; }
        .deviation-header { display:flex; align-items:center; justify-content:space-between; gap:18px; margin-bottom:18px; }
        .deviation-header h1 { margin:0; color:#111827; font-size:30px; }
        .deviation-header p { margin:6px 0 0; color:#64748b; max-width:760px; }
        .deviation-header button { border:0; border-radius:10px; padding:11px 15px; cursor:pointer; background:#111827; color:#fff; font-weight:700; white-space:nowrap; }
        .deviation-warning { padding:13px 15px; margin-bottom:18px; border-radius:12px; background:#fffbeb; border:1px solid #fde68a; color:#92400e; }
        .deviation-error { padding:13px 15px; border-radius:12px; background:#fef2f2; border:1px solid #fecaca; color:#b91c1c; margin-bottom:18px; }
        .risk-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:18px; }
        .risk-card { display:flex; flex-direction:column; min-height:116px; padding:17px; background:#fff; border:1px solid #e2e8f0; border-radius:14px; }
        .risk-card span { color:#64748b; font-size:13px; }
        .risk-card strong { margin-top:8px; color:#0f172a; font-size:28px; }
        .risk-card small { margin-top:auto; color:#94a3b8; }
        .risk-card.score.critical { border-color:#ef4444; background:#fef2f2; }
        .risk-card.score.high { border-color:#f97316; background:#fff7ed; }
        .risk-card.score.medium { border-color:#eab308; background:#fefce8; }
        .risk-card.score.low { border-color:#22c55e; background:#f0fdf4; }
        .source-strip { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:16px; color:#64748b; font-size:13px; }
        .source-strip b { border-radius:999px; padding:5px 9px; font-size:12px; }
        .source-strip .on { background:#dcfce7; color:#166534; }
        .source-strip .off { background:#f1f5f9; color:#94a3b8; }
        .deviation-toolbar { display:flex; gap:10px; margin-bottom:14px; }
        .deviation-toolbar input, .deviation-toolbar select { border:1px solid #dbe1ea; border-radius:10px; background:#fff; padding:10px 12px; }
        .deviation-toolbar input { flex:1; max-width:460px; }
        .alert-list { display:grid; gap:11px; }
        .alert-card { padding:16px 17px; border:1px solid #e2e8f0; border-radius:13px; background:#fff; }
        .alert-top { display:flex; justify-content:space-between; align-items:center; gap:10px; }
        .badge { display:inline-flex; align-items:center; border-radius:999px; padding:4px 8px; font-size:11px; font-weight:800; text-transform:uppercase; }
        .badge.critico { color:#991b1b; background:#fee2e2; }
        .badge.alto { color:#9a3412; background:#ffedd5; }
        .badge.medio { color:#854d0e; background:#fef9c3; }
        .badge.baixo { color:#166534; background:#dcfce7; }
        .rule { margin-left:8px; color:#94a3b8; font-size:11px; }
        .alert-score { color:#475569; }
        .alert-card h3 { margin:11px 0 6px; color:#111827; font-size:17px; }
        .alert-card p { margin:0; color:#475569; line-height:1.55; }
        .alert-meta { display:flex; flex-wrap:wrap; gap:14px; padding-top:12px; margin-top:12px; border-top:1px solid #f1f5f9; color:#64748b; font-size:12px; }
        .alert-meta b { color:#334155; }
        .empty-alerts, .loading-analysis { padding:32px; text-align:center; color:#64748b; border:1px solid #e2e8f0; border-radius:13px; background:#fff; }
        @media (max-width:900px) { .risk-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
        @media (max-width:640px) {
          .deviation-header { align-items:stretch; flex-direction:column; }
          .deviation-header button { align-self:flex-start; }
          .risk-grid { grid-template-columns:1fr; }
          .deviation-toolbar { flex-direction:column; }
          .deviation-toolbar input { max-width:none; }
        }
      `}</style>
    </section>
  );
}
'''



SERVER_PAGE_SOURCE = r'''import { redirect } from "next/navigation";
import { getRestaurantContext } from "@/backend/lib/context";
import DesviosClient from "./DesviosClient";

export default async function DesviosPage() {
  const ctx = await getRestaurantContext();

  const role =
    (ctx as any).role ??
    (ctx as any).membership?.role ??
    (ctx as any).user?.role;

  if (role !== "OPERATOR") {
    redirect("/dashboard");
  }

  return <DesviosClient />;
}
'''


ACCESS_API_SOURCE = r'''import { NextResponse } from "next/server";
import { getRestaurantContext } from "@/backend/lib/context";

export async function GET() {
  try {
    const ctx = await getRestaurantContext();

    const role =
      (ctx as any).role ??
      (ctx as any).membership?.role ??
      (ctx as any).user?.role;

    return NextResponse.json({
      allowed: role === "OPERATOR",
    });
  } catch {
    return NextResponse.json(
      { allowed: false },
      { status: 401 }
    );
  }
}
'''


NAV_SOURCE = r'''"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function OperatorDesviosNav() {
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let active = true;

    fetch("/api/desvios/access", {
      cache: "no-store",
      credentials: "include",
    })
      .then(async (response) => {
        if (!response.ok) return { allowed: false };
        return response.json();
      })
      .then((data) => {
        if (active) setAllowed(Boolean(data?.allowed));
      })
      .catch(() => {
        if (active) setAllowed(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (!allowed) return null;

  return (
    <Link
      href="/desvios"
      className="operator-desvios-link"
      style={{
        display: "block",
        padding: "10px 12px",
        borderRadius: "8px",
        textDecoration: "none",
        color: "inherit",
      }}
    >
      Desvios
    </Link>
  );
}
'''


def sidebar_candidates() -> list[Path]:
    result = []

    for base in (COMPONENTS, APP):
        if not base.exists():
            continue

        for path in base.rglob("*.tsx"):
            try:
                source = read(path)
            except Exception:
                continue

            low = source.lower()

            if (
                "dashboard" in low
                and (
                    "movimenta" in low
                    or "fornecedor" in low
                    or "estoque" in low
                    or "funcion" in low
                )
            ):
                result.append(path)

    return result


def patch_sidebar(backup_root: Path) -> Path | None:
    for path in sidebar_candidates():
        source = read(path)
        old = source

        if "OperatorDesviosNav" in source:
            return path

        lines = source.splitlines()
        import_line = 'import OperatorDesviosNav from "@/components/OperatorDesviosNav";'

        insert_index = 0

        if lines and lines[0].strip() in {'"use client";', "'use client';"}:
            insert_index = 1

        last_import = None
        for i, line in enumerate(lines):
            if line.lstrip().startswith("import "):
                last_import = i

        if last_import is not None:
            insert_index = last_import + 1

        lines.insert(insert_index, import_line)
        source = "\n".join(lines)

        nav_close = source.lower().find("</nav>")

        if nav_close != -1:
            source = (
                source[:nav_close]
                + "\n        <OperatorDesviosNav />\n"
                + source[nav_close:]
            )
        else:
            aside_close = source.lower().find("</aside>")

            if aside_close != -1:
                source = (
                    source[:aside_close]
                    + "\n        <OperatorDesviosNav />\n"
                    + source[aside_close:]
                )
            else:
                continue

        if source != old:
            backup(path, backup_root)
            write(path, source)
            return path

    return None

def restore():
    if not STATE.exists():
        fail("Não encontrei informações do último backup.")

    state = json.loads(read(STATE))
    backup_root = Path(state["backup"])

    if not backup_root.exists():
        fail(f"Backup não encontrado: {backup_root}")

    restored = 0

    for source in backup_root.rglob("*"):
        if not source.is_file():
            continue

        rel = source.relative_to(backup_root)
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored += 1

    for raw in state.get("created", []):
        path = ROOT / raw
        if path.exists() and not (backup_root / raw).exists():
            path.unlink()

    print(f"Restaurados {restored} arquivo(s).")
    print("Reinicie o sistema com: npm run restaurante")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    if args.restore:
        restore()
        return

    if not (ROOT / "package.json").exists() or not APP.exists():
        fail("Execute este script na raiz do projeto.")

    if not SCHEMA.exists():
        fail("Não encontrei database/prisma/schema.prisma.")

    models = parse_schema(read(SCHEMA))

    detected = {
        "cash": detect_model(models, "cash"),
        "transaction": detect_model(models, "transaction"),
        "audit": detect_model(models, "audit"),
        "payable": detect_model(models, "payable"),
        "stock": detect_model(models, "stock"),
    }

    config = {
        kind: build_source(model, kind)
        for kind, model in detected.items()
    }

    print("\n=== FONTES DETECTADAS ===")

    for kind, model in detected.items():
        print(f"{kind:12} -> {model.name if model else 'não encontrada'}")

    if not any(item.get("enabled") for item in config.values()):
        fail("Nenhum modelo financeiro/operacional relevante foi detectado.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / f"backup_desvios_{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)

    api_path = APP / "api" / "desvios" / "route.ts"
    access_api_path = APP / "api" / "desvios" / "access" / "route.ts"
    page_path = APP / "(protected)" / "desvios" / "page.tsx"
    client_path = APP / "(protected)" / "desvios" / "DesviosClient.tsx"
    nav_path = COMPONENTS / "OperatorDesviosNav.tsx"

    created = []

    for path in (api_path, access_api_path, page_path, client_path, nav_path):
        if path.exists():
            backup(path, backup_root)
        else:
            created.append(str(path.relative_to(ROOT)))

    fetch_blocks = {
        "cash": create_fetch_block(config["cash"], "cashRows"),
        "transaction": create_fetch_block(config["transaction"], "transactionRows"),
        "audit": create_fetch_block(config["audit"], "auditRows"),
        "payable": create_fetch_block(config["payable"], "payableRows"),
        "stock": create_fetch_block(config["stock"], "stockRows"),
    }

    api_source = API_TEMPLATE
    api_source = api_source.replace(
        "__CONFIG__",
        json.dumps(config, ensure_ascii=False, indent=2),
    )
    api_source = api_source.replace("__FETCH_CASH__", fetch_blocks["cash"])
    api_source = api_source.replace("__FETCH_TRANSACTIONS__", fetch_blocks["transaction"])
    api_source = api_source.replace("__FETCH_AUDIT__", fetch_blocks["audit"])
    api_source = api_source.replace("__FETCH_PAYABLES__", fetch_blocks["payable"])
    api_source = api_source.replace("__FETCH_STOCK__", fetch_blocks["stock"])

    write(api_path, api_source)
    write(access_api_path, ACCESS_API_SOURCE)
    write(page_path, SERVER_PAGE_SOURCE)
    write(client_path, PAGE_SOURCE)
    write(nav_path, NAV_SOURCE)

    sidebar = patch_sidebar(backup_root)

    write(
        STATE,
        json.dumps(
            {
                "backup": str(backup_root),
                "created": created,
                "sidebar": str(sidebar.relative_to(ROOT)) if sidebar else None,
                "createdAt": datetime.now().isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    print("\n==============================================")
    print("SISTEMA DE DETECÇÃO DE DESVIOS ADICIONADO")
    print("==============================================")
    print("Página: /desvios")
    print("API:    /api/desvios")
    print("Acesso: SOMENTE papel OPERATOR")
    print(f"Backup: {backup_root.name}")

    if sidebar:
        print(f"Menu atualizado em: {sidebar.relative_to(ROOT)}")
    else:
        print("AVISO: não consegui adicionar o link ao menu automaticamente.")
        print("A página continua acessível em /desvios somente para OPERATOR.")

    print("\nO painel analisa:")
    print(" - diferenças de caixa")
    print(" - recorrência de falta por responsável")
    print(" - despesas muito acima do padrão")
    print(" - lançamentos possivelmente duplicados")
    print(" - movimentações em horários incomuns")
    print(" - alterações/exclusões sensíveis da auditoria")
    print(" - contas a pagar possivelmente duplicadas")
    print(" - ajustes/saídas incomuns de estoque")
    print("\nAgora rode:")
    print("  npm run restaurante")
    print("\nSe o servidor já estiver aberto:")
    print("  Ctrl+C")
    print("  npm run restaurante")
    print("\nPara desfazer:")
    print("  python adicionar-deteccao-desvios.py --restore")
    print("==============================================\n")


if __name__ == "__main__":
    main()
