import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/roles",
  title: "Roles",
  mountSelector: "#roles-section",
  columns: [
    { key: "name", label: "Nombre" },
    { key: "description", label: "Descripción" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "name", label: "Nombre", type: "text", required: true },
    { name: "description", label: "Descripción", type: "textarea" },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});

initCrudPage({
  endpoint: "/profiles",
  title: "Usuarios",
  mountSelector: "#profiles-section",
  allowCreate: false,
  allowDelete: false,
  columns: [
    { key: "full_name", label: "Nombre" },
    { key: "email", label: "Email" },
    { key: "role_name", label: "Rol" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    {
      name: "role_id",
      label: "Rol",
      type: "select",
      optionsEndpoint: "/roles",
      optionLabel: (row) => row.name,
      optionValue: (row) => row.id,
    },
    { name: "active", label: "Activo", type: "checkbox" },
  ],
});
