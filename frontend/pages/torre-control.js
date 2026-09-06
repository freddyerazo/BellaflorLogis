/* ─── Torre de Control ("Fedex-Ups See") ───────────────────────────────────
   Portado de REPORTEUPSFEDEX (static/dashboard.html, script inline) a un
   módulo ES para seguir la convención del resto de BLIS. Misma lógica de
   filtrado, misma tabla por bulto, mismos colores — adaptado a los
   endpoints /api/torre-control/* y al modelo de datos de
   courier_reconciliation (sin id_comercializadora, sin fuente_excel/csv/
   fedex: la fuente aquí siempre es dartis_ventas + las tablas de
   manifiesto, no archivos).
   ─────────────────────────────────────────────────────────────────────── */

import { apiGet, apiPost } from "/js/api.js";

let DATA = { cajas: [], resumen: {} };
let refreshMs = 300000, timerUI = null, nextAt = null;

const $ = (sel) => document.querySelector(sel);
const fmt = (n) => (n == null ? "—" : n.toLocaleString ? n.toLocaleString("es-EC") : n);

// ---------- Carga de datos ----------
async function cargar(forzar = false) {
  try {
    if (forzar) { $("#btnRefrescar").disabled = true; await apiPost("/torre-control/refrescar", {}); }
    DATA = await apiGet("/torre-control/estado");
    refreshMs = (DATA.refresh_seconds || 300) * 1000;

    const omitidas = DATA.omitidas_agencias_locales
      ? `${DATA.omitidas_agencias_locales} facturas de agencias locales fuera del proceso`
      : "";
    const fuenteTag = $("#fuenteTag");
    fuenteTag.style.display = "inline-block";
    fuenteTag.className = "torre-info-tag ok";
    fuenteTag.textContent = [
      "Fuente: dartis_ventas + manifiestos (courier_ups_manifest / courier_fedex_envios)",
      omitidas,
    ].filter(Boolean).join("  ·  ");

    if (DATA.error) {
      $("#cuerpo").innerHTML = `<tr><td colspan="13" class="torre-vacio">${DATA.error}</td></tr>`;
    }
    $("#when").textContent = DATA.actualizado ? new Date(DATA.actualizado).toLocaleTimeString("es-EC") : "—";
    sincronizarFiltroEstadoCourier();
    pintarTabla();
  } catch (e) {
    $("#cuerpo").innerHTML = `<tr><td colspan="13" class="torre-vacio">No se pudo conectar con el backend (${e.message}).</td></tr>`;
  } finally {
    $("#btnRefrescar").disabled = false;
    nextAt = Date.now() + refreshMs;
  }
}

function sincronizarFiltroEstadoCourier() {
  // El filtro "Estado courier" arranca con valores típicos de UPS, pero
  // FedEx puede traer cualquier texto de su propio manifiesto. En vez de
  // mantener la lista a mano, se agrega automáticamente cualquier valor
  // nuevo visto en los datos (marcado por defecto).
  const panel = document.querySelector("#fEstadoCourier .torre-ms-panel");
  const existentes = new Set([...panel.querySelectorAll('input[type="checkbox"]')].map((cb) => cb.value));
  const vistos = new Set((DATA.cajas || []).map((c) => (c.estado_csv || "").trim()));
  vistos.forEach((valor) => {
    if (existentes.has(valor)) return;
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = valor;
    cb.checked = true;
    cb.addEventListener("change", pintarTabla);
    label.appendChild(cb);
    label.appendChild(document.createTextNode(" " + (valor || "Sin estado")));
    panel.appendChild(label);
    existentes.add(valor);
  });
}

function estadoCourierSeleccionados() {
  return [...document.querySelectorAll('#fEstadoCourier input[type="checkbox"]:checked')]
    .map((cb) => (cb.value || "").trim().toUpperCase());
}

