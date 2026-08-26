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
