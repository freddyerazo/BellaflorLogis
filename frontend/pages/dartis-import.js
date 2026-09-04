const API = "/api/dartis/upload";

// ── Drag & drop + selección ───────────────────────────────────────────────────
document.querySelectorAll(".file-drop").forEach(zone => {
  const inputId = zone.dataset.target;
  const input   = document.getElementById(inputId);
  const label   = document.getElementById("label_" + inputId.replace("file_", ""));

  zone.addEventListener("click", () => input.click());

  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer.files[0]) {
      input.files = e.dataTransfer.files;
      updateLabel(label, zone, e.dataTransfer.files[0].name);
      checkReady();
    }
  });

  input.addEventListener("change", () => {
    if (input.files[0]) {
      updateLabel(label, zone, input.files[0].name);
      checkReady();
    }
  });
});

function updateLabel(label, zone, name) {
  label.textContent = name;
  zone.classList.add("file-selected");
}

function checkReady() {
  const r = document.getElementById("file_recetas").files[0];
  const v = document.getElementById("file_ventas").files[0];
  document.getElementById("btnUpload").disabled = !(r && v);
}

// ── Submit ────────────────────────────────────────────────────────────────────
document.getElementById("importForm").addEventListener("submit", async e => {
  e.preventDefault();

  const btn = document.getElementById("btnUpload");
  btn.disabled = true;

  showProgress("Enviando archivos...");

  const form = new FormData();
  form.append("file_recetas", document.getElementById("file_recetas").files[0]);
  form.append("file_ventas",  document.getElementById("file_ventas").files[0]);

  try {
    const res = await fetch(API, { method: "POST", body: form });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Error en el servidor");
    }

    const data = await res.json();
    hideProgress();
    showResult(data);
  } catch (err) {
    hideProgress();
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});

// ── UI helpers ────────────────────────────────────────────────────────────────
function showProgress(msg) {
  document.getElementById("progressSection").classList.remove("hidden");
  document.getElementById("resultSection").classList.add("hidden");
  document.getElementById("progressMsg").textContent = msg;
  let w = 0;
  window._prog = setInterval(() => {
    w = Math.min(w + 3, 90);
    document.getElementById("progressFill").style.width = w + "%";
  }, 200);
}

function hideProgress() {
  clearInterval(window._prog);
  document.getElementById("progressFill").style.width = "100%";
  setTimeout(() => document.getElementById("progressSection").classList.add("hidden"), 400);
}

function showResult(data) {
  const r = data.recetas;
  const v = data.ventas;

  const agNuevas = [...(r.agencias_nuevas || []), ...(v.agencias_nuevas || [])];
  const sinFinca = r.postcosechas_sin_finca || [];

  let html = `
    <div class="result-box success">
      <h3><i class="ph ph-check-circle"></i> Importación completada</h3>

      <div class="result-cols">
        <div class="result-col">
          <h4><i class="ph ph-file-xls"></i> Ventas Recetas</h4>
          <p><span class="badge badge-green">${r.insertados_o_actualizados}</span> registros importados</p>
          <p><span class="badge badge-blue">${r.clientes_vinculados}</span> clientes vinculados</p>
          ${r.clientes_nuevos ? `<p><span class="badge badge-orange">${r.clientes_nuevos}</span> clientes nuevos creados</p>` : ""}
          ${r.inactivados ? `<p><span class="badge badge-orange">${r.inactivados}</span> registros inactivados (ya no están en el archivo)</p>` : ""}
          ${r.errores ? `<p><span class="badge badge-red">${r.errores}</span> errores</p>` : ""}
        </div>
        <div class="result-col">
          <h4><i class="ph ph-file-xls"></i> Ventas</h4>
          <p><span class="badge badge-blue">${v.actualizadas}</span> registros enriquecidos</p>
          ${v.errores ? `<p><span class="badge badge-red">${v.errores}</span> errores</p>` : ""}
        </div>
      </div>`;

  if (agNuevas.length) {
    html += `<div class="result-alert alert-info">
      <i class="ph ph-truck"></i> <strong>${agNuevas.length} agencia(s) nueva(s) agregada(s):</strong>
      <ul>${agNuevas.map(a => `<li>${a}</li>`).join("")}</ul>
    </div>`;
  }

  if (sinFinca.length) {
    html += `<div class="result-alert alert-warn">
      <i class="ph ph-warning"></i> <strong>Postcosechas sin finca asignada (revisar en farm_postcosecha):</strong>
      <ul>${sinFinca.map(p => `<li>${p}</li>`).join("")}</ul>
    </div>`;
  }

  html += `</div>`;

  const section = document.getElementById("resultSection");
  section.innerHTML = html;
  section.classList.remove("hidden");
}

function showError(msg) {
  const section = document.getElementById("resultSection");
  section.innerHTML = `
    <div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> Error al importar</h3>
      <p>${msg}</p>
    </div>`;
  section.classList.remove("hidden");
}

/* ─── Registro VUE ────────────────────────────────────────────────────────
   El archivo "Lista de Producto.xls" se descarga de la Ventanilla Única y es
   POR RUC: se sube uno por cada empresa que exporta. Cada carga actualiza y
   agrega, nunca borra — un archivo parcial no prueba que una autorización se
   haya revocado.

   El manejador genérico de .file-drop de más arriba ya cubre esta zona; acá
   solo va lo propio: habilitar el botón, enviar y mostrar el estado.
   ───────────────────────────────────────────────────────────────────────── */

