import CrudManager, { type CrudField } from "@/components/CrudManager";

const fields: CrudField[] = [
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
    "name": "type",
    "label": "Tipo",
    "kind": "select",
    "required": true,
    "options": [
      "INCOME",
      "EXPENSE"
    ],
    "prismaType": "TransactionType",
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
    "name": "occurredAt",
    "label": "Data",
    "kind": "date",
    "required": true,
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
  },
  {
    "name": "reference",
    "label": "Reference",
    "kind": "text",
    "required": false,
    "options": [],
    "prismaType": "String",
    "currency": false
  }
];
const columns = ["description", "type", "amount", "occurredAt", "categoryId", "accountId", "paymentMethod"];

export default function Page() {
  return (
    <CrudManager
      title="Movimentações"
      subtitle="Controle entradas e saídas com acesso rápido às ações."
      apiBase="/api/transactions"
      fields={fields}
      columns={columns}
      payableMode={false}
    />
  );
}
