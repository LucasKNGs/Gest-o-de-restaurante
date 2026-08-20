"use client";
import { FormEvent, useEffect, useState } from "react";

type Ref = { id: string; name: string; type?: string };
type Tx = { id: string; type: "INCOME"|"EXPENSE"; description: string; amount: number; occurredAt: string; paymentMethod: string; category?: Ref|null; account?: Ref|null; creator?: { name: string } };
const payment = ["CASH","PIX","DEBIT_CARD","CREDIT_CARD","BANK_TRANSFER","BOLETO","OTHER"];
function brl(n:number){return n.toLocaleString("pt-BR",{style:"currency",currency:"BRL"});}

export default function TransactionsClient(){
 const [rows,setRows]=useState<Tx[]>([]); const [refs,setRefs]=useState<{categories:Ref[];accounts:Ref[]}>({categories:[],accounts:[]}); const [error,setError]=useState("");
 async function load(){const [a,b]=await Promise.all([fetch("/api/transactions"),fetch("/api/reference")]); if(a.ok)setRows(await a.json()); if(b.ok)setRefs(await b.json());}
 useEffect(()=>{load();},[]);
 async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setError("");const f=new FormData(e.currentTarget);const body={type:f.get("type"),description:f.get("description"),amount:f.get("amount"),occurredAt:`${f.get("occurredAt")}T12:00:00`,paymentMethod:f.get("paymentMethod"),categoryId:f.get("categoryId")||null,accountId:f.get("accountId")||null,notes:f.get("notes")||null}; const r=await fetch("/api/transactions",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});if(!r.ok){const d=await r.json();return setError(d.error||"Erro");} e.currentTarget.reset(); await load();}
 async function remove(id:string){if(!confirm("Excluir esta movimentação?"))return; const r=await fetch(`/api/transactions/${id}`,{method:"DELETE"});if(!r.ok){const d=await r.json();alert(d.error||"Erro");return;}load();}
 return <main className="content"><h1 className="page-title">Movimentações</h1><p className="page-subtitle">Registre todas as entradas e saídas do restaurante.</p>
 <div className="card"><h2 className="section-title">Novo lançamento</h2>{error&&<div className="notice error">{error}</div>}<form className="form-grid" onSubmit={submit}>
 <div className="field"><label>Tipo</label><select name="type"><option value="INCOME">Entrada</option><option value="EXPENSE">Saída</option></select></div>
 <div className="field span-2"><label>Descrição</label><input name="description" required placeholder="Ex.: vendas do almoço"/></div>
 <div className="field"><label>Valor</label><input name="amount" type="number" step="0.01" min="0.01" required/></div>
 <div className="field"><label>Data</label><input name="occurredAt" type="date" required defaultValue={new Date().toISOString().slice(0,10)}/></div>
 <div className="field"><label>Pagamento</label><select name="paymentMethod">{payment.map(x=><option key={x}>{x}</option>)}</select></div>
 <div className="field"><label>Categoria</label><select name="categoryId"><option value="">Sem categoria</option>{refs.categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></div>
 <div className="field"><label>Conta/caixa</label><select name="accountId"><option value="">Sem conta</option>{refs.accounts.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></div>
 <div className="field span-4"><label>Observação</label><input name="notes"/></div><div className="span-4"><button className="btn primary">Salvar movimentação</button></div></form></div>
 <div className="card" style={{marginTop:16}}><div className="table-wrap"><table><thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Conta</th><th>Tipo</th><th>Usuário</th><th className="right">Valor</th><th></th></tr></thead><tbody>{rows.map(x=><tr key={x.id}><td>{new Date(x.occurredAt).toLocaleDateString("pt-BR")}</td><td>{x.description}</td><td>{x.category?.name||"—"}</td><td>{x.account?.name||"—"}</td><td><span className={`badge ${x.type==="INCOME"?"income":"expense"}`}>{x.type==="INCOME"?"Entrada":"Saída"}</span></td><td>{x.creator?.name||"—"}</td><td className="right">{brl(x.amount)}</td><td><button className="btn small danger" onClick={()=>remove(x.id)}>Excluir</button></td></tr>)}</tbody></table></div></div></main>;
}
