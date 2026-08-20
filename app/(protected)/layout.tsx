import { redirect } from "next/navigation";
import { getRestaurantContext } from "@/backend/lib/context";
import Sidebar from "@/components/Sidebar";
import LogoutButton from "@/components/LogoutButton";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const ctx = await getRestaurantContext();
  if (!ctx) redirect("/login");
  return (
    <div className="shell">
      <Sidebar restaurantName={ctx.restaurant.name} />
      <div className="main">
        <header className="topbar">
          <div><strong>{ctx.restaurant.name}</strong> <span className="muted">• {ctx.membership.role}</span></div>
          <div className="actions"><span className="muted">{ctx.user.name}</span><LogoutButton /></div>
        </header>
        {children}
      </div>
    </div>
  );
}
