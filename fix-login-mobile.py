from pathlib import Path

login_form = Path("app/(auth)/login/LoginForm.tsx")
login_route = Path("app/api/auth/login/route.ts")

login_form.write_text('''"use client";

import { FormEvent, useState } from "react";

export default function LoginForm() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const form = new FormData(e.currentTarget);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });

      const raw = await res.text();
      let data: { ok?: boolean; error?: string } = {};

      if (raw) {
        try {
          data = JSON.parse(raw);
        } catch {
          data = {};
        }
      }

      if (!res.ok) {
        setError(data.error || `Falha ao entrar (HTTP ${res.status})`);
        return;
      }

      if (!data.ok) {
        setError("O servidor respondeu de forma inesperada.");
        return;
      }

      window.location.href = "/dashboard";
    } catch (err) {
      console.error("Erro no login:", err);
      setError("Não foi possível conectar ao servidor. Verifique se o sistema e o banco estão ligados.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {error && <div className="notice error">{error}</div>}
      <div className="field">
        <label>E-mail</label>
        <input
          name="email"
          type="email"
          required
          defaultValue="admin@restaurante.local"
        />
      </div>
      <div className="field">
        <label>Senha</label>
        <input
          name="password"
          type="password"
          required
          defaultValue="admin123"
        />
      </div>
      <button className="btn primary" disabled={loading}>
        {loading ? "Entrando..." : "Entrar"}
      </button>
    </form>
  );
}
''', encoding="utf-8")

login_route.write_text('''import { NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/backend/lib/prisma";
import { verifyPassword } from "@/backend/lib/security";
import { createSession } from "@/backend/lib/session";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export async function POST(request: Request) {
  try {
    const parsed = schema.safeParse(await request.json().catch(() => null));

    if (!parsed.success) {
      return NextResponse.json({ error: "Dados inválidos" }, { status: 400 });
    }

    const user = await prisma.user.findUnique({
      where: { email: parsed.data.email.toLowerCase().trim() },
    });

    if (!user || !(await verifyPassword(parsed.data.password, user.passwordHash))) {
      return NextResponse.json(
        { error: "E-mail ou senha inválidos" },
        { status: 401 }
      );
    }

    await createSession(user.id);

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[LOGIN_ERROR]", error);

    return NextResponse.json(
      { error: "Erro interno ao fazer login. Verifique o banco de dados e tente novamente." },
      { status: 500 }
    );
  }
}
''', encoding="utf-8")

print("Correção aplicada em:")
print(" -", login_form)
print(" -", login_route)
print()
print("Agora rode: npm run dev")
