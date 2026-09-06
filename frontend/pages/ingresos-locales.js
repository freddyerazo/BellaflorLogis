/* ═══════════════════════════════════════════════════════════════════
   INGRESOS LOCALES — Dashboard de entregas (datos desde GAS)
   ═══════════════════════════════════════════════════════════════════ */

let todosLosDatos = [];
let datosFiltrados = [];

async function init() {
  const content = document.getElementById("panel-recibos");
  content.innerHTML = `
    <div class="dashboard-loading">
      <span></span>
      <p style="font-size:16px;font-weight:600;margin-top:16px">Cargando registros desde Google Sheets…</p>
      <p style="font-size:13px;margin-top:8px;color:#397c55;background:#edf7f0;padding:8px 16px;border-radius:8px;border:1px solid #c3e6cb">
        ⏳ La primera carga del día puede tardar <strong>1–2 minutos</strong> (GAS en espera).<br>
        Por favor aguarda — la tabla aparecerá automáticamente.
      </p>
    </div>`;

  try {
    const resp = await fetch("/api/ingresos-locales/datos");
    if (resp.status === 501) {
      content.innerHTML = `
        <div class="dashboard-error">
          <strong>URL no configurada</strong>
          <p>Agrega <code>INGRESOS_LOCALES_URL=&lt;url-del-gas&gt;</code> en el archivo <code>backend/.env</code> y reinicia el servidor.</p>
        </div>`;
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    todosLosDatos = (await resp.json()).reverse();
    renderPage();
  } catch (err) {
    content.innerHTML = `
      <div class="dashboard-error">
        <strong>Error al cargar los registros</strong>
        <p>${err.message}</p>
        <button class="btn btn-primary" onclick="location.reload()">Reintentar</button>
      </div>`;
  }
}

/* ─── Render principal ─────────────────────────────────────────── */
function renderPage() {
  const content = document.getElementById("panel-recibos");
  content.innerHTML = `
    <section class="il-hero">
      <div>
        <h1><i class="ph ph-truck"></i> Recibos registrados</h1>
        <p>Lo que el bot de Telegram lleva capturado — lectura en vivo del Google Sheet.</p>
      </div>
      <div class="il-hero-time">
        Actualizado: <strong id="il-updated">—</strong>
        <button class="btn btn-sm btn-outline" id="btn-refresh">
          <i class="ph ph-arrows-clockwise"></i> Actualizar
        </button>
      </div>
    </section>

    <!-- Tarjetas resumen -->
    <div class="il-resumen" id="il-resumen"></div>

    <!-- Filtros -->
    <div class="card il-filtros">
      <div class="il-filtro-campo" style="flex:2; min-width:200px">
        <label>Buscar</label>
        <div class="search-input-wrap">
          <i class="ph ph-magnifying-glass"></i>
          <input type="text" id="il-buscar" placeholder="Guía, finca, cliente, chofer...">
        </div>
      </div>
      <div class="il-filtro-campo">
        <label>Empresa</label>
        <select id="il-filtro-empresa"><option value="">Todas</option></select>
      </div>
      <div class="il-filtro-campo">
        <label>Fecha</label>
        <input type="date" id="il-filtro-fecha">
      </div>
      <button class="btn btn-outline" id="btn-limpiar">
        <i class="ph ph-x"></i> Limpiar
      </button>
    </div>

    <!-- Tabla -->
    <div class="card" style="padding:0; overflow:hidden">
      <div class="il-tabla-header">
        <h2>Registros de entregas</h2>
        <span class="badge badge-gray" id="il-contador">—</span>
      </div>
      <div style="overflow-x:auto">
        <div id="il-tabla-body"></div>
      </div>
    </div>

    <!-- Modal compartir -->
    <div class="il-overlay" id="il-overlay">
      <div class="il-modal">
        <h3>Compartir entrega</h3>
        <div class="il-modal-guia" id="il-modal-guia">—</div>
        <div class="il-modal-detalle" id="il-modal-detalle"></div>
        <div class="il-link-row">
          <input type="text" id="il-link-input" readonly>
          <button class="btn btn-primary btn-sm" id="btn-copiar">Copiar</button>
        </div>
        <p class="il-copiado" id="il-copiado">✓ Enlace copiado</p>
        <button class="btn btn-outline" style="width:100%" id="btn-cerrar-modal">Cerrar</button>
      </div>
    </div>`;

  // Actualizar hora
  document.getElementById("il-updated").textContent =
    new Date().toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit" });

  poblarResumen();
  poblarFiltroEmpresas();
  aplicarFiltros();

  // Listeners
  document.getElementById("il-buscar").addEventListener("input", aplicarFiltros);
  document.getElementById("il-filtro-empresa").addEventListener("change", aplicarFiltros);
  document.getElementById("il-filtro-fecha").addEventListener("change", aplicarFiltros);
  document.getElementById("btn-limpiar").addEventListener("click", limpiarFiltros);
  document.getElementById("btn-refresh").addEventListener("click", () => init());
  document.getElementById("btn-copiar").addEventListener("click", copiarLink);
  document.getElementById("btn-cerrar-modal").addEventListener("click", cerrarModal);
  document.getElementById("il-overlay").addEventListener("click", (e) => {
    if (e.target === document.getElementById("il-overlay")) cerrarModal();
  });

  // Abrir registro compartido si viene en URL
  const fila = new URLSearchParams(window.location.search).get("fila");
  if (fila) {
    const reg = todosLosDatos.find(r => String(r._fila) === fila);
    if (reg) abrirModal(reg);
  }
}

/* ─── Resumen ──────────────────────────────────────────────────── */
function poblarResumen() {
  const hoyStr = new Date().toLocaleDateString("es-EC", {
    day: "2-digit", month: "2-digit", year: "numeric"
  }).replace(/\//g, "/");

  const mesNum = new Date().getMonth();
  const hoy    = todosLosDatos.filter(r => String(r["Fecha Documento"]).trim() === hoyStr);
  const mes    = todosLosDatos.filter(r => {
    const p = String(r["Fecha Documento"]).split("/");
    return p.length === 3 && parseInt(p[1]) - 1 === mesNum;
  });
  const empresasHoy = [...new Set(hoy.map(r => r["Empresa Logística"]).filter(Boolean))];
  let fullsHoy = 0;
  hoy.forEach(r => {
    const v = String(r["Total Fulls / PCS"] || "").split("/")[0].trim();
    const n = parseFloat(v);
    if (!isNaN(n)) fullsHoy += n;
  });

  document.getElementById("il-resumen").innerHTML = `
    <div class="il-card il-card--accent">
      <div class="il-card-label">Hoy</div>
      <div class="il-card-valor">${hoy.length}</div>
      <div class="il-card-sub">recibos del día</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Total mes</div>
      <div class="il-card-valor">${mes.length}</div>
      <div class="il-card-sub">recibos</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Empresas</div>
      <div class="il-card-valor">${empresasHoy.length}</div>
      <div class="il-card-sub">activas hoy</div>
    </div>
    <div class="il-card">
      <div class="il-card-label">Fulls hoy</div>
      <div class="il-card-valor">${fullsHoy.toFixed(2)}</div>
      <div class="il-card-sub">total entregados</div>
    </div>`;
}

/* ─── Filtros ──────────────────────────────────────────────────── */
function poblarFiltroEmpresas() {
  const empresas = [...new Set(todosLosDatos.map(r => r["Empresa Logística"]).filter(Boolean))].sort();
  const sel = document.getElementById("il-filtro-empresa");
  empresas.forEach(e => {
    const opt = document.createElement("option");
    opt.value = e; opt.textContent = e;
    sel.appendChild(opt);
  });
}

function aplicarFiltros() {
  const texto   = document.getElementById("il-buscar").value.toLowerCase();
  const empresa = document.getElementById("il-filtro-empresa").value;
  const fecha   = document.getElementById("il-filtro-fecha").value;

  datosFiltrados = todosLosDatos.filter(r => {
    const campos = [
      r["N° Guía / Ingreso"], r["Finca / Exportador"], r["Nombre del Cliente"],
      r["Nombre del Chofer"], r["Placa Vehículo"]
    ].join(" ").toLowerCase();
    const passTexto   = !texto   || campos.includes(texto);
    const passEmpresa = !empresa || r["Empresa Logística"] === empresa;
    const passFecha   = !fecha   || coincideFecha(r["Fecha Documento"], fecha);
    return passTexto && passEmpresa && passFecha;
  });

  renderTabla();
}

function coincideFecha(fechaReg, fechaInput) {
  if (!fechaReg || !fechaInput) return false;
  const p = String(fechaReg).split("/");
  if (p.length !== 3) return false;
  return `${p[2]}-${p[1].padStart(2,"0")}-${p[0].padStart(2,"0")}` === fechaInput;
}

function limpiarFiltros() {
  document.getElementById("il-buscar").value = "";
  document.getElementById("il-filtro-empresa").value = "";
  document.getElementById("il-filtro-fecha").value = "";
  aplicarFiltros();
}

/* ─── Tabla ────────────────────────────────────────────────────── */
function renderTabla() {
  const tbody = document.getElementById("il-tabla-body");
  document.getElementById("il-contador").textContent =
    datosFiltrados.length + " registro" + (datosFiltrados.length !== 1 ? "s" : "");

  if (datosFiltrados.length === 0) {
    tbody.innerHTML = `<div class="il-empty">
      <i class="ph ph-leaf" style="font-size:40px; color:var(--color-primary)"></i>
      <p>Sin resultados con esos filtros.</p>
    </div>`;
    return;
  }

  let html = `<table class="il-tabla">
    <thead><tr>
      <th>Fecha</th><th>Empresa</th><th>Guía / Ingreso</th>
      <th>Finca</th><th>Cliente</th><th>Fulls</th><th>Temp.</th><th></th>
    </tr></thead><tbody>`;

  datosFiltrados.forEach((r, i) => {
    const empresa = r["Empresa Logística"] || "—";
    const fecha   = r["Fecha Documento"] || "—";
    const guia    = r["N° Guía / Ingreso"] || "—";
    const finca   = r["Finca / Exportador"] || "—";
    const cliente = r["Nombre del Cliente"] || "—";
    const fulls   = r["Total Fulls / PCS"] || "—";
    const temp    = r["Temperatura (°C)"] || "—";
    const fila    = r["_fila"];

    const tempNum = parseFloat(String(temp).replace(/[^0-9.\-]/g, ""));
    const tempCls = isNaN(tempNum) ? "" : tempNum > 5 ? "il-temp-alt" : "il-temp-ok";
    const badgeCls = badgeEmpresa(empresa);
    const fincaCorta  = finca.length > 22  ? finca.slice(0, 22) + "…" : finca;
    const clienteCorto = cliente.length > 20 ? cliente.slice(0, 20) + "…" : cliente;

    html += `<tr class="il-row" data-idx="${i}">
      <td>${fecha}</td>
      <td><span class="il-badge ${badgeCls}">${empresa}</span></td>
      <td><strong>${guia}</strong></td>
      <td title="${finca}">${fincaCorta}</td>
      <td title="${cliente}">${clienteCorto}</td>
      <td>${fulls}</td>
      <td class="${tempCls}">${temp}</td>
      <td><button class="btn btn-sm btn-outline il-btn-compartir" data-idx="${i}">
        <i class="ph ph-share-network"></i>
      </button></td>
    </tr>`;
  });

  html += "</tbody></table>";
  tbody.innerHTML = html;

  tbody.querySelectorAll(".il-row").forEach(row => {
    row.addEventListener("click", (e) => {
      if (!e.target.closest("button")) {
        abrirModal(datosFiltrados[row.dataset.idx]);
      }
    });
  });
  tbody.querySelectorAll(".il-btn-compartir").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      abrirModal(datosFiltrados[btn.dataset.idx]);
    });
  });
}

