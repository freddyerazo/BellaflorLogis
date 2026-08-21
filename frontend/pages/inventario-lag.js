import { apiGet, apiPost } from "/js/api.js";

// ---------- API del modulo (proxy sobre LAG) ----------
const api = {
  crearOrdenCompra: (payload) => apiPost("/inventario-lag/purchase-orders", payload),
  piezasInventario: () => apiGet("/inventario-lag/pieces"),
  reporteDetallado: (params) => apiGet(`/inventario-lag/full?${new URLSearchParams(params)}`),
  infoCodigosBarra: (shipmentNr) => apiGet(`/inventario-lag/barcode/${encodeURIComponent(shipmentNr)}`),
  infoEnvios: (fecha) => apiGet(`/inventario-lag/shipments?fecha=${fecha}`),
  piezasDespachadas: (fecha) => apiGet(`/inventario-lag/dispatched?fecha=${fecha}`),
  crearOrdenVenta: (payload) => apiPost("/inventario-lag/sales-orders", payload),
  cancelarOrdenVenta: (idOrder) =>
    apiPost("/inventario-lag/sales-orders/cancel", { idOrder: Number(idOrder) }),
  postearInventario: (payload) => apiPost("/inventario-lag/posteo-inventario", payload),
};

// ---------- Utilidades ----------
const $ = (sel) => document.querySelector(sel);

function mostrarError(destino, mensaje) {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = "msg-error";
  p.textContent = mensaje;
  div.appendChild(p);
}

function mostrarMensaje(destino, mensaje, clase = "msg-ok") {
  const div = $(destino);
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = clase;
  p.textContent = mensaje;
  div.appendChild(p);
}

function mostrarTabla(destino, filas) {
  const div = $(destino);
  div.innerHTML = "";

  if (!Array.isArray(filas) || filas.length === 0) {
    mostrarMensaje(destino, "Sin resultados para esta consulta.", "msg-info");
    return;
  }

  const columnas = [...new Set(filas.flatMap((f) => Object.keys(f)))];

  const conteo = document.createElement("p");
  conteo.className = "conteo";
  conteo.textContent = `${filas.length} registro(s)`;
  div.appendChild(conteo);

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const thead = tabla.createTHead().insertRow();
  columnas.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    thead.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((fila) => {
    const tr = tbody.insertRow();
    columnas.forEach((c) => {
      const valor = fila[c];
      tr.insertCell().textContent =
        valor === null || valor === undefined
          ? ""
          : typeof valor === "object"
            ? JSON.stringify(valor)
            : String(valor);
    });
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

async function ejecutar(boton, destino, accion) {
  boton.disabled = true;
  mostrarMensaje(destino, "Consultando...", "msg-info");
  try {
    await accion();
  } catch (err) {
    mostrarError(destino, err.message);
  } finally {
    boton.disabled = false;
  }
}

function datosFormulario(form) {
  const datos = {};
  new FormData(form).forEach((valor, clave) => {
    const texto = String(valor).trim();
    if (texto !== "") datos[clave] = texto;
  });
  return datos;
}

// ---------- Navegacion por sub-pestanas ----------
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(`#panel-${tab.dataset.tab}`).classList.add("active");
  });
});

// ---------- Inventario ----------
const inventario = {
  piezas: [],
  orden: { columna: "rack", asc: true },
};

function aplicarFiltros() {
  const texto = $("#buscar-barcode").value.trim().toLowerCase();
  const rack = $("#filtro-rack").value;

  let filas = inventario.piezas.filter(
    (p) => (!texto || p.barcode.toLowerCase().includes(texto)) && (!rack || p.rack === rack)
  );

  const { columna, asc } = inventario.orden;
  filas = [...filas].sort((a, b) => a[columna].localeCompare(b[columna]) * (asc ? 1 : -1));

  $("#kpi-visibles").textContent = filas.length;
  renderTablaInventario(filas);
}

