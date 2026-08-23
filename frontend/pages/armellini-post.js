import { apiGet, apiPost } from "/js/api.js";

const API = "/armellini-post";
let cajas = [];

// ── Subtabs ───────────────────────────────────────────────────────────────────
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
    if (tab.dataset.tab === "historial") cargarHistorial();
    if (tab.dataset.tab === "consignees") cargarConsignees();
  });
});

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const avisosHtml = (avisos) =>
  !avisos?.length
    ? ""
    : `<div class="result-alert alert-warn"><i class="ph ph-warning"></i> <strong>Revisar:</strong>
        <ul>${avisos.map((a) => `<li>${esc(a)}</li>`).join("")}</ul></div>`;

// ── 1 · Importar ──────────────────────────────────────────────────────────────
const zona = document.getElementById("drop_ops");
const input = document.getElementById("file_ops");
const btnImp = document.getElementById("btnImportar");

zona.addEventListener("click", () => input.click());
zona.addEventListener("dragover", (e) => { e.preventDefault(); zona.classList.add("drag-over"); });
zona.addEventListener("dragleave", () => zona.classList.remove("drag-over"));
zona.addEventListener("drop", (e) => {
  e.preventDefault();
  zona.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) { input.files = e.dataTransfer.files; marcarArchivo(); }
});
input.addEventListener("change", marcarArchivo);

function marcarArchivo() {
  if (!input.files[0]) return;
  document.getElementById("label_ops").textContent = input.files[0].name;
  zona.classList.add("file-selected");
  btnImp.disabled = false;
}

