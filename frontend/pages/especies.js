import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/species",
  title: "Especies",
  columns: [
    { key: "code", label: "Código" },
    { key: "name", label: "Nombre" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "code", label: "Código", type: "text", required: true },
    { name: "name", label: "Nombre", type: "text", required: true },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
