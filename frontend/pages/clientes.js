import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/customers",
  title: "Clientes",
  columns: [
    { key: "customer_code", label: "Código" },
    { key: "customer_name", label: "Nombre" },
    { key: "contact_name", label: "Contacto" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Teléfono" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "customer_code", label: "Código", type: "text", required: true },
    { name: "customer_name", label: "Nombre", type: "text", required: true },
    { name: "contact_name", label: "Contacto", type: "text" },
    { name: "email", label: "Email", type: "text" },
    { name: "phone", label: "Teléfono", type: "text" },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
