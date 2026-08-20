"use client";
export default function LogoutButton() {
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }
  return <button className="btn small" onClick={logout}>Sair</button>;
}