btnImp.addEventListener("click", async () => {
  btnImp.disabled = true;
  const prog = document.getElementById("impProgress");
  const res = document.getElementById("impResultado");
  prog.classList.remove("hidden");
  res.classList.add("hidden");
  document.getElementById("impMsg").textContent = "Leyendo y guardando cajas…";
  let ancho = 0;
  const timer = setInterval(() => {
    ancho = Math.min(ancho + 4, 90);
    document.getElementById("impFill").style.width = ancho + "%";
  }, 200);

  const form = new FormData();
  form.append("file", input.files[0]);

  try {
    const r = await fetch("/api" + API + "/importar", { method: "POST", body: form });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || "Error del servidor");
    }
    mostrarImportacion(await r.json());
  } catch (err) {
    res.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> No se pudo importar</h3><p>${esc(err.message)}</p></div>`;
    res.classList.remove("hidden");
  } finally {
    clearInterval(timer);
    document.getElementById("impFill").style.width = "100%";
    setTimeout(() => prog.classList.add("hidden"), 400);
    btnImp.disabled = false;
  }
});

function mostrarImportacion(d) {
  const descuadres = (d.conciliacion || []).filter((c) => c.sin_venta || Number(c.dif_cajas) || Number(c.dif_tallos));

  let html = `<div class="result-box success">
    <h3><i class="ph ph-check-circle"></i> ${esc(d.archivo)}</h3>
    <div class="card-grid" style="margin:1rem 0;">
      <div class="summary-card"><span class="summary-card-value">${d.total_cajas}</span><span class="summary-card-label">Cajas</span></div>
      <div class="summary-card"><span class="summary-card-value">${d.total_tallos.toLocaleString("es-EC")}</span><span class="summary-card-label">Tallos</span></div>
      <div class="summary-card"><span class="summary-card-value">${d.facturas.length}</span><span class="summary-card-label">Pedidos</span></div>
      <div class="summary-card"><span class="summary-card-value">${d.awbs.length}</span><span class="summary-card-label">Guías madre</span></div>
    </div>
    <p><span class="badge badge-green">${d.insertadas}</span> cajas nuevas ·
       <span class="badge badge-blue">${d.actualizadas}</span> actualizadas ·
       <span class="badge ${d.cajas_sin_po ? "badge-orange" : "badge-gray"}">${d.cajas_sin_po}</span> sin PO</p>
    <p class="page-subtitle">Carriers en el archivo: ${d.carriers.map((c) => `<span class="badge badge-gray">${esc(c)}</span>`).join(" ")}</p>`;

  html += `<div class="result-alert ${descuadres.length ? "alert-warn" : "alert-info"}">
      <i class="ph ph-${descuadres.length ? "warning" : "check"}"></i>
      <strong>Conciliación contra Ventas:</strong>
      ${descuadres.length
        ? `${descuadres.length} de ${d.conciliacion.length} pedidos no cuadran.<ul>${descuadres
            .map((c) => `<li>${esc(c.destinatario_xml ?? c.destinatario ?? "")}: ${c.sin_venta ? "no existe en Ventas" : `${c.cajas_xml} vs ${c.cajas_dartis} cajas · ${c.tallos_xml} vs ${c.tallos_dartis} tallos`}</li>`)
            .join("")}</ul>`
        : `los ${d.conciliacion.length} pedidos cuadran en cajas y tallos.`}
    </div>`;

  html += avisosHtml(d.avisos) + `</div>`;

  const res = document.getElementById("impResultado");
  res.innerHTML = html;
  res.classList.remove("hidden");
}

// ── 2 · Generar ───────────────────────────────────────────────────────────────
document.getElementById("btnBuscar").addEventListener("click", async () => {
  const fecha = document.getElementById("genFecha").value;
  const params = new URLSearchParams();
  if (fecha) params.set("fecha", fecha);

  try {
    const d = await apiGet(`${API}/preview?${params}`);
    cajas = d.cajas;
    if (d.shipdate_sugerido && !fecha) document.getElementById("genFecha").value = d.shipdate_sugerido;
    document.getElementById("genAvisos").innerHTML = avisosHtml(d.avisos);
    pintarCajas();
  } catch (err) {
    document.getElementById("genAvisos").innerHTML =
      `<div class="result-alert alert-warn"><i class="ph ph-x-circle"></i> ${esc(err.message)}</div>`;
  }
});

function pintarCajas() {
  const cuerpo = document.getElementById("genCuerpo");

  if (!cajas.length) {
    cuerpo.innerHTML = `<tr><td colspan="9" class="il-empty">No hay cajas de Armellini para esa fecha.</td></tr>`;
    document.getElementById("genConteo").textContent = "";
    document.getElementById("btnGenerar").disabled = true;
    return;
  }

  cuerpo.innerHTML = cajas
    .map((c, i) => `<tr>
      <td><input type="checkbox" class="chk-caja" data-i="${i}" checked /></td>
      <td>${esc(c.codigo_pieza)}</td>
      <td>${esc(c.awb)}</td>
      <td>${esc(c.nombre_cliente)}</td>
      <td>${c.consignee_code ? esc(c.consignee_code) : '<span class="badge badge-red">falta</span>'}</td>
      <td>${esc(c.product_code)} · ${esc(c.descripcion_producto)}</td>
      <td>${c.largo_inch}×${c.ancho_inch}×${c.alto_inch}</td>
      <td>${c.invoice ? esc(c.invoice) : '<span class="badge badge-red">falta</span>'}</td>
      <td>${c.po
        ? esc(c.po)
        : `<input type="text" class="po-input" data-cp="${esc(c.codigo_pieza)}" placeholder="digitar PO" style="width:9rem" />`}</td>
    </tr>`)
    .join("");

  document.getElementById("genConteo").textContent = `${cajas.length} caja(s)`;
  document.getElementById("btnGenerar").disabled = false;

  cuerpo.querySelectorAll(".chk-caja").forEach((chk) =>
    chk.addEventListener("change", () => {
      const n = cuerpo.querySelectorAll(".chk-caja:checked").length;
      document.getElementById("genConteo").textContent = `${n} de ${cajas.length} caja(s)`;
      document.getElementById("btnGenerar").disabled = n === 0;
    }));
}

document.getElementById("chkTodos").addEventListener("change", (e) => {
  document.querySelectorAll(".chk-caja").forEach((c) => { c.checked = e.target.checked; });
  document.querySelectorAll(".chk-caja")[0]?.dispatchEvent(new Event("change"));
});

document.getElementById("btnGenerar").addEventListener("click", async () => {
  const seleccion = [...document.querySelectorAll(".chk-caja:checked")].map((c) => cajas[Number(c.dataset.i)]);
  const shipdate = document.getElementById("genFecha").value;

  if (!shipdate) {
    alert("Indica la fecha de salida (Shipdate).");
    return;
  }

  const pos = [...document.querySelectorAll(".po-input")]
    .filter((i) => i.value.trim() && seleccion.some((c) => c.codigo_pieza === i.dataset.cp))
    .map((i) => ({ codigo_pieza: i.dataset.cp, po: i.value.trim() }));

  const res = document.getElementById("genResultado");

  try {
    // El shipper no se envia: es un codigo fijo que resuelve el backend.
    const d = await apiPost(`${API}/generar`, {
      barcodes: seleccion.map((c) => c.codigo_pieza),
      shipdate,
      pos,
    });

    const url = URL.createObjectURL(new Blob([d.xml], { type: "application/xml" }));
    res.innerHTML = `<div class="result-box success">
        <h3><i class="ph ph-check-circle"></i> XML generado</h3>
        <p><strong>${esc(d.filename)}</strong> · ${d.total_cajas} caja(s) · registro #${d.export_id}</p>
        ${avisosHtml(d.avisos)}
        <div class="import-actions" style="justify-content:flex-start; gap:.75rem">
          <a class="btn btn-primary" href="${url}" download="${esc(d.filename)}"><i class="ph ph-download-simple"></i> Descargar</a>
          <button class="btn btn-secondary" id="btnCorreoGen" data-correo="${d.export_id}"><i class="ph ph-envelope-simple"></i> Enviar aviso por correo</button>
        </div>
        <pre style="max-height:18rem;overflow:auto;font-size:.78rem">${esc(d.xml.slice(0, 4000))}</pre>
      </div>`;
    res.classList.remove("hidden");

    const btnCorreo = document.getElementById("btnCorreoGen");
    btnCorreo.addEventListener("click", () => enviarCorreo(btnCorreo.dataset.correo, btnCorreo));
  } catch (err) {
    res.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> No se generó</h3><p>${esc(err.message)}</p></div>`;
    res.classList.remove("hidden");
  }
});

