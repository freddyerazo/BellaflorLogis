import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/airlines",
  title: "Aerolíneas",
  columns: [
    { key: "airline_code", label: "Código" },
    { key: "airline_name", label: "Nombre" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "airline_code", label: "Código", type: "text", required: true },
    { name: "airline_name", label: "Nombre", type: "text", required: true },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