function badgeEmpresa(empresa) {
  const e = (empresa || "").toLowerCase();
  if (e.includes("one") || e.includes("teamcargo"))  return "il-badge-one";
  if (e.includes("pacific"))                          return "il-badge-pac";
  if (e.includes("value"))                            return "il-badge-val";
  if (e.includes("logiztik") || e.includes("alliance")) return "il-badge-log";
  if (e.includes("ldsexport") || e.includes("lds"))   return "il-badge-lds";
  if (e.includes("fresh"))                            return "il-badge-fresh";
  return "il-badge-otra";
}

/* ─── Modal ────────────────────────────────────────────────────── */
function abrirModal(reg) {
  if (!reg) return;
  document.getElementById("il-modal-guia").textContent =
    "Guía / Ingreso: " + (reg["N° Guía / Ingreso"] || "—");
  document.getElementById("il-modal-detalle").innerHTML = `
    <strong>Empresa:</strong> ${reg["Empresa Logística"] || "—"}<br>
    <strong>Fecha:</strong> ${reg["Fecha Documento"] || "—"} ${reg["Hora Registro"] || ""}<br>
    <strong>Chofer:</strong> ${reg["Nombre del Chofer"] || "—"} · ${reg["Placa Vehículo"] || "—"}<br>
    <strong>Finca:</strong> ${reg["Finca / Exportador"] || "—"}<br>
    <strong>Cliente:</strong> ${reg["Nombre del Cliente"] || "—"}<br>
    <strong>Cajas:</strong> ${reg["Detalle Cajas"] || "—"}<br>
    <strong>Fulls:</strong> ${reg["Total Fulls / PCS"] || "—"}<br>
    <strong>Temperatura:</strong> ${reg["Temperatura (°C)"] || "—"}`;

  const url = window.location.href.split("?")[0] + "?fila=" + reg["_fila"];
  document.getElementById("il-link-input").value = url;
  document.getElementById("il-copiado").style.display = "none";
  document.getElementById("il-overlay").classList.add("il-overlay--open");
}

