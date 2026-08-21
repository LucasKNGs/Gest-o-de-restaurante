import CrudManager, { type CrudField } from "@/components/CrudManager";

const fields: CrudField[] = [
  {
    "name": "name",
    "label": "Nome",
    "kind": "text",
    "required": true,
    "options": [],
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "unit",
    "label": "Unidade",
    "kind": "text",
    "required": false,
    "options": [],
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "currentStock",
    "label": "Current Stock",
    "kind": "number",
    "required": false,
    "options": [],
    "prismaType": "Decimal",
    "currency": false
  },
  {
    "name": "minimumStock",
    "label": "Minimum Stock",
    "kind": "number",
    "required": false,
    "options": [],
    "prismaType": "Decimal",
    "currency": false
  },
  {
    "name": "averageCost",
    "label": "Custo médio",
    "kind": "number",
    "required": false,
    "options": [],
    "prismaType": "Decimal",
    "currency": true
  },
  {
    "name": "active",
    "label": "Ativo",
    "kind": "checkbox",
    "required": false,
    "options": [],
    "prismaType": "Boolean",
    "currency": false
  }
];
const columns = ["name", "unit", "averageCost", "active", "currentStock", "minimumStock"];

export default function Page() {
  return (
    <CrudManager
      title="Estoque"
      subtitle="Gerencie itens, quantidades, custos e estoque mínimo."
      apiBase="/api/inventory/movements"
      fields={fields}
      columns={columns}
      payableMode={false}
    />
  );
}