const escVue = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function vueListo() {
  document.getElementById("btnVue").disabled =
    !(document.getElementById("file_vue").files[0] &&
      document.getElementById("vue_empresa").value);
}
document.getElementById("file_vue").addEventListener("change", vueListo);
document.getElementById("vue_empresa").addEventListener("change", vueListo);
document.getElementById("drop_vue").addEventListener("drop", () => setTimeout(vueListo, 0));

document.getElementById("vueForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btnVue");
  const prog = document.getElementById("vueProgreso");
  const res = document.getElementById("vueResultado");

  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-circle-notch"></i> Importando…`;
  prog.classList.remove("hidden");
  document.getElementById("vueFill").style.width = "60%";
  res.classList.add("hidden");

  const form = new FormData();
  form.append("file", document.getElementById("file_vue").files[0]);
  form.append("empresa", document.getElementById("vue_empresa").value);

  try {
    const r = await fetch("/api/vue/upload", { method: "POST", body: form });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);

    document.getElementById("vueFill").style.width = "100%";
    res.innerHTML = `
      <div class="result-box success">
        <h3><i class="ph ph-check-circle"></i> Registro VUE importado</h3>
        <table class="ag-ficha">
          <tr><th>RUC del archivo</th><td>${escVue(d.rucs.join(", "))}</td></tr>
          <tr><th>Autorizaciones</th><td>${d.autorizaciones_unicas}</td></tr>
          <tr><th>Nuevas</th><td>${d.nuevas}</td></tr>
          <tr><th>Actualizadas</th><td>${d.actualizadas}</td></tr>
        </table>
        ${d.paises_sin_equivalencia?.length ? `
          <p class="ag-vacio"><i class="ph ph-warning"></i>
            Países del archivo sin equivalencia en el catálogo:
            <strong>${escVue(d.paises_sin_equivalencia.join(", "))}</strong>.
            Esas autorizaciones se guardaron igual, pero no se van a poder cruzar
            hasta resolver el país.</p>` : ""}
      </div>`;
    res.classList.remove("hidden");
    cargarRegistrosVue();
  } catch (err) {
    res.innerHTML = `<div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> No se pudo importar</h3>
      <p>${escVue(err.message)}</p></div>`;
    res.classList.remove("hidden");
  } finally {
    prog.classList.add("hidden");
    document.getElementById("vueFill").style.width = "0%";
    btn.disabled = false;
    btn.innerHTML = `<i class="ph ph-upload-simple"></i> Importar registro VUE`;
  }
});

async function cargarRegistrosVue() {
  const caja = document.getElementById("vueRegistros");
  try {
    const r = await fetch("/api/vue/registros");
    const d = await r.json();
    const registros = d.registros || [];
    const ventas = d.empresas_ventas || [];

    /* El selector se llena con las empresas EXACTAS de Dartis: ese texto es la
       llave que enlaza el registro VUE con los despachos, asi que no puede ser
       un nombre escrito a mano. */
    const sel = document.getElementById("vue_empresa");
    const elegido = sel.value;
    sel.innerHTML = `<option value="">Selecciona la empresa…</option>` +
      ventas.map((e) => `<option value="${escVue(e.empresa)}">${escVue(e.empresa)}</option>`).join("");
    sel.value = elegido;

    /* Que empresas exportan pero todavia no tienen registro VUE cargado. Es el
       dato que dice cuanto de la verificacion queda sin poder hacerse. */
    const conRegistro = registros.length;
    const conVue = new Set(registros.map((r2) => r2.empresa));
    const faltantes = ventas.filter((v) => !conVue.has(v.empresa));

    caja.innerHTML = `
      <h4 class="vue-titulo">Registros cargados</h4>
      ${registros.length ? `
        <table class="cot-tabla">
          <thead><tr>
            <th>RUC</th><th>Empresa</th><th class="num">Autorizaciones</th>
            <th class="num">Productos</th><th class="num">Países</th><th>Actualizado</th>
          </tr></thead>
          <tbody>
            ${registros.map((r2) => `
              <tr>
                <td>${escVue(r2.ruc)}</td>
                <td><b>${escVue(r2.empresa || "—")}</b></td>
                <td class="num">${r2.autorizaciones}</td>
                <td class="num">${r2.productos}</td>
                <td class="num">${r2.paises}</td>
                <td>${new Date(r2.actualizado_at).toLocaleString("es-EC")}</td>
              </tr>`).join("")}
          </tbody>
        </table>` : `<p class="ag-vacio">Todavía no hay ningún registro VUE cargado.</p>`}

      ${faltantes.length ? `
        <p class="ag-pendiente-inline">
          <i class="ph ph-warning-circle"></i>
          ${faltantes.length} empresa${faltantes.length === 1 ? "" : "s"} exporta${faltantes.length === 1 ? "" : "n"}
          según Dartis pero no tiene${faltantes.length === 1 ? "" : "n"} registro VUE cargado:
          <strong>${faltantes.map((f) => escVue(f.empresa)).join(", ")}</strong>.
          Sus despachos no se van a poder verificar contra la VUE.
        </p>` : ""}`;
  } catch (err) {
    caja.innerHTML = `<p class="ag-vacio">No se pudieron cargar los registros: ${escVue(err.message)}</p>`;
  }
}

cargarRegistrosVue();