function cerrarModal() {
  document.getElementById("il-overlay").classList.remove("il-overlay--open");
}

function copiarLink() {
  const input = document.getElementById("il-link-input");
  navigator.clipboard.writeText(input.value).then(() => {
    document.getElementById("il-copiado").style.display = "block";
  }).catch(() => {
    input.select();
    document.execCommand("copy");
    document.getElementById("il-copiado").style.display = "block";
  });
}

init();
setInterval(init, 180000);

/* ═══════════════════════════════════════════════════════════════════
   SUB-PESTAÑA: Dartis Ventas vs Entregas Locales
   ═══════════════════════════════════════════════════════════════════
   Modulo nuevo, separado del tablero de arriba: aquel es un proxy de solo
   lectura al Apps Script del bot; este lee el mismo Sheet con la API de
   Google, reinterpreta el OCR con Claude y lo cruza contra dartis_ventas.

   El universo lo manda Dartis, no los recibos: cada pedido aparece siempre,
   aunque todavia no se haya procesado ("SIN PROCESAR"). Asi la cobertura
   del 100% se ve en pantalla en vez de ser un hueco silencioso. */

const $$ = (sel) => document.querySelector(sel);

const BADGE_CRUCE = {
  "OK": "badge-green",
  "SIN RECIBO": "badge-orange",
  "AMBIGUO": "badge-blue",
  "SIN PROCESAR": "badge-gray",
};

