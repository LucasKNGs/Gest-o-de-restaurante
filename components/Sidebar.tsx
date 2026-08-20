import Link from "next/link";

const links = [
  ["Dashboard", "/dashboard"],
  ["Movimentações", "/transactions"],
  ["Categorias", "/categories"],
  ["Contas a pagar", "/payables"],
  ["Abertura/fechamento", "/cash"],
  ["Contas e caixas", "/accounts"],
  ["Fornecedores", "/suppliers"],
  ["Funcionários", "/employees"],
  ["Estoque", "/inventory"],
  ["Relatórios", "/reports"],
  ["Equipe", "/team"],
  ["Auditoria", "/audit"],
];

export default function Sidebar({ restaurantName }: { restaurantName: string }) {
  return (
    <aside className="sidebar">
      <div className="brand">Gestão Financeira<small>{restaurantName}</small></div>
      <nav className="nav">
        {links.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}
      </nav>
      <div className="sidebar-footer">V1 • controle operacional e financeiro</div>
    </aside>
  );
}