function renderTablaInventario(filas) {
  const div = $("#res-piezas");
  div.innerHTML = "";

  if (filas.length === 0) {
    mostrarMensaje(
      "#res-piezas",
      inventario.piezas.length === 0
        ? "LAG no reporta piezas en inventario para este cliente."
        : "Ninguna pieza coincide con los filtros aplicados.",
      "msg-info"
    );
    return;
  }

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();

  [
    { clave: "barcode", titulo: "Barcode" },
    { clave: "rack", titulo: "Ubicacion (rack)" },
  ].forEach(({ clave, titulo }) => {
    const th = document.createElement("th");
    const activa = inventario.orden.columna === clave;
    th.textContent = titulo + (activa ? (inventario.orden.asc ? " ▲" : " ▼") : "");
    th.style.cursor = "pointer";
    th.addEventListener("click", () => {
      inventario.orden = {
        columna: clave,
        asc: activa ? !inventario.orden.asc : true,
      };
      aplicarFiltros();
    });
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((pieza) => {
    const tr = tbody.insertRow();
    tr.insertCell().textContent = pieza.barcode;
    tr.insertCell().textContent = pieza.rack;
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

function renderResumenRacks(resumen) {
  const div = $("#res-racks");
  div.innerHTML = "";

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();
  ["Ubicacion (rack)", "Piezas"].forEach((t) => {
    const th = document.createElement("th");
    th.textContent = t;
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  resumen.forEach((fila) => {
    const tr = tbody.insertRow();
    const celdaRack = tr.insertCell();
    const enlace = document.createElement("button");
    enlace.type = "button";
    enlace.className = "enlace";
    enlace.textContent = fila.rack;
    enlace.addEventListener("click", () => {
      $("#filtro-rack").value = fila.rack;
      $("#resumen-racks").open = false;
      aplicarFiltros();
    });
    celdaRack.appendChild(enlace);
    tr.insertCell().textContent = fila.piezas;
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

$("#btn-piezas").addEventListener("click", (e) =>
  ejecutar(e.target, "#res-piezas", async () => {
    const data = await api.piezasInventario();

    inventario.piezas = data.piezas;
    $("#kpi-piezas").textContent = data.total_piezas;
    $("#kpi-racks").textContent = data.total_racks;

    const select = $("#filtro-rack");
    const rackPrevio = select.value;
    select.innerHTML = '<option value="">Todas</option>';
    data.resumen_racks.forEach((r) => {
      const opcion = document.createElement("option");
      opcion.value = r.rack;
      opcion.textContent = `${r.rack} (${r.piezas})`;
      select.appendChild(opcion);
    });
    select.value = data.resumen_racks.some((r) => r.rack === rackPrevio) ? rackPrevio : "";

    renderResumenRacks(data.resumen_racks);

    ["#tarjetas", "#filtros", "#resumen-racks"].forEach((sel) => $(sel).classList.remove("hidden"));
    $("#btn-exportar").disabled = data.total_piezas === 0;
    $("#actualizado").textContent = `Actualizado ${new Date().toLocaleString("es-EC")}`;

    aplicarFiltros();
  })
);

$("#buscar-barcode").addEventListener("input", aplicarFiltros);
$("#filtro-rack").addEventListener("change", aplicarFiltros);

$("#btn-limpiar").addEventListener("click", () => {
  $("#buscar-barcode").value = "";
  $("#filtro-rack").value = "";
  aplicarFiltros();
});

$("#btn-exportar").addEventListener("click", () => {
  const texto = $("#buscar-barcode").value.trim().toLowerCase();
  const rack = $("#filtro-rack").value;
  const filas = inventario.piezas.filter(
    (p) => (!texto || p.barcode.toLowerCase().includes(texto)) && (!rack || p.rack === rack)
  );

  // BOM inicial para que Excel respete los acentos al abrir el CSV.
  const csv = ["barcode;rack", ...filas.map((p) => `${p.barcode};${p.rack}`)].join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `inventario_${new Date().toISOString().slice(0, 10)}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
});

$("#form-barcode").addEventListener("submit", (e) => {
  e.preventDefault();
  const shipmentNr = datosFormulario(e.target).shipmentNr;
  ejecutar(e.target.querySelector("button"), "#res-barcode", async () => {
    mostrarTabla("#res-barcode", await api.infoCodigosBarra(shipmentNr));
  });
});

// ---------- Reporte detallado ----------
const COLUMNAS_REPORTE = [
  { clave: "status", titulo: "Status" },
  { clave: "barcode", titulo: "Barcode" },
  { clave: "shipment_nr", titulo: "Shipment Nr" },
  { clave: "house", titulo: "House" },
  { clave: "exporter", titulo: "Exporter" },
  { clave: "consignee", titulo: "Consignee" },
  { clave: "carrier", titulo: "Carrier" },
  { clave: "location", titulo: "Location" },
  { clave: "product", titulo: "Product" },
  { clave: "description", titulo: "Description" },
  { clave: "tipo", titulo: "Type" },
  { clave: "largo_cm", titulo: "Largo Cm" },
  { clave: "ancho_cm", titulo: "Ancho Cm" },
  { clave: "alto_cm", titulo: "Alto Cm" },
  { clave: "largo_inch", titulo: "Largo Inch" },
  { clave: "ancho_inch", titulo: "Ancho Inch" },
  { clave: "alto_inch", titulo: "Alto Inch" },
  { clave: "unidades", titulo: "Uni/Pcs" },
  { clave: "precio", titulo: "Price" },
  { clave: "peso", titulo: "Weight" },
  { clave: "valor_caja", titulo: "Valor caja" },
];

const reporte = { piezas: [] };

function esRecibida(p) {
  return (p.status || "").toUpperCase().includes("RECEIV");
}

function filtrarReporte() {
  const estado = $("#rep-estado").value;
  const texto = $("#rep-buscar").value.trim().toLowerCase();
  const consignee = $("#rep-consignee").value;

  return reporte.piezas.filter((p) => {
    if (estado === "recibidas" && !esRecibida(p)) return false;
    if (estado === "pendientes" && esRecibida(p)) return false;
    if (consignee && p.consignee !== consignee) return false;
    if (texto) {
      const heno = `${p.barcode} ${p.consignee} ${p.product} ${p.description} ${p.house}`;
      if (!heno.toLowerCase().includes(texto)) return false;
    }
    return true;
  });
}

function renderReporte() {
  const filas = filtrarReporte();
  const div = $("#res-reporte");
  div.innerHTML = "";

  if (filas.length === 0) {
    mostrarMensaje(
      "#res-reporte",
      reporte.piezas.length === 0
        ? "La consulta no devolvio piezas."
        : "Ninguna pieza coincide con los filtros.",
      "msg-info"
    );
    return;
  }

  const conteo = document.createElement("p");
  conteo.className = "conteo";
  conteo.textContent = `${filas.length} de ${reporte.piezas.length} piezas`;
  div.appendChild(conteo);

  const tabla = document.createElement("table");
  tabla.className = "data-table";
  const encabezado = tabla.createTHead().insertRow();
  COLUMNAS_REPORTE.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c.titulo;
    encabezado.appendChild(th);
  });

  const tbody = tabla.createTBody();
  filas.forEach((pieza) => {
    const tr = tbody.insertRow();
    if (!esRecibida(pieza)) tr.className = "pendiente";
    COLUMNAS_REPORTE.forEach((c) => {
      const valor = pieza[c.clave];
      tr.insertCell().textContent = valor === null || valor === undefined ? "" : String(valor);
    });
  });

  const wrap = document.createElement("div");
  wrap.className = "tabla-wrap";
  wrap.appendChild(tabla);
  div.appendChild(wrap);
}

$("#form-reporte").addEventListener("submit", (e) => {
  e.preventDefault();
  const datos = datosFormulario(e.target);

  if (!datos.fecha && !datos.guias) {
    mostrarError("#res-reporte", "Indique una fecha de embarque o al menos una guia.");
    return;
  }

  ejecutar(e.target.querySelector('button[type="submit"]'), "#res-reporte", async () => {
    const data = await api.reporteDetallado(datos);
    reporte.piezas = data.piezas;

    $("#rep-piezas").textContent = data.total_piezas;
    $("#rep-recibidas").textContent = data.total_recibidas;
    $("#rep-pendientes").textContent = data.total_pendientes;
    $("#rep-unidades").textContent = data.total_unidades.toLocaleString("es-EC");
    $("#rep-valor").textContent = `$${data.valor_total.toLocaleString("es-EC")}`;

    const select = $("#rep-consignee");
    select.innerHTML = '<option value="">Todos</option>';
    [...new Set(data.piezas.map((p) => p.consignee).filter(Boolean))].sort().forEach((c) => {
      const opcion = document.createElement("option");
      opcion.value = c;
      opcion.textContent = c;
      select.appendChild(opcion);
    });

    const avisos = $("#avisos-rep");
    avisos.innerHTML = "";
    data.avisos.forEach((texto) => {
      const p = document.createElement("p");
      p.className = "msg-aviso";
      p.textContent = texto;
      avisos.appendChild(p);
    });

    ["#tarjetas-rep", "#filtros-rep"].forEach((s) => $(s).classList.remove("hidden"));
    $("#btn-exportar-rep").disabled = data.total_piezas === 0;
    renderReporte();
  });
});

["#rep-estado", "#rep-consignee"].forEach((s) => $(s).addEventListener("change", renderReporte));
$("#rep-buscar").addEventListener("input", renderReporte);
$("#rep-limpiar").addEventListener("click", () => {
  $("#rep-estado").value = "";
  $("#rep-buscar").value = "";
  $("#rep-consignee").value = "";
  renderReporte();
});

$("#btn-exportar-rep").addEventListener("click", () => {
  const filas = filtrarReporte();
  const escapar = (v) => {
    const t = v === null || v === undefined ? "" : String(v);
    return t.includes(";") || t.includes('"') ? `"${t.replace(/"/g, '""')}"` : t;
  };

  const csv = [
    COLUMNAS_REPORTE.map((c) => c.titulo).join(";"),
    ...filas.map((p) => COLUMNAS_REPORTE.map((c) => escapar(p[c.clave])).join(";")),
  ].join("\r\n");

  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `ResumenCodigosDeBarra_${new Date().toISOString().slice(0, 10)}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
});

// ---------- Envios ----------
$("#form-envios").addEventListener("submit", (e) => {
  e.preventDefault();
  const fecha = datosFormulario(e.target).fecha;
  ejecutar(e.target.querySelector("button"), "#res-envios", async () => {
    mostrarTabla("#res-envios", await api.infoEnvios(fecha));
  });
});

$("#form-despachadas").addEventListener("submit", (e) => {
  e.preventDefault();
  const fecha = datosFormulario(e.target).fecha;
  ejecutar(e.target.querySelector("button"), "#res-despachadas", async () => {
    mostrarTabla("#res-despachadas", await api.piezasDespachadas(fecha));
  });
});

// ---------- Ordenes de compra ----------
function plantillaItemPO() {
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group"><label>Farm Code *</label><input name="farm_code" required maxlength="32" /></div>
      <div class="form-group"><label>Barcode</label><input name="barcode" maxlength="11" /></div>
      <div class="form-group"><label>Box Size</label><input name="box_size" maxlength="16" placeholder="QB" /></div>
      <div class="form-group"><label>Codigo producto</label><input name="product_code" maxlength="32" /></div>
      <div class="form-group"><label>Descripcion</label><input name="product_description" maxlength="128" /></div>
      <div class="form-group"><label>Packing</label><input type="number" name="packing" min="0" /></div>
      <div class="form-group"><label>Precio unitario</label><input type="number" step="0.01" name="unit_price" min="0" /></div>
      <div class="form-group"><label>Largo *</label><input type="number" step="0.01" name="length" required min="0" /></div>
      <div class="form-group"><label>Ancho *</label><input type="number" step="0.01" name="width" required min="0" /></div>
      <div class="form-group"><label>Alto *</label><input type="number" step="0.01" name="height" required min="0" /></div>
      <div class="form-group"><label>Peso bruto *</label><input type="number" step="0.01" name="gross_weight" required min="0" /></div>
      <div class="form-group">
        <label>Unidad de medida *</label>
        <select name="unit_of_measurement"><option value="CM">CM</option><option value="INCH">INCH</option></select>
      </div>
      <div class="form-group"><label>Carrier Code</label><input name="carrier_code" maxlength="8" /></div>
      <div class="form-group"><label>Ship To Code</label><input name="ship_to_code" maxlength="32" /></div>
      <div class="form-group"><label>Fecha de despacho</label><input type="date" name="dispatch_date" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());
  return div;
}

$("#btn-add-item").addEventListener("click", () => $("#items-po").appendChild(plantillaItemPO()));
$("#items-po").appendChild(plantillaItemPO());

const NUMERICOS_PO = ["packing", "unit_price", "length", "width", "height", "gross_weight"];

$("#form-po").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  const cajas = [...form.querySelectorAll("#items-po .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-po", "Agregue al menos una caja al detalle.");
    return;
  }

  const cabecera = {};
  ["consignee_code", "destination_port_code", "post_type", "warehouse_code", "po_number",
   "origin_port_code", "estimated_date", "comments", "accion"].forEach((campo) => {
    const valor = form.elements[campo]?.value.trim();
    if (valor) cabecera[campo] = valor;
  });

  const items = cajas.map((caja) => {
    const item = {};
    caja.querySelectorAll("input, select").forEach((campo) => {
      const valor = campo.value.trim();
      if (valor === "") return;
      item[campo.name] = NUMERICOS_PO.includes(campo.name) ? Number(valor) : valor;
    });
    return item;
  });

  ejecutar(form.querySelector('button[type="submit"]'), "#res-po", async () => {
    const res = await api.crearOrdenCompra({ ...cabecera, items });
    if (res.is_success) {
      mostrarMensaje("#res-po", "Orden de compra registrada correctamente en LAG.");
    } else {
      const detalle = res.errors.length
        ? res.errors.map((x) => `${x.poNumber}: ${x.message}`).join(" | ")
        : res.raw_response;
      mostrarError("#res-po", `LAG rechazo la orden. ${detalle}`);
    }
  });
});

// ---------- Ordenes de venta ----------
function plantillaCaja() {
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group"><label>Box ID (barcode) *</label><input name="boxId" required maxlength="16" /></div>
      <div class="form-group"><label>Precio unitario</label><input type="number" step="0.001" name="unitPrice" min="0" /></div>
      <div class="form-group"><label>Unidades</label><input type="number" name="units" min="0" /></div>
      <div class="form-group"><label>Mark Code</label><input name="markCode" maxlength="16" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());
  return div;
}

$("#btn-add-box").addEventListener("click", () => $("#items-venta").appendChild(plantillaCaja()));
$("#items-venta").appendChild(plantillaCaja());

// LAG espera la fecha en formato MM/dd/yyyy; el input type=date entrega yyyy-MM-dd.
function aFormatoLag(fechaIso) {
  const [anio, mes, dia] = fechaIso.split("-");
  return `${mes}/${dia}/${anio}`;
}

$("#form-venta").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  const cajas = [...form.querySelectorAll("#items-venta .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-venta", "Agregue al menos una caja.");
    return;
  }

  const payload = {
    customerId: form.elements.customerId.value.trim(),
    carrierId: form.elements.carrierId.value.trim(),
    shipDate: aFormatoLag(form.elements.shipDate.value),
    orderNumber: form.elements.orderNumber.value.trim(),
    idOrder: Number(form.elements.idOrder.value),
    boxIds: cajas.map((caja) => {
      const box = {};
      caja.querySelectorAll("input").forEach((campo) => {
        const valor = campo.value.trim();
        if (valor === "") return;
        box[campo.name] = ["unitPrice", "units"].includes(campo.name) ? Number(valor) : valor;
      });
      return box;
    }),
  };

  const poNumber = form.elements.poNumber.value.trim();
  if (poNumber) payload.poNumber = poNumber;

  const generateBOL = form.elements.generateBOL.value;
  if (generateBOL) payload.generateBOL = generateBOL === "true";

  ejecutar(form.querySelector('button[type="submit"]'), "#res-venta", async () => {
    const res = await api.crearOrdenVenta(payload);
    const detalle = res.error || JSON.stringify(res);
    if (String(res.status) === "1") {
      mostrarMensaje("#res-venta", detalle);
    } else {
      mostrarError("#res-venta", detalle);
    }
    if (Array.isArray(res.boxesNotAvailable) && res.boxesNotAvailable.length) {
      const p = document.createElement("p");
      p.className = "msg-info";
      p.textContent = `Cajas no disponibles: ${res.boxesNotAvailable.join(", ")}`;
      $("#res-venta").appendChild(p);
    }
  });
});

$("#form-cancelar").addEventListener("submit", (e) => {
  e.preventDefault();
  const idOrder = e.target.elements.idOrder.value;
  ejecutar(e.target.querySelector("button"), "#res-cancelar", async () => {
    const res = await api.cancelarOrdenVenta(idOrder);
    const detalle = res.error || JSON.stringify(res);
    if (String(res.status) === "1") {
      mostrarMensaje("#res-cancelar", detalle);
    } else {
      mostrarError("#res-cancelar", detalle);
    }
  });
});

// ---------- Posteo de Inventario (PlaceOrder/ordernew, sin ambiente de pruebas) ----------

const normalizarBusqueda = (s) =>
  (s || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

const escapeHtml = (s) =>
  (s || "").toString().replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Combo buscable generico (input de texto + lista filtrada en vivo,
// navegable con flechas/Enter) para catalogos largos donde un <select>
// plano no se puede filtrar. Devuelve el estado (con .seleccionado) para
// poder leerlo despues, p.ej. al armar el mensaje de confirmacion.
function crearComboBuscable({ prefix, cargar, filtro, textoOpcion, valorOpcion, textoSeleccionado, etiquetaCarga }) {
  const estado = { items: [], seleccionado: null, resaltado: -1 };
  const input = document.getElementById(`${prefix}-search`);
  const hidden = document.getElementById(`${prefix}-value`);
  const cont = document.getElementById(`${prefix}-opciones`);
  const combo = document.getElementById(`${prefix}-combo`);

  async function cargarDatos() {
    try {
      const items = await cargar();
      estado.items = filtro(items);
      input.disabled = false;
      input.placeholder = `Escribe para buscar (${estado.items.length} ${etiquetaCarga})...`;
    } catch (err) {
      input.placeholder = `Error cargando ${etiquetaCarga}: ${err.message}`;
    }
  }

  function render(texto) {
    const norm = normalizarBusqueda(texto);
    const coincidencias = estado.items
      .filter((it) => !norm || normalizarBusqueda(textoOpcion(it)).includes(norm))
      .slice(0, 50);
    estado.resaltado = -1;
    cont.innerHTML = coincidencias.length
      ? coincidencias.map((it, i) => `<div class="combo-opcion" data-index="${i}">${escapeHtml(textoOpcion(it))}</div>`).join("")
      : `<div class="combo-vacio">Sin coincidencias</div>`;
    cont._coincidencias = coincidencias;
    cont.classList.add("abierto");
  }

  function seleccionar(item) {
    estado.seleccionado = item;
    input.value = textoSeleccionado(item);
    hidden.value = valorOpcion(item);
    cont.classList.remove("abierto");
  }

  input.addEventListener("input", () => {
    estado.seleccionado = null;
    hidden.value = "";
    render(input.value);
  });
  input.addEventListener("focus", () => render(input.value));
  cont.addEventListener("click", (e) => {
    const fila = e.target.closest(".combo-opcion");
    if (!fila) return;
    const item = cont._coincidencias[Number(fila.dataset.index)];
    if (item) seleccionar(item);
  });
  input.addEventListener("keydown", (e) => {
    const filas = cont.querySelectorAll(".combo-opcion");
    if (!filas.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      estado.resaltado = Math.min(estado.resaltado + 1, filas.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      estado.resaltado = Math.max(estado.resaltado - 1, 0);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (estado.resaltado >= 0) {
        const item = cont._coincidencias[estado.resaltado];
        if (item) seleccionar(item);
      }
      return;
    } else {
      return;
    }
    filas.forEach((f, i) => f.classList.toggle("resaltada", i === estado.resaltado));
  });
  document.addEventListener("click", (e) => {
    if (!combo.contains(e.target)) cont.classList.remove("abierto");
  });

  cargarDatos();
  return estado;
}

// El customerId de LAG viene de customers.customer_code_lag (verificado:
// siempre igual a customer_code cuando existe, 1,409 de 1,703 clientes lo
// tienen poblado). Solo se listan esos — postear con un customerId
// inventado fallaria contra LAG.
const comboCliente = crearComboBuscable({
  prefix: "posteo-customer",
  cargar: () => apiGet("/customers"),
  filtro: (clientes) => clientes.filter((c) => c.customer_code_lag).sort((a, b) => a.customer_name.localeCompare(b.customer_name)),
  textoOpcion: (c) => `${c.customer_name} (${c.customer_code_lag})`,
  textoSeleccionado: (c) => `${c.customer_name} (${c.customer_code_lag})`,
  valorOpcion: (c) => c.customer_code_lag,
  etiquetaCarga: "clientes",
});

// El carrierId viene de truck_company.id_logistic_carrier (catalogo de
// carriers de Miami, cargado desde "ID clientes.xlsx" hoja
// "Listado de Carriers-Miami").
const comboCarrier = crearComboBuscable({
  prefix: "posteo-carrier",
  cargar: () => apiGet("/truck-companies"),
  filtro: (carriers) => carriers,
  textoOpcion: (c) => c.sub_carrier_name && c.sub_carrier_name !== c.carrier_name
    ? `${c.carrier_name} - ${c.sub_carrier_name} (${c.id_logistic_carrier})`
    : `${c.carrier_name} (${c.id_logistic_carrier})`,
  textoSeleccionado: (c) => `${c.carrier_name} (${c.id_logistic_carrier})`,
  valorOpcion: (c) => c.id_logistic_carrier,
  etiquetaCarga: "carriers",
});

// Box ID = barcode de una pieza disponible en bodega (misma fuente que la
// pestana "Inventario", GET /inventario-lag/pieces). Se pide una sola vez
// y se comparte entre todas las filas de caja (cada fila tiene su propio
// combo, pero la lista de piezas es la misma).
let piezasDisponiblesPromise = null;
function obtenerPiezasDisponibles() {
  if (!piezasDisponiblesPromise) {
    piezasDisponiblesPromise = apiGet("/inventario-lag/pieces").then((r) => r.piezas || []);
  }
  return piezasDisponiblesPromise;
}

let contadorCajaPosteo = 0;

function plantillaCajaPosteo() {
  const idx = contadorCajaPosteo++;
  const prefix = `posteo-box-${idx}`;
  const div = document.createElement("div");
  div.className = "item-row";
  div.innerHTML = `
    <div class="form-grid">
      <div class="form-group">
        <label>Box ID (pieza en bodega) *</label>
        <div class="combo-buscable" id="${prefix}-combo">
          <input type="text" id="${prefix}-search" placeholder="Cargando piezas..." autocomplete="off" disabled />
          <input type="hidden" name="boxId" id="${prefix}-value" />
          <div class="combo-opciones" id="${prefix}-opciones"></div>
        </div>
      </div>
      <div class="form-group"><label>Stem Price</label><input type="number" step="0.01" name="stemPrice" min="0" /></div>
    </div>
    <button type="button" class="btn btn-secondary btn-quitar">Quitar</button>`;
  div.querySelector(".btn-quitar").addEventListener("click", () => div.remove());

  crearComboBuscable({
    prefix,
    cargar: obtenerPiezasDisponibles,
    filtro: (piezas) => piezas,
    textoOpcion: (p) => `${p.barcode} (Rack: ${p.rack})`,
    textoSeleccionado: (p) => `${p.barcode} (Rack: ${p.rack})`,
    valorOpcion: (p) => p.barcode,
    etiquetaCarga: "piezas",
  });

  return div;
}

$("#btn-add-box-posteo").addEventListener("click", () => $("#items-posteo").appendChild(plantillaCajaPosteo()));
$("#items-posteo").appendChild(plantillaCajaPosteo());

// LAG espera miamiShipDate en MM/dd/yyyy; el input type=date entrega yyyy-MM-dd.
$("#form-posteo").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;

  if (!form.elements.customerId.value) {
    mostrarError("#res-posteo", "Selecciona un cliente de la lista.");
    return;
  }
  if (!form.elements.carrierId.value) {
    mostrarError("#res-posteo", "Selecciona un carrier de la lista.");
    return;
  }

  const cajas = [...form.querySelectorAll("#items-posteo .item-row")];
  if (cajas.length === 0) {
    mostrarError("#res-posteo", "Agregue al menos una caja.");
    return;
  }

  const boxIdsVacios = cajas.some((caja) => !caja.querySelector('[name="boxId"]').value.trim());
  if (boxIdsVacios) {
    mostrarError("#res-posteo", "Selecciona un Box ID (pieza en bodega) para cada caja.");
    return;
  }

  const boxIds = cajas.map((caja) => {
    const box = { boxId: caja.querySelector('[name="boxId"]').value.trim() };
    const stemPrice = caja.querySelector('[name="stemPrice"]').value.trim();
    if (stemPrice !== "") box.stemPrice = Number(stemPrice);
    return box;
  });

  const payload = {
    customerId: form.elements.customerId.value.trim(),
    carrierId: form.elements.carrierId.value.trim(),
    miamiShipDate: aFormatoLag(form.elements.miamiShipDate.value),
    printWmsLabels: form.elements.printWmsLabels.value === "true",
    boxIds,
  };

  const nombreCliente = comboCliente.seleccionado
    ? `${comboCliente.seleccionado.customer_name} (${payload.customerId})`
    : payload.customerId;
  const nombreCarrier = comboCarrier.seleccionado
    ? `${comboCarrier.seleccionado.carrier_name} (${payload.carrierId})`
    : payload.carrierId;
  const confirmado = window.confirm(
    `Esto crea una orden REAL en el WMS de LAG (sin ambiente de pruebas).\n\n` +
    `Cliente: ${nombreCliente}\nCarrier: ${nombreCarrier}\nFecha: ${payload.miamiShipDate}\n` +
    `Cajas: ${boxIds.map((b) => b.boxId).join(", ")}\n\n¿Confirmas el envío?`
  );
  if (!confirmado) return;

  ejecutar(form.querySelector('button[type="submit"]'), "#res-posteo", async () => {
    const res = await api.postearInventario(payload);
    mostrarMensaje("#res-posteo", `Respuesta de LAG:\n${res.raw_response}`);
  });
});
