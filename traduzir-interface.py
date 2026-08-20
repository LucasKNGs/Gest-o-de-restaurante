
from pathlib import Path

def replace(path_str, old, new, label):
    path = Path(path_str)
    if not path.exists():
        print(f"[AVISO] Arquivo não encontrado: {path_str}")
        return
    text = path.read_text(encoding="utf-8")
    if old not in text:
        print(f"[AVISO] Não encontrei trecho para: {label}")
        return
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[OK] {label}")

# MOVIMENTAÇÕES: formas de pagamento
replace(
    "app/(protected)/transactions/TransactionsClient.tsx",
    'const payment = ["CASH","PIX","DEBIT_CARD","CREDIT_CARD","BANK_TRANSFER","BOLETO","OTHER"];',
    '''const payment = [
 {value:"CASH",label:"Dinheiro"},
 {value:"PIX",label:"Pix"},
 {value:"DEBIT_CARD",label:"Cartão de débito"},
 {value:"CREDIT_CARD",label:"Cartão de crédito"},
 {value:"BANK_TRANSFER",label:"Transferência bancária"},
 {value:"BOLETO",label:"Boleto"},
 {value:"OTHER",label:"Outro"}
];''',
    "Formas de pagamento em Movimentações"
)

replace(
    "app/(protected)/transactions/TransactionsClient.tsx",
    '{payment.map(x=><option key={x}>{x}</option>)}',
    '{payment.map(x=><option key={x.value} value={x.value}>{x.label}</option>)}',
    "Opções de pagamento em português"
)

# CONTAS E CAIXAS
replace(
    "app/(protected)/accounts/AccountsClient.tsx",
    '<select name="type"><option>CASH</option><option>BANK</option><option>PIX</option><option>CARD_CLEARING</option><option>OTHER</option></select>',
    '<select name="type"><option value="CASH">Dinheiro / Caixa físico</option><option value="BANK">Conta bancária</option><option value="PIX">Pix</option><option value="CARD_CLEARING">Recebíveis de cartão</option><option value="OTHER">Outro</option></select>',
    "Tipos de conta"
)

replace(
    "app/(protected)/accounts/AccountsClient.tsx",
    'type A={id:string;name:string;type:string;initialBalance:number;balance:number;active:boolean};',
    'type A={id:string;name:string;type:string;initialBalance:number;balance:number;active:boolean};const accountLabels:Record<string,string>={CASH:"Dinheiro / Caixa físico",BANK:"Conta bancária",PIX:"Pix",CARD_CLEARING:"Recebíveis de cartão",OTHER:"Outro"};',
    "Mapa de tipos de conta"
)

replace(
    "app/(protected)/accounts/AccountsClient.tsx",
    '<div className="kpi-label">{x.type}</div>',
    '<div className="kpi-label">{accountLabels[x.type]||x.type}</div>',
    "Exibição de tipo de conta"
)

# CATEGORIAS
replace(
    "app/(protected)/categories/CategoriesClient.tsx",
    '<select name="type"><option>EXPENSE</option><option>INCOME</option><option>BOTH</option></select>',
    '<select name="type"><option value="EXPENSE">Despesa</option><option value="INCOME">Receita</option><option value="BOTH">Receita e despesa</option></select>',
    "Tipos de categoria"
)

replace(
    "app/(protected)/categories/CategoriesClient.tsx",
    'type C={id:string;name:string;type:string;active:boolean};',
    'type C={id:string;name:string;type:string;active:boolean};const categoryLabels:Record<string,string>={EXPENSE:"Despesa",INCOME:"Receita",BOTH:"Receita e despesa"};',
    "Mapa de categorias"
)

replace(
    "app/(protected)/categories/CategoriesClient.tsx",
    '<td>{x.type}</td>',
    '<td>{categoryLabels[x.type]||x.type}</td>',
    "Exibição de categoria"
)

# ESTOQUE
replace(
    "app/(protected)/inventory/InventoryClient.tsx",
    '<select name="type"><option>IN</option><option>OUT</option><option>ADJUSTMENT</option></select>',
    '<select name="type"><option value="IN">Entrada</option><option value="OUT">Saída</option><option value="ADJUSTMENT">Ajuste de estoque</option></select>',
    "Tipos de movimentação de estoque"
)

