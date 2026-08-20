import { redirect } from "next/navigation";
import { getRestaurantContext } from "@/backend/lib/context";
import LoginForm from "./LoginForm";

export default async function LoginPage() {
  const ctx = await getRestaurantContext();
  if (ctx) redirect("/dashboard");
  return (
    <main className="login-shell">
      <section className="login-card">
        <h1>Gestão do Restaurante</h1>
        <p className="muted">Entre para acessar o financeiro, fornecedores, contas a pagar, equipe e estoque.</p>
        <LoginForm />
        <p className="muted" style={{ fontSize: 12, marginTop: 18 }}>
          Ambiente inicial: admin@restaurante.local / admin123
        </p>
      </section>
    </main>
  );
}
