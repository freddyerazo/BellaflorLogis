import { apiGet, apiPost } from "/js/api.js";

const $ = (sel) => document.querySelector(sel);

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
  const fecha = $("#filtroFecha").value || fechaHoyLocal();
  const [despachos, auditorias] = await Promise.all([
    apiGet(`/auditoria-etiquetas/despachos?fecha=${fecha}`),
    apiGet(`/auditoria-etiquetas/auditorias?fecha=${fecha}`),
  ]);
  auditoriasCargadas = auditorias;
  renderKpis(despachos, auditorias);
  renderDespachos(despachos);
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

function renderDespachos(despachos) {
  const tbody = $("#tablaDespachos");
  if (!despachos.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Sin despachos para esta fecha. Usa "Generar despachos del día" o espera a que el bot los cree con /lista.</td></tr>`;
    return;
  }
  tbody.innerHTML = despachos.map((d) => `
    <tr>
      <td>${d.postcosecha || ""}</td>
      <td>${d.cliente || ""}</td>
      <td>${d.guia_madre || ""}</td>
      <td>${d.guia_hija || ""}</td>
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
    tbody.innerHTML = `<tr><td colspan="10" class="empty">${soloProblemas ? "Sin auditorías con problemas para esta fecha." : "Sin auditorías registradas para esta fecha."}</td></tr>`;
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
  a.download = `auditorias_etiquetas_${$("#filtroFecha").value || fechaHoyLocal()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

$("#filtroFecha").value = fechaHoyLocal();
$("#filtroFecha").addEventListener("change", cargar);
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
    const fecha = $("#filtroFecha").value || fechaHoyLocal();
    const r = await apiPost(`/auditoria-etiquetas/despachos/generar?fecha=${fecha}`, {});
    $("#resultado").innerHTML = `<p class="msg-ok">${r.encontrados} facturas de clientes especiales encontradas, ${r.insertados} despachos nuevos creados.</p>`;
    await cargar();
  } catch (err) {
    $("#resultado").innerHTML = `<p class="msg-error">${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
});

cargar();