/* ─── Sub-pestañas ─────────────────────────────────────────────── */
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
    if (tab.dataset.tab === "cruce") cargarCruce();
  });
});

/* ─── Resumen + tabla ──────────────────────────────────────────── */
async function cargarResumenCruce() {
  const r = await fetch("/api/entregas-locales/resumen");
  const d = await r.json();
  const tarjeta = (valor, etiqueta, acento = false) => `
    <div class="il-card${acento ? " il-card--accent" : ""}">
      <div class="il-card-label">${etiqueta}</div>
      <div class="il-card-valor">${(valor ?? 0).toLocaleString("es-EC")}</div>
    </div>`;

  $$("#el-resumen").innerHTML = [
    tarjeta(d.pedidos_dartis, "Pedidos en Dartis", true),
    tarjeta(d.ok, "Con recibo (OK)"),
    tarjeta(d.sin_recibo, "Sin recibo"),
    tarjeta(d.ambiguo, "Ambiguos"),
    tarjeta(d.sin_procesar, "Sin procesar"),
    tarjeta(d.recibos_interpretados, "Recibos interpretados"),
  ].join("");

  if (!d.sheet_configurado) {
    mostrarEl("Falta configurar el acceso al Sheet (ENTREGAS_LOCALES_SHEET_ID o el .json de la cuenta de servicio).", "msg-error");
  }
  return d;
}

