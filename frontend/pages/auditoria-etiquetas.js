import { apiGet, apiPost } from "/js/api.js";

const $ = (sel) => document.querySelector(sel);

function badgeSiNo(v) {
  if (v === true) return `<span class="badge badge-green">Sí</span>`;
  if (v === false) return `<span class="badge badge-red">No</span>`;
  return "-";
}

async function cargar() {
  const [despachos, auditorias] = await Promise.all([
    apiGet("/auditoria-etiquetas/despachos"),
    apiGet("/auditoria-etiquetas/auditorias"),
  ]);
  renderKpis(despachos);
  renderDespachos(despachos);
  renderAuditorias(auditorias);
  $("#actualizado").textContent = `Actualizado ${new Date().toLocaleString("es-EC")}`;
}

function renderKpis(despachos) {
  const total = despachos.length;
  const auditados = despachos.filter((d) => d.estado === "AUDITADO").length;
  $("#kpi-total").textContent = total;
  $("#kpi-auditados").textContent = auditados;
  $("#kpi-pendientes").textContent = total - auditados;
}

function renderDespachos(despachos) {
  const tbody = $("#tablaDespachos");
  if (!despachos.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Sin despachos hoy. Usa "Generar despachos de hoy" o espera a que el bot los cree con /lista.</td></tr>`;
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

function renderAuditorias(auditorias) {
  const tbody = $("#tablaAuditorias");
  if (!auditorias.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">Sin auditorías registradas hoy.</td></tr>`;
    return;
  }
  tbody.innerHTML = auditorias.map((a) => `
    <tr>
      <td>${new Date(a.fecha_hora).toLocaleTimeString("es-EC")}</td>
      <td>${a.auditor || ""}</td>
      <td>${a.cliente || ""}</td>
      <td>${a.cajas_despachadas ?? ""}</td>
      <td>${a.piezas_despachadas ?? ""}</td>
      <td>${badgeSiNo(a.tipo_caja_ok)}</td>
      <td>${badgeSiNo(a.especie_ok)}</td>
      <td>${badgeSiNo(a.etiqueta_ok)}</td>
      <td>${a.observaciones || ""}</td>
      <td>${a.foto_url ? `<a href="${a.foto_url}" target="_blank" rel="noopener">Ver foto</a>` : "-"}</td>
    </tr>
  `).join("");
}

$("#btnGenerar").addEventListener("click", async () => {
  const btn = $("#btnGenerar");
  btn.disabled = true;
  $("#resultado").innerHTML = `<p class="msg-info">Generando despachos desde dartis_ventas...</p>`;
  try {
    const r = await apiPost("/auditoria-etiquetas/despachos/generar", {});
    $("#resultado").innerHTML = `<p class="msg-ok">${r.encontrados} facturas de clientes especiales encontradas, ${r.insertados} despachos nuevos creados.</p>`;
    await cargar();
  } catch (err) {
    $("#resultado").innerHTML = `<p class="msg-error">${err.message}</p>`;
  } finally {
    btn.disabled = false;
  }
});

cargar();
