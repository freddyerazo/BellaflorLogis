import { apiGet, apiPost } from "/js/api.js";

const $ = (sel) => document.querySelector(sel);

let despachosCargados = [];
let auditoriasCargadas = [];

function badgeSiNo(v) {
  if (v === true) return `<span class="badge badge-green">Sí</span>`;
  if (v === false) return `<span class="badge badge-red">No</span>`;
  return "-";
}

function tieneProblema(a) {
  return a.tipo_caja_ok === false || a.especie_ok === false || a.etiqueta_ok === false;
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
    const claveA = `${a.fecha || ""}|${a.postcosecha || ""}|${a.id_pedido ?? ""}|${a.destinatario || ""}|${a.guia_madre || ""}|${a.guia_hija || ""}`;
    const claveB = `${b.fecha || ""}|${b.postcosecha || ""}|${b.id_pedido ?? ""}|${b.destinatario || ""}|${b.guia_madre || ""}|${b.guia_hija || ""}`;
    return claveA.localeCompare(claveB);
  });
  tbody.innerHTML = ordenados.map((d) => `
    <tr>
      <td>${d.fecha || ""}</td>
      <td>${d.postcosecha || ""}</td>
      <td>${d.id_pedido ?? ""}</td>
      <td>${d.destinatario || ""}</td>
      <td>${d.guia_madre || ""}</td>
      <td>${d.guia_hija || ""}</td>
      <td>${d.cliente || ""}</td>
      <td>${d.cajas ?? ""}</td>
      <td>${d.tipo_caja || ""}</td>
      <td><span class="badge ${d.estado === "AUDITADO" ? "badge-green" : "badge-gray"}">${d.estado}</span></td>
    </tr>
  `).join("");
}

function renderAuditorias() {
  const tbody = $("#tablaAuditorias");
  const soloProblemas = $("#filtroSoloProblemas").checked;
  const auditorias = soloProblemas ? auditoriasCargadas.filter(tieneProblema) : auditoriasCargadas;

  if (!auditorias.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">${soloProblemas ? "Sin auditorías con problemas para este rango." : "Sin auditorías registradas para este rango."}</td></tr>`;
    return;
  }
  tbody.innerHTML = auditorias.map((a) => `
    <tr class="${tieneProblema(a) ? "fila-alerta" : ""}">
      <td>${new Date(a.fecha_hora).toLocaleTimeString("es-EC")}</td>
      <td>${a.auditor || ""}</td>
      <td>${a.cliente || ""}</td>
      <td>${a.cajas_despachadas ?? ""}</td>
      <td>${a.piezas_despachadas ?? ""}</td>
      <td>${badgeSiNo(a.tipo_caja_ok)}</td>
      <td>${badgeSiNo(a.especie_ok)}</td>
      <td>${badgeSiNo(a.etiqueta_ok)}</td>
      <td>${a.observaciones || ""}</td>
      <td>${a.foto_url ? `<img class="foto-thumb" src="${a.foto_url}" alt="Foto de respaldo" loading="lazy" />` : "-"}</td>
    </tr>
  `).join("");
}

function exportarCsv() {
  const soloProblemas = $("#filtroSoloProblemas").checked;
  const auditorias = soloProblemas ? auditoriasCargadas.filter(tieneProblema) : auditoriasCargadas;
  const encabezados = ["Hora", "Auditor", "Cliente", "Cajas", "Piezas", "TipoCajaOK", "EspecieOK", "EtiquetaOK", "Observaciones", "FotoURL"];
  const filas = auditorias.map((a) => [
    new Date(a.fecha_hora).toLocaleTimeString("es-EC"),
    a.auditor || "",
    a.cliente || "",
    a.cajas_despachadas ?? "",
    a.piezas_despachadas ?? "",
    a.tipo_caja_ok === true ? "SI" : a.tipo_caja_ok === false ? "NO" : "",
    a.especie_ok === true ? "SI" : a.especie_ok === false ? "NO" : "",
    a.etiqueta_ok === true ? "SI" : a.etiqueta_ok === false ? "NO" : "",
    (a.observaciones || "").replace(/"/g, '""'),
    a.foto_url || "",
  ]);
  const csv = [encabezados, ...filas]
    .map((fila) => fila.map((v) => `"${v}"`).join(","))
    .join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `auditorias_etiquetas_${$("#filtroDesde").value}_a_${$("#filtroHasta").value}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

$("#filtroDesde").value = fechaHoyLocal();
$("#filtroHasta").value = fechaHoyLocal();
$("#filtroDesde").addEventListener("change", cargar);
$("#filtroHasta").addEventListener("change", cargar);
$("#filtroGuiasCompletas").addEventListener("change", renderDespachos);
$("#filtroSoloProblemas").addEventListener("change", renderAuditorias);
$("#btnExportar").addEventListener("click", exportarCsv);

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
    $("#resultado").innerHTML = `<p class="msg-ok">${r.encontrados} facturas de clientes especiales encontradas, ${r.insertados} despachos nuevos creados.</p>`;
    await cargar();
  } catch (err) {
    $("#resultado").innerHTML = `<p class="msg-error">${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
});

cargar();