function filtrarFilas() {
  const q = $("#q").value.trim().toLowerCase();
  const fc = $("#fCourier").value, fe = $("#fEstado").value, fp = $("#fPlanif").value;
  const estadosCourier = estadoCourierSeleccionados();
  const desde = $("#fDesde").value, hasta = $("#fHasta").value;
  return (DATA.cajas || []).filter((c) => {
    if (c.courier !== "UPS" && c.courier !== "FEDEX") return false;
    if (fc && c.courier !== fc) return false;
    const estadoCsv = (c.estado_csv || "").trim().toUpperCase();
    if (estadosCourier.length && !estadosCourier.includes(estadoCsv)) return false;
    if (fp && entregaPlanificacion(c) !== fp) return false;
    if (fe && c.conciliacion !== fe) return false;
    if (desde && (!c.fecha_dartis || c.fecha_dartis < desde)) return false;
    if (hasta && (!c.fecha_dartis || c.fecha_dartis > hasta)) return false;
    const trackings = (c.detalle_bultos && c.detalle_bultos.length) ? c.detalle_bultos.map((b) => b.tracking) : [c.tracking];
    if (q && ![...trackings, c.cliente, c.factura, c.destinatario, c.empresa].join(" ").toLowerCase().includes(q)) return false;
    return true;
  });
}

// Día de salida -> días hábiles hasta la entrega esperada
//   Lunes->Jueves(+3) Martes->Viernes(+3) Miércoles->Lunes sig.(+5)
//   Jueves->Lunes sig.(+4) Viernes->Martes sig.(+4) Sábado->Miércoles sig.(+4)
const OFFSET_ENTREGA = { 1: 3, 2: 3, 3: 5, 4: 4, 5: 4, 6: 4 };

function entregaPlanificacion(c) {
  if (!c.fecha_dartis || !c.entrega_programada) return "—";
  const [ys, ms, ds] = c.fecha_dartis.split("-").map(Number);
  const salida = new Date(ys, ms - 1, ds);
  const offset = OFFSET_ENTREGA[salida.getDay()];
  if (offset === undefined) return "—";
  const esperada = new Date(salida);
  esperada.setDate(esperada.getDate() + offset);
  const [me, de, ye] = c.entrega_programada.split("/").map(Number);
  if (!me || !de || !ye) return "—";
  const real = new Date(ye, me - 1, de);
  return real.getTime() > esperada.getTime() ? "RETRASO" : "A TIEMPO";
}

// Paleta ejecutiva Bellaflor para indicadores de estado/planificación
const COLOR_ESTADO = {
  "Delivered": "#6F7F1F",
  "In Transit": "#4A5C6B",
  "Out For Delivery": "#3D6E63",
  "Manifest": "#8A6D2E",
  "Exception": "#8C2F2F",
};
const COLOR_PLANIF = { "A TIEMPO": "#6F7F1F", "RETRASO": "#8C2F2F" };
function colorEstado(estado) { return COLOR_ESTADO[estado] || "#8A6D2E"; }
function tag(texto, color) {
  return `<span class="torre-tag"><span class="dot" style="background:${color}"></span>${texto}</span>`;
}

