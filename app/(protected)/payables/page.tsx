import CrudManager, { type CrudField } from "@/components/CrudManager";

const fields: CrudField[] = [
  {
    "name": "supplierId",
    "label": "Fornecedor",
    "kind": "relation",
    "required": false,
    "options": [],
    "relationApi": "/api/suppliers",
    "relationName": "supplier",
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "categoryId",
    "label": "Categoria",
    "kind": "relation",
    "required": false,
    "options": [],
    "relationApi": "/api/categories",
    "relationName": "category",
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "accountId",
    "label": "Conta / Caixa",
    "kind": "relation",
    "required": false,
    "options": [],
    "relationApi": "/api/accounts",
    "relationName": "account",
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "description",
    "label": "Descrição",
    "kind": "textarea",
    "required": true,
    "options": [],
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "amount",
    "label": "Valor",
    "kind": "number",
    "required": true,
    "options": [],
    "prismaType": "Decimal",
    "currency": true
  },
  {
    "name": "dueDate",
    "label": "Vencimento",
    "kind": "date",
    "required": true,
    "options": [],
    "prismaType": "DateTime",
    "currency": false
  },
  {
    "name": "status",
    "label": "Status",
    "kind": "select",
    "required": false,
    "options": [
      "PENDING",
      "PAID",
      "CANCELED",
      "OVERDUE"
    ],
    "prismaType": "PayableStatus",
    "currency": false
  },
  {
    "name": "paidAt",
    "label": "Data de pagamento",
    "kind": "date",
    "required": false,
    "options": [],
    "prismaType": "DateTime",
    "currency": false
  },
  {
    "name": "paymentMethod",
    "label": "Forma de pagamento",
    "kind": "select",
    "required": false,
    "options": [
      "CASH",
      "PIX",
      "DEBIT_CARD",
      "CREDIT_CARD",
      "BANK_TRANSFER",
      "BOLETO",
      "OTHER"
    ],
    "prismaType": "PaymentMethod",
    "currency": false
  },
  {
    "name": "notes",
    "label": "Observações",
    "kind": "textarea",
    "required": false,
    "options": [],
    "prismaType": "String",
    "currency": false
  }
];
const columns = ["description", "amount", "dueDate", "supplierId", "categoryId", "status", "accountId"];

export default function Page() {
  return (
    <CrudManager
      title="Contas a pagar"
      subtitle="Gerencie vencimentos, alterações, baixas e exclusões."
      apiBase="/api/payables"
      fields={fields}
      columns={columns}
      payableMode={true}
    />
  );
}
