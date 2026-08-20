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
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
    });
    const data = await res.json();
    setLoading(false);
    if (!res.ok) return setError(data.error || "Falha ao entrar");
    window.location.href = "/dashboard";
  }

  return (
    <form onSubmit={submit}>
      {error && <div className="notice error">{error}</div>}
      <div className="field"><label>E-mail</label><input name="email" type="email" required defaultValue="admin@restaurante.local" /></div>
      <div className="field"><label>Senha</label><input name="password" type="password" required defaultValue="admin123" /></div>
      <button className="btn primary" disabled={loading}>{loading ? "Entrando..." : "Entrar"}</button>
    </form>
  );
}
