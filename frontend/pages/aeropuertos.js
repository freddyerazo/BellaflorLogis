import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/airports",
  title: "Aeropuertos",
  columns: [
    { key: "iata_code", label: "Código IATA" },
    { key: "airport_name", label: "Nombre" },
    { key: "city", label: "Ciudad" },
    { key: "country_name", label: "País" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "iata_code", label: "Código IATA", type: "text", required: true },
    { name: "airport_name", label: "Nombre", type: "text", required: true },
    { name: "city", label: "Ciudad", type: "text" },
    {
      name: "country_id",
      label: "País",
      type: "select",
      optionsEndpoint: "/countries",
      optionLabel: (row) => `${row.code} - ${row.name}`,
      optionValue: (row) => row.id,
    },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
