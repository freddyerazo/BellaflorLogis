import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/varieties",
  title: "Variedades",
  columns: [
    { key: "species_name", label: "Especie" },
    { key: "code", label: "Código" },
    { key: "name", label: "Nombre" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    {
      name: "species_id",
      label: "Especie",
      type: "select",
      required: true,
      optionsEndpoint: "/species",
      optionLabel: (row) => `${row.code} - ${row.name}`,
      optionValue: (row) => row.id,
    },
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text", required: true },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
