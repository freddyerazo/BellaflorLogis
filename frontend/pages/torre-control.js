import { apiGet, apiPost } from "/js/api.js";

const BADGE = {
  OK: "badge-green",
  DISCREPANCIA: "badge-red",
  PENDIENTE: "badge-gray",
  "SIN MANIFIESTO": "badge-orange",
  "NO EN DARTIS": "badge-red",
};

let snapshot = { cajas: [], resumen: {} };

const $ = (sel) => document.querySelector(sel);

// ---------- Sub-pestanas ----------
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(`#panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ---------- Carga de datos ----------
async function cargarEstado() {
  snapshot = await apiGet("/torre-control/estado");
  renderKpis();
  renderTablaPrincipal();
  renderTablaLocales();
  if (snapshot.actualizado) {
    $("#actualizado").textContent = `Actualizado ${new Date(snapshot.actualizado).toLocaleString("es-EC")}`;
  }
}

function renderKpis() {
  const t = snapshot.resumen?.total || {};
  $("#kpi-guias").textContent = t.guias ?? 0;
  $("#kpi-ok").textContent = t.ok ?? 0;
  $("#kpi-discrepancias").textContent = t.discrepancias ?? 0;
  $("#kpi-pendientes").textContent = t.pendientes ?? 0;
  $("#kpi-sin-manifiesto").textContent = t.sin_manifiesto ?? 0;
  $("#kpi-no-en-dartis").textContent = t.no_en_dartis ?? 0;
}

function renderTablaPrincipal() {
  const estado = $("#filtroEstado").value;
  const courier = $("#filtroCourier").value;
  const texto = $("#filtroBuscar").value.trim().toLowerCase();

  const filas = snapshot.cajas.filter((c) => {
    if (!["UPS", "FEDEX"].includes(c.courier)) return false;
    if (estado && c.conciliacion !== estado) return false;
    if (courier && c.courier !== courier) return false;
    if (texto) {
      const heno = `${c.factura} ${c.cliente || ""} ${c.empresa || ""} ${c.tracking || ""}`.toLowerCase();
      if (!heno.includes(texto)) return false;
    }
    return true;
  });

  const tbody = $("#tablaPrincipal");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">Sin resultados</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.slice(0, 500).map((c) => `
    <tr>
      <td>${c.factura}</td>
      <td>${c.courier}</td>
      <td>${c.empresa || ""}</td>
      <td>${c.cliente || ""}</td>
      <td>${c.cajas_dartis ?? ""}</td>
      <td>${c.bultos_csv ?? c.cajas_manifiesto ?? "-"}</td>
      <td>${c.diferencia ?? "-"}</td>
      <td>${c.estado_vivo || ""}</td>
      <td>${c.ubicacion || ""}</td>
      <td><span class="badge ${BADGE[c.conciliacion] || "badge-gray"}">${c.conciliacion}</span></td>
    </tr>
  `).join("");
  if (filas.length > 500) {
    tbody.innerHTML += `<tr><td colspan="10" class="conteo">Mostrando 500 de ${filas.length} — afina el filtro para ver el resto.</td></tr>`;
  }
}

function renderTablaLocales() {
  const estado = $("#filtroEstadoLocal").value;
  const texto = $("#filtroBuscarLocal").value.trim().toLowerCase();

  const filas = snapshot.cajas.filter((c) => {
    if (["UPS", "FEDEX"].includes(c.courier)) return false;
    if (estado && c.conciliacion !== estado) return false;
    if (texto) {
      const heno = `${c.factura} ${c.courier_raw || ""} ${c.cliente || ""} ${c.empresa || ""}`.toLowerCase();
      if (!heno.includes(texto)) return false;
    }
    return true;
  });

  const tbody = $("#tablaLocales");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin resultados</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.slice(0, 500).map((c) => `
    <tr>
      <td>${c.factura}</td>
      <td>${c.courier_raw || ""}</td>
      <td>${c.empresa || ""}</td>
      <td>${c.cliente || ""}</td>
      <td>${c.fecha_dartis || ""}</td>
      <td>${c.cajas_dartis ?? ""}</td>
      <td>${c.fecha_entrega_real || "-"}</td>
      <td><span class="badge ${BADGE[c.conciliacion] || "badge-gray"}">${c.conciliacion}</span></td>
    </tr>
  `).join("");
  if (filas.length > 500) {
    tbody.innerHTML += `<tr><td colspan="8" class="conteo">Mostrando 500 de ${filas.length} — afina el filtro para ver el resto.</td></tr>`;
  }
}

["filtroEstado", "filtroCourier", "filtroBuscar"].forEach((id) =>
  $(`#${id}`).addEventListener("input", renderTablaPrincipal)
);
["filtroEstadoLocal", "filtroBuscarLocal"].forEach((id) =>
  $(`#${id}`).addEventListener("input", renderTablaLocales)
);

// ---------- Acciones ----------
function mostrarResultado(msg, clase = "msg-ok") {
  $("#resultado").innerHTML = `<p class="${clase}">${msg}</p>`;
}

$("#btnRefrescar").addEventListener("click", async () => {
  const btn = $("#btnRefrescar");
  btn.disabled = true;
  mostrarResultado("Actualizando (dartis_ventas + manifiestos + tracking en vivo)...", "msg-info");
  try {
    const r = await apiPost("/torre-control/refrescar", {});
    mostrarResultado(`Actualizado: ${r.total_facturas} facturas procesadas.`);
    await cargarEstado();
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

$("#btnDuoplane").addEventListener("click", async () => {
  const btn = $("#btnDuoplane");
  btn.disabled = true;
  mostrarResultado("Sincronizando con Duoplane...", "msg-info");
  try {
    const r = await apiPost("/torre-control/sincronizar-duoplane", {});
    if (!r.ok) {
      mostrarResultado(r.error, "msg-error");
    } else {
      mostrarResultado(`Duoplane: ${r.revisadas} POs revisadas, ${r.creados.length} shipments creados, ${r.pendientes.length} pendientes, ${r.errores.length} errores.`);
    }
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

async function subirArchivo(input, path) {
  const file = input.files[0];
  if (!file) return;
  mostrarResultado(`Subiendo ${file.name}...`, "msg-info");
  const form = new FormData();
  form.append("archivo", file);
  try {
    const res = await fetch(`/api${path}`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al subir el archivo");
    mostrarResultado(`${file.name}: ${JSON.stringify(data)}`);
    await cargarEstado();
  } catch (err) {
    mostrarResultado(err.message, "msg-error");
  } finally {
    input.value = "";
  }
}

$("#fileUps").addEventListener("change", (e) => subirArchivo(e.target, "/torre-control/subir-ups"));
$("#fileFedex").addEventListener("change", (e) => subirArchivo(e.target, "/torre-control/subir-fedex"));

cargarEstado();
