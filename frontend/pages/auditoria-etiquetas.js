import { apiGet, apiPost, apiPut } from "/js/api.js";

const $ = (sel) => document.querySelector(sel);

let despachosCargados = [];
let auditoriasCargadas = [];

function badgeConfirmado(v) {
  if (v === true) return `<span class="badge badge-green">Confirmado</span>`;
  if (v === false) return `<span class="badge badge-red">No confirmado</span>`;
  return "-";
}

function tieneProblema(a) {
  return a.confirmado === false;
}

// Un despacho ahora consolida varios id_pedido y tipos de caja de Dartis
// bajo un mismo cliente+HAWB (2026-09-14) -- las filas viejas (de antes del
// cambio) siguen con los campos singulares id_pedido/tipo_caja, asi que se
// muestra lo nuevo si existe y se cae a lo viejo si no.
function formatearPedidos(d) {
  if (d.id_pedidos && d.id_pedidos.length) return d.id_pedidos.join(", ");
  return d.id_pedido ?? "";
}

function formatearTipoCaja(d) {
  const desglose = d.desglose_tipo_caja || {};
  const entradas = Object.entries(desglose);
  if (entradas.length) return entradas.map(([tipo, cajas]) => `${tipo}:${cajas}`).join(", ");
  return d.tipo_caja || "";
}

function fechaHoyLocal() {
  const hoy = new Date();
  const offset = hoy.getTimezoneOffset();
  return new Date(hoy.getTime() - offset * 60000).toISOString().slice(0, 10);
}

async function cargar() {
  // El rango es de solo lectura para consulta -- se puede ver historial hacia
  // atras libremente. Lo unico que siempre mira solo hacia adelante es la
  // accion de generar despachos (botón "Generar despachos del día", que usa
  // fechaHoyLocal() directo sin importar este filtro).
  const desde = $("#filtroDesde").value || fechaHoyLocal();
  const hasta = $("#filtroHasta").value && $("#filtroHasta").value >= desde ? $("#filtroHasta").value : desde;
  $("#filtroHasta").value = hasta;
  const [despachos, auditorias] = await Promise.all([
    apiGet(`/auditoria-etiquetas/despachos?desde=${desde}&hasta=${hasta}`),
    apiGet(`/auditoria-etiquetas/auditorias?desde=${desde}&hasta=${hasta}`),
  ]);
  despachosCargados = despachos;
  auditoriasCargadas = auditorias;
  renderKpis(despachos, auditorias);
  renderDespachos();
  renderAuditorias();
  $("#actualizado").textContent = `Actualizado ${new Date().toLocaleString("es-EC")}`;
}

function renderKpis(despachos, auditorias) {
  const total = despachos.length;
  const auditados = despachos.filter((d) => d.estado === "AUDITADO").length;
  const problemas = auditorias.filter(tieneProblema).length;
  $("#kpi-total").textContent = total;
  $("#kpi-auditados").textContent = auditados;
  $("#kpi-pendientes").textContent = total - auditados;
  $("#kpi-problemas").textContent = problemas;
}

function renderDespachos() {
  const tbody = $("#tablaDespachos");
  const soloGuiasCompletas = $("#filtroGuiasCompletas").checked;
  const despachos = soloGuiasCompletas
    ? despachosCargados.filter((d) => d.guia_madre && d.guia_hija)
    : despachosCargados;

  if (!despachos.length) {
    const mensaje = soloGuiasCompletas
      ? "Ningún despacho de este rango tiene guía madre y guía hija."
      : "Sin despachos para este rango. Usa \"Generar despachos del día\" o espera a que el bot los cree con /lista.";
    tbody.innerHTML = `<tr><td colspan="10" class="empty">${mensaje}</td></tr>`;
    return;
  }
  const ordenados = [...despachos].sort((a, b) => {
    const claveA = `${a.fecha || ""}|${a.postcosecha || ""}|${a.cliente || ""}|${a.destinatario || ""}|${a.guia_madre || ""}|${a.guia_hija || ""}`;
    const claveB = `${b.fecha || ""}|${b.postcosecha || ""}|${b.cliente || ""}|${b.destinatario || ""}|${b.guia_madre || ""}|${b.guia_hija || ""}`;
    return claveA.localeCompare(claveB);
  });
  tbody.innerHTML = ordenados.map((d) => `
    <tr>
      <td>${d.fecha || ""}</td>
      <td>${d.postcosecha || ""}</td>
      <td>${formatearPedidos(d)}</td>
      <td>${d.destinatario || ""}</td>
      <td>${d.guia_madre || ""}</td>
      <td>${d.guia_hija || ""}</td>
      <td>${d.cliente || ""}</td>
      <td>${d.cajas ?? ""}</td>
      <td>${formatearTipoCaja(d)}</td>
      <td><span class="badge ${d.estado === "AUDITADO" ? "badge-green" : "badge-gray"}">${d.estado}</span></td>
    </tr>
  `).join("");
}

