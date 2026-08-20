import { initCrudPage } from "../js/crud-page.js";

initCrudPage({
  endpoint: "/farms",
  title: "Fincas Exportadoras",
  columns: [
    { key: "code",               label: "Código" },
    { key: "name",               label: "Nombre oficial" },
    { key: "dartis_postcosecha", label: "Postcosecha Dartis" },
    { key: "active",             label: "Estado", format: "active-badge" },
  ],
  fields: [
    { name: "code",               label: "Código",             type: "text", required: true },
    { name: "name",               label: "Nombre oficial",     type: "text", required: true },
    { name: "dartis_postcosecha", label: "Postcosecha Dartis", type: "text",
      help: "Código de postcosecha en Dartis (ej: EXPOFLOR, AMAZING, OASIS)" },
    { name: "ocr_variants",       label: "Variantes OCR",      type: "textarea",
      help: "Una variante por línea — nombres que puede generar el OCR para esta finca" },
    { name: "active",             label: "Activo",             type: "checkbox", editOnly: true },
  ],
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
