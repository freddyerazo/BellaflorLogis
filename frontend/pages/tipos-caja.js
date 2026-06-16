import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/box-types",
  title: "Tipos de Caja",
  columns: [
    { key: "box_code", label: "Código" },
    { key: "box_name", label: "Nombre" },
    { key: "length_cm", label: "Largo (cm)" },
    { key: "width_cm", label: "Ancho (cm)" },
    { key: "height_cm", label: "Alto (cm)" },
    { key: "cube_ft3", label: "Volumen (ft³)" },
    { key: "reference_weight_kg", label: "Peso ref. (kg)" },
    { key: "active", label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "box_code", label: "Código", type: "text", required: true },
    { name: "box_name", label: "Nombre", type: "text" },
    { name: "length_cm", label: "Largo (cm)", type: "number", step: "0.01", required: true },
    { name: "width_cm", label: "Ancho (cm)", type: "number", step: "0.01", required: true },
    { name: "height_cm", label: "Alto (cm)", type: "number", step: "0.01", required: true },
    { name: "cube_ft3", label: "Volumen (ft³)", type: "number", step: "0.0001" },
    { name: "reference_weight_kg", label: "Peso ref. (kg)", type: "number", step: "0.01" },
    { name: "active", label: "Activo", type: "checkbox", editOnly: true },
  ],
});