// ── Historial ─────────────────────────────────────────────────────────────────
async function cargarHistorial() {
  const cuerpo = document.getElementById("histCuerpo");
  try {
    const filas = await apiGet(`${API}/exports`);
    cuerpo.innerHTML = filas.length
      ? filas.map((f) => `<tr>
          <td>${new Date(f.created_at).toLocaleString("es-EC")}</td>
          <td>${esc(f.filename)}</td>
          <td>${esc(f.shipdate)}</td>
          <td>${f.total_cajas}</td>
          <td>${(f.awbs || []).map((a) => esc(a)).join("<br>")}</td>
          <td>${f.correo_enviado_at
            ? `<span class="badge badge-green" title="${esc((f.correo_destinatarios || []).join(", "))}">enviado</span>`
            : '<span class="badge badge-gray">no enviado</span>'}</td>
          <td>
            <button class="btn btn-link" data-descargar="${f.id}">Descargar</button>
            <button class="btn btn-link" data-correo="${f.id}">${f.correo_enviado_at ? "Reenviar" : "Enviar correo"}</button>
          </td>
        </tr>`).join("")
      : `<tr><td colspan="7" class="il-empty">Todavía no se ha generado ningún XML.</td></tr>`;

    cuerpo.querySelectorAll("button[data-descargar]").forEach((b) =>
      b.addEventListener("click", async () => {
        const d = await apiGet(`${API}/exports/${b.dataset.descargar}`);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([d.xml_content], { type: "application/xml" }));
        a.download = d.filename;
        a.click();
      }));

    cuerpo.querySelectorAll("button[data-correo]").forEach((b) =>
      b.addEventListener("click", () => enviarCorreo(b.dataset.correo, b)));
  } catch (err) {
    cuerpo.innerHTML = `<tr><td colspan="7" class="il-empty">${esc(err.message)}</td></tr>`;
  }
}

// Enviar es una accion hacia afuera: primero se muestra a quien va y que
// dice, y no se manda hasta que la persona lo confirma.
async function enviarCorreo(exportId, boton) {
  boton.disabled = true;
  try {
    const p = await apiGet(`${API}/exports/${exportId}/correo`);

    if (!p.configurado) {
      alert("El servidor no tiene configurada la cuenta de Gmail (GMAIL_USER y GMAIL_APP_PASSWORD).");
      return;
    }
    if (!p.destinatarios.length) {
      alert(`Sin correos configurados para: ${p.destinos_sin_correo.join(", ")}.\n\n` +
            "Agrégalos en la pestaña Consignees.");
      return;
    }

    const ok = confirm(
      `Se enviará desde ${p.remitente} a:\n\n${p.destinatarios.join("\n")}\n\n` +
      `Asunto: ${p.asunto}\n\n¿Enviar?`);
    if (!ok) return;

    const r = await apiPost(`${API}/exports/${exportId}/correo`, {});
    alert(`Correo enviado a ${r.destinatarios.length} destinatario(s).`);
    cargarHistorial();
  } catch (err) {
    alert(err.message);
  } finally {
    boton.disabled = false;
  }
}

// ── Consignees ────────────────────────────────────────────────────────────────
async function cargarConsignees() {
  const cuerpo = document.getElementById("conCuerpo");
  try {
    const filas = await apiGet(`${API}/consignees`);
    cuerpo.innerHTML = filas.length
      ? filas.map((f) => `<tr><td>${esc(f.destinatario)}</td><td><strong>${esc(f.consignee_code)}</strong></td>
          <td>${f.emails?.length
            ? f.emails.map((e) => esc(e)).join("<br>")
            : '<span class="badge badge-orange">sin correos</span>'}</td>
          <td style="text-align:right">${f.dias_entrega}</td>
          <td>${esc(f.descripcion ?? "")}</td></tr>`).join("")
      : `<tr><td colspan="5" class="il-empty">Sin códigos cargados.</td></tr>`;
  } catch (err) {
    cuerpo.innerHTML = `<tr><td colspan="5" class="il-empty">${esc(err.message)}</td></tr>`;
  }
}

document.getElementById("btnConsignee").addEventListener("click", async () => {
  const destinatario = document.getElementById("conDest").value.trim();
  const consignee_code = document.getElementById("conCode").value.trim();

  if (!destinatario || !consignee_code) {
    alert("Destinatario y código son obligatorios.");
    return;
  }

  try {
    await apiPost(`${API}/consignees`, {
      destinatario,
      consignee_code,
      descripcion: document.getElementById("conDesc").value.trim() || null,
      emails: document.getElementById("conMails").value
        .split(",").map((v) => v.trim()).filter(Boolean),
      dias_entrega: Number(document.getElementById("conDias").value) || 0,
    });
    document.getElementById("conDest").value = "";
    document.getElementById("conCode").value = "";
    document.getElementById("conDesc").value = "";
    document.getElementById("conMails").value = "";
    cargarConsignees();
  } catch (err) {
    alert(err.message);
  }
});
