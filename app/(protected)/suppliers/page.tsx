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
    "name": "document",
    "label": "CNPJ/CPF",
    "kind": "text",
    "required": false,
    "options": [],
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "phone",
    "label": "Telefone",
    "kind": "text",
    "required": false,
    "options": [],
    "prismaType": "String",
    "currency": false
  },
  {
    "name": "email",
    "label": "E-mail",
    "kind": "text",
    "required": false,
    "options": [],
    "prismaType": "String",
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
    "name": "active",
    "label": "Ativo",
    "kind": "checkbox",
    "required": false,
    "options": [],
    "prismaType": "Boolean",
    "currency": false
  }
];
const columns = ["name", "document", "phone", "email", "active"];

export default function Page() {
  return (
    <CrudManager
      title="Fornecedores"
      subtitle="Cadastre, edite, pesquise e gerencie fornecedores."
      apiBase="/api/suppliers"
      fields={fields}
      columns={columns}
      payableMode={false}
    />
  );
}
