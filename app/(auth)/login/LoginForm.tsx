"use client";

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
