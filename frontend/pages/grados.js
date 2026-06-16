import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/product-sizes",
  title: "Grados",
  columns: [
    { key: "species_name", label: "Especie" },
    { key: "size_code", label: "Grado" },
    { key: "description", label: "Descripción" },
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
    { name: "size_code", label: "Grado", type: "text", required: true },
    { name: "description", label: "Descripción", type: "text" },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