function pintarTabla() {
  const rows = filtrarFilas();
  if (!rows.length) {
    $("#cuerpo").innerHTML = `<tr><td colspan="13" class="torre-vacio">Sin resultados con los filtros aplicados. Limpia la búsqueda para ver todas las guías.</td></tr>`;
    return;
  }
  $("#cuerpo").innerHTML = rows.map((c) => {
    const cls = c.conciliacion === "OK" ? "ok" : (c.conciliacion === "DISCREPANCIA" || c.conciliacion === "NO EN DARTIS") ? "mal" : "";
    const dif = c.diferencia == null ? "—" : (c.diferencia > 0 ? "−" + c.diferencia : (c.diferencia < 0 ? "+" + (-c.diferencia) : "0"));
    const bultos = (c.detalle_bultos && c.detalle_bultos.length)
      ? c.detalle_bultos
      : (c.tracking ? [{ tracking: c.tracking, estado: c.estado_csv, entrega_programada: c.entrega_programada }] : []);
    const filas = bultos.map((b) => {
      const p = entregaPlanificacion({ fecha_dartis: c.fecha_dartis, entrega_programada: b.entrega_programada });
      const colorP = COLOR_PLANIF[p];
      return {
        tracking: b.tracking || "—",
        estadoHtml: (() => {
          const estadoTxt = b.estado || c.estado_vivo || "Sin estado";
          const entregaTxt = b.entrega_programada || c.entrega_estimada || "";
          const colorE2 = colorEstado(estadoTxt);
          return `${tag(estadoTxt, colorE2)}${entregaTxt ? `<br><span class="torre-mono" style="color:#5d6b78;font-size:.74rem">entrega est. ${entregaTxt}</span>` : ""}`;
        })(),
        planifHtml: colorP ? tag(p, colorP) : "—",
        consultaHtml: b.tracking
          ? `<a class="torre-btn-consulta" target="_blank" rel="noopener" href="${c.courier === "FEDEX" ? `https://www.fedex.com/fedextrack/?trknbr=${encodeURIComponent(b.tracking)}` : `https://www.ups.com/track?track=yes&trackNums=${encodeURIComponent(b.tracking)}&loc=en_US&requester=ST/trackdetails`}">Consultar</a>`
          : "—",
      };
    });
    if (!filas.length) filas.push({ tracking: "—", estadoHtml: "—", planifHtml: "—", consultaHtml: "—" });
    const rowspan = filas.length;
    const estadoConciliacion = ({ OK: "OK", DISCREPANCIA: "DISCREPANCIA", PENDIENTE: "PENDIENTE", "SIN MANIFIESTO": "SINMAN", "NO EN DARTIS": "NODARTIS" })[c.conciliacion] || "PENDIENTE";
    return filas.map((f, i) => `<tr class="torre-bulto-row ${i === 0 ? "torre-factura-inicio" : ""}">
      ${i === 0 ? `
      <td rowspan="${rowspan}" class="torre-mono torre-dato-factura">${c.fecha_dartis || "—"}</td>
      <td rowspan="${rowspan}" class="torre-dato-factura"><span class="torre-courier ${c.courier}">${c.courier}</span></td>
      <td rowspan="${rowspan}" class="torre-dato-factura" style="font-size:.76rem">${c.vendedor_cliente || "—"}</td>
      <td rowspan="${rowspan}" class="torre-dato-factura" style="font-size:.76rem">${c.empresa || "—"}</td>
      <td rowspan="${rowspan}" class="torre-dato-factura"><b>${c.cliente || "—"}</b><br><span class="torre-mono" style="font-size:.72rem;color:#5d6b78">${c.factura}</span></td>
      <td rowspan="${rowspan}" class="torre-dato-factura">${c.destinatario || "—"}</td>` : ""}
      <td class="torre-mono torre-tracking-cell">${f.tracking}</td>
      <td>${f.estadoHtml}</td>
      <td>${f.planifHtml}</td>
      <td>${f.consultaHtml}</td>
      ${i === 0 ? `
      <td rowspan="${rowspan}" class="torre-dato-factura"><span class="torre-riel ${cls}">
        <span class="n torre-mono" title="Total Dartis">${fmt(c.cajas_dartis)}</span><span class="sep">→</span>
        <span class="n torre-mono" title="Bultos en el manifiesto del courier">${c.cajas_manifiesto ?? "—"}</span></span></td>
      <td rowspan="${rowspan}" class="torre-dif ${c.diferencia ? "neg" : ""} torre-mono torre-dato-factura">${dif}</td>
      <td rowspan="${rowspan}" class="torre-dato-factura"><span class="torre-estado ${estadoConciliacion}">${c.conciliacion}</span></td>` : ""}
    </tr>`).join("");
  }).join("");
}

function fechaISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
const hoy = new Date();
const hace15 = new Date(); hace15.setDate(hoy.getDate() - 15);
$("#fDesde").value = fechaISO(hace15);
$("#fHasta").value = fechaISO(hoy);
$("#fCourier").value = "";
// Se fija explícitamente en vez de dejarlo al atributo `selected` del HTML:
// al recargar, el navegador restaura el valor que tenía el select.
$("#fEstado").value = "OK";

["q", "fDesde", "fHasta", "fCourier", "fPlanif", "fEstado"].forEach((id) => $("#" + id).addEventListener("input", pintarTabla));
$("#btnRefrescar").addEventListener("click", () => cargar(true));

// ---------- Subida de manifiestos ----------
function mostrarResultado(msg, clase = "msg-ok") {
  $("#resultado").innerHTML = `<p class="${clase}">${msg}</p>`;
}