async function cargarCruce() {
  await cargarResumenCruce();
  const params = new URLSearchParams();
  const estado = $$("#elFiltroEstado").value;
  const texto = $$("#elBuscar").value.trim();
  const desde = $$("#elDesde").value;
  const hasta = $$("#elHasta").value;
  if (estado) params.set("estado", estado);
  if (texto) params.set("texto", texto);
  if (desde) params.set("desde", desde);
  if (hasta) params.set("hasta", hasta);

  const tbody = $$("#elTabla");
  tbody.innerHTML = `<tr><td colspan="9" class="loading">Cargando…</td></tr>`;
  try {
    const r = await fetch(`/api/entregas-locales/cruce?${params}`);
    const filas = await r.json();
    if (!filas.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty">Sin resultados con esos filtros.</td></tr>`;
      return;
    }
    tbody.innerHTML = filas.map((f) => `
      <tr>
        <td><strong>${f.id_pedido}</strong></td>
        <td>${f.fecha || "—"}</td>
        <td>${f.empresa || "—"}</td>
        <td>${f.agencia_carga || "—"}</td>
        <td class="num">${f.cajas ?? "—"}</td>
        <td>${f.numero_ingreso || "—"}</td>
        <td>${f.fecha_documento || "—"}</td>
        <td>${f.agencia_raw || "—"}</td>
        <td><span class="badge ${BADGE_CRUCE[f.estado] || "badge-gray"}">${f.estado}</span></td>
      </tr>`).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="error">${err.message}</td></tr>`;
  }
}

["elFiltroEstado", "elDesde", "elHasta", "elBuscar"].forEach((id) =>
  $$(`#${id}`).addEventListener("input", cargarCruce)
);

/* ─── Acciones del pipeline ────────────────────────────────────── */
function mostrarEl(msg, clase = "msg-ok") {
  $$("#elResultado").innerHTML = `<p class="${clase}">${msg}</p>`;
}

async function postEl(ruta) {
  const r = await fetch(`/api/entregas-locales/${ruta}`, { method: "POST" });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || r.statusText);
  return d;
}

$$("#btnSincronizar").addEventListener("click", async () => {
  const btn = $$("#btnSincronizar");
  btn.disabled = true;
  mostrarEl("Leyendo el Google Sheet…", "msg-info");
  try {
    const d = await postEl("sincronizar-sheet");
    mostrarEl(`Sheet leído: ${d.leidas} filas (${d.nuevas} nuevas, ${d.actualizadas} actualizadas). Total en la tabla: ${d.total_en_tabla}.`);
    await cargarResumenCruce();
  } catch (err) {
    mostrarEl(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

$$("#btnInterpretar").addEventListener("click", async () => {
  const btn = $$("#btnInterpretar");
  const continuo = $$("#chkContinuo").checked;
  btn.disabled = true;
  try {
    let total = 0;
    let vuelta = 0;
    // En modo continuo se encadena lote tras lote: son ~3.500 recibos a ~3 s
    // cada uno, imposible en una sola peticion sin morir por timeout.
    do {
      vuelta++;
      mostrarEl(`Interpretando con Claude… (lote ${vuelta}, ${total} recibos listos)`, "msg-info");
      const d = await postEl("interpretar?limite=25");
      total += d.procesadas;
      await cargarResumenCruce();
      if (d.errores?.length) {
        mostrarEl(`${total} recibos interpretados. ${d.errores.length} fallaron en el último lote: ${d.errores[0].error}`, "msg-error");
      }
      if (!continuo || d.procesadas === 0 || d.pendientes === 0) {
        mostrarEl(`Listo: ${total} recibos interpretados en esta corrida. Quedan ${d.pendientes} pendientes.`);
        break;
      }
    } while (true);
  } catch (err) {
    mostrarEl(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});

$$("#btnCruzar").addEventListener("click", async () => {
  const btn = $$("#btnCruzar");
  btn.disabled = true;
  mostrarEl("Recalculando el cruce contra dartis_ventas…", "msg-info");
  try {
    const d = await postEl("cruzar");
    mostrarEl(`Cruce recalculado sobre ${d.pedidos.toLocaleString("es-EC")} pedidos: ${d.ok} con recibo, ${d.sin_recibo} sin recibo, ${d.ambiguo} ambiguos (ventana ±${d.ventana_dias} días).`);
    await cargarCruce();
  } catch (err) {
    mostrarEl(err.message, "msg-error");
  } finally {
    btn.disabled = false;
  }
});