function renderAuditorias() {
  const tbody = $("#tablaAuditorias");
  const soloProblemas = $("#filtroSoloProblemas").checked;
  const auditorias = soloProblemas ? auditoriasCargadas.filter(tieneProblema) : auditoriasCargadas;

  if (!auditorias.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">${soloProblemas ? "Sin auditorías con problemas para este rango." : "Sin auditorías registradas para este rango."}</td></tr>`;
    return;
  }
  tbody.innerHTML = auditorias.map((a) => `
    <tr class="${tieneProblema(a) ? "fila-alerta" : ""}">
      <td>${new Date(a.fecha_hora).toLocaleTimeString("es-EC")}</td>
      <td>${a.auditor || ""}</td>
      <td>${a.cliente || ""}</td>
      <td>${a.cajas_despachadas ?? ""}</td>
      <td>${badgeConfirmado(a.confirmado)}</td>
      <td>${a.observaciones || ""}</td>
      <td>${(a.foto_urls || []).map((url) => `<img class="foto-thumb" src="${url}" alt="Foto de respaldo" loading="lazy" />`).join("") || "-"}</td>
    </tr>
  `).join("");
}

function descargarCsv(encabezados, filas, nombreArchivo) {
  const csv = [encabezados, ...filas]
    .map((fila) => fila.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombreArchivo;
  a.click();
  URL.revokeObjectURL(url);
}

function exportarCsv() {
  const soloProblemas = $("#filtroSoloProblemas").checked;
  const auditorias = soloProblemas ? auditoriasCargadas.filter(tieneProblema) : auditoriasCargadas;
  const encabezados = ["Hora", "Auditor", "Cliente", "Cajas", "Confirmado", "Observaciones", "FotoURLs"];
  const filas = auditorias.map((a) => [
    new Date(a.fecha_hora).toLocaleTimeString("es-EC"),
    a.auditor || "",
    a.cliente || "",
    a.cajas_despachadas ?? "",
    a.confirmado === true ? "SI" : a.confirmado === false ? "NO" : "",
    a.observaciones || "",
    (a.foto_urls || []).join(" | "),
  ]);
  descargarCsv(encabezados, filas, `auditorias_etiquetas_${$("#filtroDesde").value}_a_${$("#filtroHasta").value}.csv`);
}

function exportarDespachosExcel() {
  const soloGuiasCompletas = $("#filtroGuiasCompletas").checked;
  const despachos = soloGuiasCompletas
    ? despachosCargados.filter((d) => d.guia_madre && d.guia_hija)
    : despachosCargados;
  const encabezados = ["Fecha", "Poscosecha", "ID Pedidos", "Destinatario", "Guía madre", "Guía hija", "Cliente", "Cajas", "Tipo(s) caja", "Estado"];
  const filas = despachos.map((d) => [
    d.fecha || "",
    d.postcosecha || "",
    formatearPedidos(d),
    d.destinatario || "",
    d.guia_madre || "",
    d.guia_hija || "",
    d.cliente || "",
    d.cajas ?? "",
    formatearTipoCaja(d),
    d.estado || "",
  ]);
  descargarCsv(encabezados, filas, `despachos_etiquetas_${$("#filtroDesde").value}_a_${$("#filtroHasta").value}.csv`);
}

$("#filtroDesde").value = fechaHoyLocal();
$("#filtroHasta").value = fechaHoyLocal();
$("#filtroDesde").addEventListener("change", cargar);
$("#filtroHasta").addEventListener("change", cargar);
$("#filtroGuiasCompletas").addEventListener("change", renderDespachos);
$("#filtroSoloProblemas").addEventListener("change", renderAuditorias);
$("#btnExportar").addEventListener("click", exportarCsv);
$("#btnExportarDespachos").addEventListener("click", exportarDespachosExcel);

$("#tablaAuditorias").addEventListener("click", (ev) => {
  const img = ev.target.closest(".foto-thumb");
  if (!img) return;
  $("#lightboxFotoImg").src = img.src;
  $("#lightboxFoto").hidden = false;
});
$("#lightboxFoto").addEventListener("click", () => {
  $("#lightboxFoto").hidden = true;
  $("#lightboxFotoImg").src = "";
});

$("#btnGenerar").addEventListener("click", async () => {
  const btn = $("#btnGenerar");
  btn.disabled = true;
  $("#resultado").innerHTML = `<p class="msg-info">Generando despachos desde dartis_ventas...</p>`;
  try {
    const r = await apiPost(`/auditoria-etiquetas/despachos/generar?fecha=${fechaHoyLocal()}`, {});
    $("#resultado").innerHTML = `<p class="msg-ok">${r.encontrados} facturas de clientes especiales encontradas: ${r.insertados} despachos nuevos, ${r.actualizados} actualizados con la venta mas reciente.</p>`;
    await cargar();
  } catch (err) {
    $("#resultado").innerHTML = `<p class="msg-error">${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
});

cargar();

/* ─── Clientes a auditar (customers.es_cliente_especial) ───────────────────
   Tabla única en modo checklist: se cargan los clientes que YA auditan,
   se pueden editar sus campos, destildar (= quitarlos sin tocar el resto
   de su registro) o agregar filas nuevas -- nada se manda al servidor
   hasta hacer clic en "Guardar cambios", que aplica todo junto (POST para
   las filas nuevas, PUT solo para las filas existentes que de verdad
   cambiaron). Pedido explicito del usuario: no el modal de una fila a la
   vez que trae el CRUD generico (initCrudPage), que se usa en la pagina
   general de Clientes. */
let clientesOriginales = [];
let clientesIdCounter = 0;

const CLIENTES_CAMPOS = ["customer_code", "customer_name", "dartis_name", "destinatario"];

const escapeHtml = (s) =>
  (s || "").toString().replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function clientesFilaHtml(c, esNueva) {
  const rowId = esNueva ? c._tempId : c.id;
  const marcado = c.es_cliente_especial !== false; // filas existentes siempre llegan en true (vienen filtradas); las nuevas arrancan en true
  return `
    <tr data-row-id="${rowId}" data-es-nueva="${esNueva}" class="${esNueva ? "row-nuevo" : ""}">
      <td><input type="checkbox" data-field="es_cliente_especial" ${marcado ? "checked" : ""} title="Requiere auditoría" /></td>
      <td><input type="text" class="table-input" data-field="customer_code" value="${escapeHtml(c.customer_code)}" /></td>
      <td><input type="text" class="table-input" data-field="customer_name" value="${escapeHtml(c.customer_name)}" /></td>
      <td><input type="text" class="table-input" data-field="dartis_name" value="${escapeHtml(c.dartis_name)}" /></td>
      <td><input type="text" class="table-input" data-field="destinatario" value="${escapeHtml(c.destinatario)}" placeholder="(todas las ventas)" /></td>
      <td class="actions-col"><button type="button" class="btn-link btn-danger" data-action="quitar">✕</button></td>
    </tr>`;
}

function filaValores(tr) {
  const valores = { es_cliente_especial: tr.querySelector('[data-field="es_cliente_especial"]').checked };
  CLIENTES_CAMPOS.forEach((f) => {
    const v = tr.querySelector(`[data-field="${f}"]`).value.trim();
    valores[f] = v === "" ? null : v;
  });
  return valores;
}

function filaEsDistinta(tr, original) {
  const actual = filaValores(tr);
  return Object.keys(actual).some((k) => (original[k] ?? null) !== (actual[k] ?? null));
}

// Cablea los eventos de UNA fila ya insertada en el DOM. Deliberadamente no
// hay ningun "re-render completo de la tabla" en toda esta seccion (buscar,
// agregar, quitar) -- reconstruir el HTML desde los arreglos de origen
// habria descartado cualquier edicion sin guardar que el usuario ya hubiera
// escrito en OTRAS filas todavia visibles.
function clientesAdjuntarEventos(tr) {
  const original = tr.dataset.esNueva === "false"
    ? clientesOriginales.find((c) => String(c.id) === tr.dataset.rowId)
    : null;

  if (original) {
    tr.querySelectorAll("input").forEach((input) => {
      input.addEventListener("input", () => {
        tr.classList.toggle("row-modificada", filaEsDistinta(tr, original));
      });
    });
  }

  tr.querySelector('[data-action="quitar"]').addEventListener("click", () => {
    if (tr.dataset.esNueva === "true") {
      tr.remove();
    } else {
      // "Quitar" en una fila existente = destildar el checkbox (se resuelve al Guardar, no borra nada todavia)
      tr.querySelector('[data-field="es_cliente_especial"]').checked = false;
      tr.classList.toggle("row-modificada", filaEsDistinta(tr, original));
    }
  });
}

function clientesHayFilas() {
  return document.querySelectorAll('#tablaClientes tr[data-row-id]').length > 0;
}

function clientesFiltrarVisibles() {
  const q = (document.getElementById("clientesBuscar").value || "").trim().toLowerCase();
  let visibles = 0;
  document.querySelectorAll('#tablaClientes tr[data-row-id]').forEach((tr) => {
    const texto = q
      ? CLIENTES_CAMPOS.map((f) => tr.querySelector(`[data-field="${f}"]`).value.toLowerCase()).join(" ")
      : "";
    const coincide = !q || texto.includes(q);
    tr.hidden = !coincide;
    if (coincide) visibles += 1;
  });
  const sinCoincidencias = document.getElementById("clientesSinCoincidencias");
  if (sinCoincidencias) sinCoincidencias.hidden = visibles > 0 || !clientesHayFilas();
}

async function cargarClientes() {
  const tbody = document.getElementById("tablaClientes");
  tbody.innerHTML = `<tr><td colspan="6" class="loading">Cargando...</td></tr>`;
  try {
    clientesOriginales = await apiGet("/customers?es_cliente_especial=true");
    tbody.innerHTML = clientesOriginales.map((c) => clientesFilaHtml(c, false)).join("")
      + `<tr id="clientesSinCoincidencias" hidden><td colspan="6" class="empty">Sin clientes que coincidan con la búsqueda.</td></tr>`;
    tbody.querySelectorAll("tr[data-row-id]").forEach(clientesAdjuntarEventos);
    document.getElementById("clientesSinCoincidencias").hidden = clientesHayFilas();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="error">Error: ${err.message}</td></tr>`;
  }
}

document.getElementById("clientesBuscar").addEventListener("input", clientesFiltrarVisibles);

document.getElementById("btnClientesAgregar").addEventListener("click", () => {
  clientesIdCounter += 1;
  const nueva = {
    _tempId: `nuevo-${clientesIdCounter}`,
    customer_code: "", customer_name: "", dartis_name: "", destinatario: "", es_cliente_especial: true,
  };
  const tbody = document.getElementById("tablaClientes");
  tbody.insertAdjacentHTML("afterbegin", clientesFilaHtml(nueva, true));
  clientesAdjuntarEventos(tbody.querySelector(`tr[data-row-id="${nueva._tempId}"]`));
  document.getElementById("clientesBuscar").value = "";
  clientesFiltrarVisibles();
});

document.getElementById("btnClientesGuardar").addEventListener("click", async () => {
  const btn = document.getElementById("btnClientesGuardar");
  const resultado = document.getElementById("clientesResultado");
  const tbody = document.getElementById("tablaClientes");

  const porCrear = [];
  const porActualizar = [];

  tbody.querySelectorAll("tr[data-row-id]").forEach((tr) => {
    const valores = filaValores(tr);
    if (tr.dataset.esNueva === "true") {
      const vacia = CLIENTES_CAMPOS.every((f) => !valores[f]);
      if (vacia) return; // fila agregada y dejada en blanco: se ignora sin avisar
      if (!valores.customer_code || !valores.customer_name || !valores.dartis_name) {
        porCrear.push({ error: true, tempId: tr.dataset.rowId });
        return;
      }
      porCrear.push({ valores });
    } else {
      const original = clientesOriginales.find((c) => String(c.id) === tr.dataset.rowId);
      if (!filaEsDistinta(tr, original)) return;
      if (!valores.customer_code || !valores.customer_name || !valores.dartis_name) {
        porActualizar.push({ error: true, id: tr.dataset.rowId });
        return;
      }
      porActualizar.push({ id: tr.dataset.rowId, valores });
    }
  });

  const incompletas = [...porCrear, ...porActualizar].filter((c) => c.error);
  if (incompletas.length) {
    resultado.innerHTML = `<p class="msg-error">⚠️ ${incompletas.length} fila(s) sin Código, Etiqueta o Dartis (obligatorios) -- ningún campo requerido puede quedar vacío.</p>`;
    return;
  }
  if (!porCrear.length && !porActualizar.length) {
    resultado.innerHTML = `<p class="msg-info">No hay cambios para guardar.</p>`;
    return;
  }

  btn.disabled = true;
  resultado.innerHTML = `<p class="msg-info">Guardando...</p>`;
  try {
    const resultados = await Promise.allSettled([
      ...porCrear.map((c) => apiPost("/customers", c.valores)),
      ...porActualizar.map((c) => apiPut(`/customers/${c.id}`, c.valores)),
    ]);
    const fallidas = resultados.filter((r) => r.status === "rejected");
    const total = porCrear.length + porActualizar.length;
    if (fallidas.length) {
      resultado.innerHTML = `<p class="msg-error">⚠️ ${total - fallidas.length}/${total} cambios guardados. Fallaron ${fallidas.length}: ${fallidas.map((f) => f.reason.message).join("; ")}</p>`;
    } else {
      resultado.innerHTML = `<p class="msg-ok">✅ ${porCrear.length} cliente(s) nuevo(s), ${porActualizar.length} actualizado(s).</p>`;
    }
    await cargarClientes();
  } finally {
    btn.disabled = false;
  }
});

cargarClientes();

/* ─── Navegación por pestañas ─────────────────────────────────────────── */
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
  });
});