async function subirArchivo(input, ruta, etiqueta, labelId, textoLabel) {
  const file = input.files[0];
  if (!file) return;
  const labelSpan = $(`#${labelId}`);
  labelSpan.closest("label").style.opacity = ".6";
  labelSpan.textContent = "Subiendo…";
  mostrarResultado(`Subiendo ${file.name}…`, "msg-info");
  const form = new FormData();
  form.append("archivo", file);
  try {
    const res = await fetch(`/api/torre-control/${ruta}`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al subir el archivo");
    const partes = [`"${data.archivo}" subido correctamente.`];
    if (ruta === "subir-ups") {
      partes.push(`${data.bultos_importados} bulto(s) (${data.nuevos} nuevos, ${data.actualizados} actualizados) en ${data.facturas} factura(s).`);
      if (data.descartados_sin_po) partes.push(`${data.descartados_sin_po} fila(s) descartadas sin token PO:<numero>.`);
    } else {
      partes.push(`${data.nuevos} envío(s) nuevo(s) de ${data.envios_en_pdf} en el PDF (${data.duplicados} ya estaban registrados) en ${data.facturas} factura(s).`);
      if (data.descartados_sin_po) partes.push(`${data.descartados_sin_po} envío(s) descartados sin token PO:<numero>.`);
    }
    mostrarResultado(partes.join(" "));
    await cargar(true);
  } catch (err) {
    mostrarResultado(`No se pudo subir ${etiqueta}: ${err.message}`, "msg-error");
  } finally {
    labelSpan.closest("label").style.opacity = "";
    labelSpan.textContent = textoLabel;
    input.value = "";
  }
}

$("#fileUps").addEventListener("change", (e) =>
  subirArchivo(e.target, "subir-ups", "el manifiesto de UPS", "labelFileUps", "Subir manifiesto UPS (.csv)"));
$("#fileFedex").addEventListener("change", (e) =>
  subirArchivo(e.target, "subir-fedex", "el manifiesto de FedEx", "labelFileFedex", "Subir manifiesto FedEx (.pdf)"));

// ---------- Duoplane ----------
$("#btnDuoplane").addEventListener("click", async () => {
  const tagEl = $("#duoplaneTag");
  $("#btnDuoplane").disabled = true;
  $("#btnDuoplane").textContent = "Sincronizando…";
  tagEl.className = "torre-info-tag";
  tagEl.style.display = "inline-block";
  tagEl.textContent = "Consultando Duoplane…";
  try {
    const data = await apiPost("/torre-control/sincronizar-duoplane", {});
    if (!data.ok) throw new Error(data.error || "Error desconocido");
    const nCreados = data.creados.length, nPendientes = data.pendientes.length, nErrores = data.errores.length;
    tagEl.classList.add(nErrores ? "err" : "ok");
    tagEl.textContent = `Duoplane: ${data.revisadas} PO revisadas · ${nCreados} shipment(s) creado(s) · ${nPendientes} sin tracking aún` + (nErrores ? ` · ${nErrores} error(es)` : "");
    mostrarResultado(`Sincronización con Duoplane completada: ${nCreados} shipment(s) creado(s) de ${data.revisadas} PO revisadas.`);
  } catch (e) {
    tagEl.classList.add("err");
    tagEl.textContent = "Duoplane: error — " + e.message;
    mostrarResultado(`No se pudo sincronizar con Duoplane: ${e.message}`, "msg-error");
  } finally {
    $("#btnDuoplane").disabled = false;
    $("#btnDuoplane").textContent = "Sincronizar Duoplane";
  }
});

// ---------- Multiselect "Estado courier" ----------
const msBtn = document.querySelector("#fEstadoCourier .torre-ms-btn");
const msPanel = document.querySelector("#fEstadoCourier .torre-ms-panel");
msBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const abierto = !msPanel.hidden;
  msPanel.hidden = abierto;
  msBtn.setAttribute("aria-expanded", String(!abierto));
});
document.addEventListener("click", (e) => {
  if (!$("#fEstadoCourier").contains(e.target)) { msPanel.hidden = true; msBtn.setAttribute("aria-expanded", "false"); }
});
msPanel.querySelectorAll('input[type="checkbox"]').forEach((cb) => cb.addEventListener("change", pintarTabla));

// ---------- Cuenta regresiva del próximo refresco ----------
timerUI = setInterval(() => {
  if (!nextAt) return;
  const s = Math.max(0, Math.round((nextAt - Date.now()) / 1000));
  $("#count").textContent = `· próximo refresco en ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  if (s === 0) { nextAt = null; cargar(); }
}, 1000);

cargar();