replace(
    "app/(protected)/inventory/InventoryClient.tsx",
    '<span className="badge paid">OK</span>',
    '<span className="badge paid">Normal</span>',
    "Situação do estoque"
)

# EQUIPE / PERFIS
replace(
    "app/(protected)/team/TeamClient.tsx",
    '<select name="role"><option>OPERATOR</option><option>VIEWER</option><option>MANAGER</option><option>ADMIN</option></select>',
    '<select name="role"><option value="OPERATOR">Operador</option><option value="VIEWER">Somente leitura</option><option value="MANAGER">Gerente</option><option value="ADMIN">Administrador</option></select>',
    "Perfis de acesso"
)

replace(
    "app/(protected)/team/TeamClient.tsx",
    'type M={id:string;role:string;active:boolean;user:{name:string;email:string}};',
    'type M={id:string;role:string;active:boolean;user:{name:string;email:string}};const roleLabels:Record<string,string>={OWNER:"Proprietário",ADMIN:"Administrador",MANAGER:"Gerente",OPERATOR:"Operador",VIEWER:"Somente leitura"};',
    "Mapa de perfis"
)

replace(
    "app/(protected)/team/TeamClient.tsx",
    '<td><span className="badge">{x.role}</span></td>',
    '<td><span className="badge">{roleLabels[x.role]||x.role}</span></td>',
    "Exibição dos perfis"
)

replace(
    "app/(protected)/team/TeamClient.tsx",
    'OWNER/ADMIN podem cadastrar usuários. MANAGER gerencia operação. OPERATOR lança dados. VIEWER é leitura.',
    'Proprietário e Administrador podem cadastrar usuários. Gerente administra a operação. Operador registra dados. Somente leitura pode apenas consultar.',
    "Explicação dos perfis"
)

# STATUS
status_expr = '({PENDING:"Pendente",PAID:"Pago",CANCELED:"Cancelado",OVERDUE:"Vencido",OPEN:"Aberto",CLOSED:"Fechado",ACTIVE:"Ativo",INACTIVE:"Inativo"} as Record<string,string>)[x.status]||x.status'

replace(
    "app/(protected)/payables/PayablesClient.tsx",
    '>{x.status}</span>',
    '>{({PENDING:"Pendente",PAID:"Pago",CANCELED:"Cancelado",OVERDUE:"Vencido"} as Record<string,string>)[x.status]||x.status}</span>',
    "Status das contas a pagar"
)

replace(
    "app/(protected)/employees/EmployeesClient.tsx",
    '<td>{x.status}</td>',
    '<td>{({PENDING:"Pendente",PAID:"Pago",CANCELED:"Cancelado"} as Record<string,string>)[x.status]||x.status}</td>',
    "Status da folha"
)

replace(
    "app/(protected)/cash/CashClient.tsx",
    '>{x.status}</span>',
    '>{({OPEN:"Aberto",CLOSED:"Fechado"} as Record<string,string>)[x.status]||x.status}</span>',
    "Status do caixa"
)

# PAGAMENTO EM CONTAS A PAGAR: trocar prompt técnico por escolha numerada
replace(
    "app/(protected)/payables/PayablesClient.tsx",
    'const paymentMethod=prompt("Forma: CASH, PIX, DEBIT_CARD, CREDIT_CARD, BANK_TRANSFER, BOLETO, OTHER","PIX")||"PIX";',
    '''const paymentOptions=[{value:"CASH",label:"Dinheiro"},{value:"PIX",label:"Pix"},{value:"DEBIT_CARD",label:"Cartão de débito"},{value:"CREDIT_CARD",label:"Cartão de crédito"},{value:"BANK_TRANSFER",label:"Transferência bancária"},{value:"BOLETO",label:"Boleto"},{value:"OTHER",label:"Outro"}];const paymentChoice=prompt(`Escolha a forma de pagamento pelo número:\\n${paymentOptions.map((p,i)=>`${i+1}. ${p.label}`).join("\\n")}`,"2");if(paymentChoice==null)return;const paymentMethod=paymentOptions[Number(paymentChoice)-1]?.value;if(!paymentMethod){alert("Forma de pagamento inválida");return;}''',
    "Pagamento das contas a pagar"
)

