import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/cargo-agencies",
  title: "Agencias de Carga",
  columns: [
    { key: "code",    label: "Código" },
    { key: "name",    label: "Nombre oficial" },
    { key: "type",    label: "Tipo" },
    { key: "country", label: "País" },
    { key: "active",  label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "code",         label: "Código",           type: "text", required: true },
    { name: "name",         label: "Nombre oficial",   type: "text", required: true },
    { name: "type",         label: "Tipo",             type: "select",
      options: [
        { value: "aerea",      label: "Aérea" },
        { value: "terrestre",  label: "Terrestre" },
        { value: "ambas",      label: "Ambas" },
      ]
    },
    { name: "country",      label: "País",             type: "text" },
    { name: "ocr_variants", label: "Variantes OCR",   type: "textarea",
      help: "Una variante por línea — tal como aparece en los recibos escaneados" },
    { name: "active",       label: "Activo",           type: "checkbox", editOnly: true },
  ],
  // Convierte textarea (líneas) ↔ array antes de enviar/mostrar
  transformBeforeSave(data) {
    if (typeof data.ocr_variants === "string") {
      data.ocr_variants = data.ocr_variants
        .split("\n")
        .map(v => v.trim())
        .filter(Boolean);
    }
    return data;
  },
  transformBeforeEdit(row) {
    if (Array.isArray(row.ocr_variants)) {
      row.ocr_variants = row.ocr_variants.join("\n");
    }
    return row;
  },
});
