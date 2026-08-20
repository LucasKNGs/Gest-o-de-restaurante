"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type Employee = {
  id: string;
  name: string;
  roleName?: string | null;
  document?: string | null;
  monthlySalary?: number | null;
  status: "ACTIVE" | "INACTIVE";
  hiredAt?: string | null;
};

type Payroll = {
  id: string;
  referenceMonth: string;
  grossAmount: number;
  deductions: number;
  netAmount: number;
  dueDate: string;
  status: "PENDING" | "PAID" | "CANCELED";
  employee: Employee;
};

type Tab = "employees" | "payroll";

const paymentOptions = [
  { value: "CASH", label: "Dinheiro" },
  { value: "PIX", label: "Pix" },
  { value: "DEBIT_CARD", label: "Cartão de débito" },
  { value: "CREDIT_CARD", label: "Cartão de crédito" },
  { value: "BANK_TRANSFER", label: "Transferência bancária" },
  { value: "BOLETO", label: "Boleto" },
  { value: "OTHER", label: "Outro" },
];

function brl(value?: number | null) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function payrollStatus(status: string) {
  return (
    {
      PENDING: "Pendente",
      PAID: "Pago",
      CANCELED: "Cancelado",
    }[status] || status
  );
}

export default function EmployeesClient() {
  const [tab, setTab] = useState<Tab>("employees");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [payroll, setPayroll] = useState<Payroll[]>([]);
  const [accounts, setAccounts] = useState<{ id: string; name: string }[]>([]);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [employeesRes, payrollRes, refsRes] = await Promise.all([
      fetch("/api/employees"),
      fetch("/api/payroll"),
      fetch("/api/reference"),
    ]);

    if (employeesRes.ok) setEmployees(await employeesRes.json());
    if (payrollRes.ok) setPayroll(await payrollRes.json());
    if (refsRes.ok) setAccounts((await refsRes.json()).accounts);
  }

  useEffect(() => {
    load();
  }, []);

  const activeEmployees = useMemo(
    () => employees.filter((employee) => employee.status === "ACTIVE"),
    [employees]
  );

  async function saveEmployee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const form = event.currentTarget;
    const data = new FormData(form);
    const body = {
      name: data.get("name"),
      roleName: data.get("roleName") || null,
      document: data.get("document") || null,
      monthlySalary: data.get("monthlySalary") || null,
      hiredAt: data.get("hiredAt") ? `${data.get("hiredAt")}T12:00:00` : null,
    };

    const url = editing ? `/api/employees/${editing.id}` : "/api/employees";
    const method = editing ? "PATCH" : "POST";

    const response = await fetch(url, {
      method,
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível salvar o funcionário.");
      return;
    }

    setMessage(editing ? "Funcionário atualizado." : "Funcionário cadastrado.");
    setEditing(null);
    form.reset();
    await load();
  }

  async function changeStatus(employee: Employee) {
    setError("");
    setMessage("");
    const nextStatus = employee.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";

    const response = await fetch(`/api/employees/${employee.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível alterar o status.");
      return;
    }

    setMessage(nextStatus === "ACTIVE" ? "Funcionário reativado." : "Funcionário desativado.");
    if (editing?.id === employee.id) setEditing(null);
    await load();
  }

  async function removeEmployee(employee: Employee) {
    setError("");
    setMessage("");

    if (!confirm(`Excluir definitivamente o funcionário ${employee.name}?`)) return;

    const response = await fetch(`/api/employees/${employee.id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível excluir o funcionário.");
      return;
    }

    setMessage("Funcionário excluído.");
    if (editing?.id === employee.id) setEditing(null);
    await load();
  }

  async function addPayroll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const form = event.currentTarget;
    const data = new FormData(form);

    const response = await fetch("/api/payroll", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        employeeId: data.get("employeeId"),
        referenceMonth: data.get("referenceMonth"),
        grossAmount: data.get("grossAmount"),
        deductions: data.get("deductions") || 0,
        dueDate: `${data.get("dueDate")}T12:00:00`,
        notes: data.get("notes") || null,
      }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível gerar a folha.");
      return;
    }

    setMessage("Folha gerada com sucesso.");
    form.reset();
    await load();
  }

  async function payPayroll(id: string) {
    const accountList = accounts.map((account, index) => `${index + 1}. ${account.name}`).join("\n");
    const accountChoice = prompt(`Escolha a conta pelo número:\n${accountList}`, "1");
    if (accountChoice == null) return;

    const account = accounts[Number(accountChoice) - 1];
    if (!account) {
      alert("Conta inválida.");
      return;
    }

    const methodList = paymentOptions.map((item, index) => `${index + 1}. ${item.label}`).join("\n");
    const methodChoice = prompt(`Escolha a forma de pagamento:\n${methodList}`, "2");
    if (methodChoice == null) return;

    const method = paymentOptions[Number(methodChoice) - 1];
    if (!method) {
      alert("Forma de pagamento inválida.");
      return;
    }

    const response = await fetch(`/api/payroll/${id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        paymentMethod: method.value,
        accountId: account.id,
      }),
    });

    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      setError(result.error || "Não foi possível pagar a folha.");
      return;
    }

    setMessage("Folha paga e saída financeira registrada.");
    await load();
  }

  return (
    <main className="content">
      <h1 className="page-title">Funcionários</h1>
      <p className="page-subtitle">
        Cadastre a equipe e mantenha a geração de folhas em uma área separada.
      </p>

      <div
        className="card"
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          padding: 10,
          marginBottom: 16,
        }}
        role="tablist"
        aria-label="Seções de funcionários"
      >
        <button
          type="button"
          className={`btn ${tab === "employees" ? "primary" : ""}`}
          onClick={() => setTab("employees")}
          role="tab"
          aria-selected={tab === "employees"}
        >
          Cadastro de funcionários
        </button>
        <button
          type="button"
          className={`btn ${tab === "payroll" ? "primary" : ""}`}
          onClick={() => setTab("payroll")}
          role="tab"
          aria-selected={tab === "payroll"}
        >
          Folhas de pagamento
        </button>
      </div>

      {message && <div className="notice" style={{ marginBottom: 16 }}>{message}</div>}
      {error && <div className="notice error" style={{ marginBottom: 16 }}>{error}</div>}

      {tab === "employees" && (
        <>
          <div className="card">
            <h2 className="section-title">
              {editing ? `Editar ${editing.name}` : "Cadastrar funcionário"}
            </h2>

            <form
              className="form-grid"
              onSubmit={saveEmployee}
              key={editing?.id || "new-employee"}
            >
              <div className="field span-2">
                <label>Nome</label>
                <input name="name" required defaultValue={editing?.name || ""} />
              </div>

              <div className="field">
                <label>Cargo</label>
                <input name="roleName" defaultValue={editing?.roleName || ""} />
              </div>

              <div className="field">
                <label>CPF / Documento</label>
                <input name="document" defaultValue={editing?.document || ""} />
              </div>

              <div className="field">
                <label>Salário mensal</label>
                <input
                  name="monthlySalary"
                  type="number"
                  step="0.01"
                  min="0"
                  defaultValue={editing?.monthlySalary ?? ""}
                />
              </div>

              <div className="field">
                <label>Data de admissão</label>
                <input
                  name="hiredAt"
                  type="date"
                  defaultValue={editing?.hiredAt ? editing.hiredAt.slice(0, 10) : ""}
                />
              </div>

              <div className="span-4" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button className="btn primary">
                  {editing ? "Salvar alterações" : "Cadastrar funcionário"}
                </button>
                {editing && (
                  <button type="button" className="btn" onClick={() => setEditing(null)}>
                    Cancelar edição
                  </button>
                )}
              </div>
            </form>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="section-title">Funcionários cadastrados</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Cargo</th>
                    <th>Documento</th>
                    <th>Admissão</th>
                    <th>Salário</th>
                    <th>Status</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((employee) => (
                    <tr key={employee.id}>
                      <td><strong>{employee.name}</strong></td>
                      <td>{employee.roleName || "—"}</td>
                      <td>{employee.document || "—"}</td>
                      <td>
                        {employee.hiredAt
                          ? new Date(employee.hiredAt).toLocaleDateString("pt-BR")
                          : "—"}
                      </td>
                      <td>{employee.monthlySalary == null ? "—" : brl(employee.monthlySalary)}</td>
                      <td>
                        <span className={`badge ${employee.status === "ACTIVE" ? "paid" : "pending"}`}>
                          {employee.status === "ACTIVE" ? "Ativo" : "Inativo"}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button type="button" className="btn small" onClick={() => setEditing(employee)}>
                            Editar
                          </button>
                          <button
                            type="button"
                            className="btn small"
                            onClick={() => changeStatus(employee)}
                          >
                            {employee.status === "ACTIVE" ? "Desativar" : "Reativar"}
                          </button>
                          <button
                            type="button"
                            className="btn small danger"
                            onClick={() => removeEmployee(employee)}
                          >
                            Excluir
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
              Funcionários com folhas já registradas não podem ser excluídos definitivamente; nesse caso, desative o cadastro para manter o histórico financeiro.
            </p>
          </div>
        </>
      )}

      {tab === "payroll" && (
        <>
          <div className="card">
            <h2 className="section-title">Gerar folha de pagamento</h2>
            <form className="form-grid" onSubmit={addPayroll}>
              <div className="field span-2">
                <label>Funcionário</label>
                <select name="employeeId" required>
                  <option value="">Selecione</option>
                  {activeEmployees.map((employee) => (
                    <option value={employee.id} key={employee.id}>
                      {employee.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Competência</label>
                <input name="referenceMonth" type="month" required />
              </div>

              <div className="field">
                <label>Vencimento</label>
                <input name="dueDate" type="date" required />
              </div>

              <div className="field">
                <label>Salário bruto</label>
                <input name="grossAmount" type="number" step="0.01" min="0.01" required />
              </div>

              <div className="field">
                <label>Descontos</label>
                <input name="deductions" type="number" step="0.01" min="0" defaultValue="0" />
              </div>

              <div className="field span-2">
                <label>Observação</label>
                <input name="notes" />
              </div>

              <div className="span-4">
                <button className="btn primary">Gerar folha</button>
              </div>
            </form>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <h2 className="section-title">Folhas cadastradas</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Competência</th>
                    <th>Funcionário</th>
                    <th>Vencimento</th>
                    <th>Bruto</th>
                    <th>Descontos</th>
                    <th>Líquido</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {payroll.map((entry) => (
                    <tr key={entry.id}>
                      <td>{entry.referenceMonth}</td>
                      <td>{entry.employee.name}</td>
                      <td>{new Date(entry.dueDate).toLocaleDateString("pt-BR")}</td>
                      <td>{brl(entry.grossAmount)}</td>
                      <td>{brl(entry.deductions)}</td>
                      <td><strong>{brl(entry.netAmount)}</strong></td>
                      <td>{payrollStatus(entry.status)}</td>
                      <td>
                        {entry.status === "PENDING" && (
                          <button
                            type="button"
                            className="btn small primary"
                            onClick={() => payPayroll(entry.id)}
                          >
                            Pagar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