# PAGAMENTO DE FOLHA
replace(
    "app/(protected)/employees/EmployeesClient.tsx",
    'const method=prompt("Forma de pagamento","PIX")||"PIX";',
    '''const paymentOptions=[{value:"CASH",label:"Dinheiro"},{value:"PIX",label:"Pix"},{value:"DEBIT_CARD",label:"Cartão de débito"},{value:"CREDIT_CARD",label:"Cartão de crédito"},{value:"BANK_TRANSFER",label:"Transferência bancária"},{value:"BOLETO",label:"Boleto"},{value:"OTHER",label:"Outro"}];const paymentChoice=prompt(`Escolha a forma de pagamento pelo número:\\n${paymentOptions.map((p,i)=>`${i+1}. ${p.label}`).join("\\n")}`,"2");if(paymentChoice==null)return;const method=paymentOptions[Number(paymentChoice)-1]?.value;if(!method){alert("Forma de pagamento inválida");return;}''',
    "Pagamento da folha"
)

# AUDITORIA
replace(
    "app/(protected)/audit/AuditClient.tsx",
    'type A={id:string;action:string;entity:string;entityId?:string;createdAt:string;actor:{name:string;email:string};data?:unknown};',
    'type A={id:string;action:string;entity:string;entityId?:string;createdAt:string;actor:{name:string;email:string};data?:unknown};const actionLabels:Record<string,string>={CREATE:"Criação",UPDATE:"Alteração",DELETE:"Exclusão",DEACTIVATE:"Desativação",REACTIVATE:"Reativação",ADD_MEMBER:"Usuário adicionado",PAY:"Pagamento",STOCK_MOVEMENT:"Movimentação de estoque",OPEN:"Abertura",CLOSE:"Fechamento"};const entityLabels:Record<string,string>={Transaction:"Movimentação financeira",Account:"Conta / caixa",Category:"Categoria",Supplier:"Fornecedor",AccountsPayable:"Conta a pagar",Employee:"Funcionário",PayrollEntry:"Folha de pagamento",InventoryItem:"Item de estoque",RestaurantMember:"Usuário do sistema",CashSession:"Sessão de caixa"};',
    "Mapas da auditoria"
)

replace(
    "app/(protected)/audit/AuditClient.tsx",
    '<td>{x.action}</td><td>{x.entity}</td>',
    '<td>{actionLabels[x.action]||x.action}</td><td>{entityLabels[x.entity]||x.entity}</td>',
    "Auditoria em português"
)

# EXCEL
replace(
    "app/api/export/route.ts",
    'Pagamento:r.paymentMethod,',
    'Pagamento:({CASH:"Dinheiro",PIX:"Pix",DEBIT_CARD:"Cartão de débito",CREDIT_CARD:"Cartão de crédito",BANK_TRANSFER:"Transferência bancária",BOLETO:"Boleto",OTHER:"Outro"} as Record<string,string>)[r.paymentMethod]||r.paymentMethod,',
    "Forma de pagamento no Excel"
)

# Mensagens de erro que expõem códigos internos
replace(
    "app/api/cash-sessions/route.ts",
    'Abertura de caixa exige uma conta do tipo CASH',
    'Abertura de caixa exige uma conta do tipo Dinheiro / Caixa físico',
    "Mensagem de caixa"
)

replace(
    "app/api/team/route.ts",
    'Somente OWNER/ADMIN',
    'Somente Proprietário ou Administrador',
    "Mensagem de permissão"
)

print()
print("Tradução concluída.")
print("IMPORTANTE: os códigos internos (CASH, PAID, etc.) continuam no banco/API.")
print("Isso é proposital. O usuário vê português, mas a lógica interna não é quebrada.")
print()
print("Agora execute: npm run dev")
