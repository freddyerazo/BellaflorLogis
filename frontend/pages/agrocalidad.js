import { apiGet, apiPost } from "/js/api.js";

const ESTADO_BADGE = {
  CON_REQUISITOS: "badge-green",
  SIN_REQUISITOS_REGISTRADOS: "badge-gray",
  NO_ENCONTRADO: "badge-red",
  ERROR: "badge-red",
  pending: "badge-blue",
  processing: "badge-blue",
  done: "badge-green",
  error: "badge-red",
};

let catalogo = { especies: [], paises: [] };
let pollTimer = null;

function fillSelect(select, items, { value, label, placeholder }) {
  select.innerHTML = "";
  if (placeholder) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    select.appendChild(opt);
  }
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item[value];
    opt.textContent = item[label];
    select.appendChild(opt);
  }
}

async function initCatalogo() {
  catalogo = await apiGet("/agrocalidad/catalogo");

  fillSelect(document.getElementById("species_id"), catalogo.especies, { value: "id", label: "name" });
  fillSelect(document.getElementById("country_id"), catalogo.paises, {
    value: "id",
    label: "name_es",
  });
  fillSelect(document.getElementById("trade_type"), catalogo.tipos.map(t => ({ v: t })), { value: "v", label: "v" });
  fillSelect(document.getElementById("area_code"), catalogo.areas.map(a => ({ v: a })), { value: "v", label: "v" });
  document.getElementById("trade_type").value = "Exportación";
  document.getElementById("area_code").value = "SV";

  fillSelect(document.getElementById("filter_species"), catalogo.especies, {
    value: "id", label: "name", placeholder: "Todas",
  });
  fillSelect(document.getElementById("filter_country"), catalogo.paises, {
    value: "id", label: "name_es", placeholder: "Todos",
  });
}

document.getElementById("consultaForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("btnConsultar");
  btn.disabled = true;
  clearInterval(pollTimer);

  const payload = {
    species_id: document.getElementById("species_id").value,
    country_id: document.getElementById("country_id").value,
    trade_type: document.getElementById("trade_type").value,
    area_code: document.getElementById("area_code").value,
  };

  showProgress();

  try {
    const solicitud = await apiPost("/agrocalidad/consultar", payload);
    pollSolicitud(solicitud.id);
  } catch (err) {
    hideProgress();
    showError(err.message);
    btn.disabled = false;
  }
});

function pollSolicitud(id) {
  pollTimer = setInterval(async () => {
    try {
      const solicitud = await apiGet(`/agrocalidad/solicitud/${id}`);
      if (solicitud.status === "done") {
        clearInterval(pollTimer);
        hideProgress();
        showResult(solicitud.requirement);
        document.getElementById("btnConsultar").disabled = false;
        cargarHistorial();
      } else if (solicitud.status === "error") {
        clearInterval(pollTimer);
        hideProgress();
        showError(solicitud.error_message || "La consulta terminó en error");
        document.getElementById("btnConsultar").disabled = false;
      }
      // pending / processing -> sigue esperando
    } catch (err) {
      clearInterval(pollTimer);
      hideProgress();
      showError(err.message);
      document.getElementById("btnConsultar").disabled = false;
    }
  }, 4000);
}

function showProgress() {
  document.getElementById("progressSection").classList.remove("hidden");
  document.getElementById("resultSection").classList.add("hidden");
  let w = 0;
  window._prog = setInterval(() => {
    w = Math.min(w + 1, 90);
    document.getElementById("progressFill").style.width = w + "%";
  }, 1000);
}

function hideProgress() {
  clearInterval(window._prog);
  const fill = document.getElementById("progressFill");
  fill.style.width = "100%";
  setTimeout(() => {
    document.getElementById("progressSection").classList.add("hidden");
    fill.style.width = "0%";
  }, 400);
}

function showResult(req) {
  const section = document.getElementById("resultSection");
  if (!req) {
    section.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> Sin resultado</h3></div>`;
    section.classList.remove("hidden");
    return;
  }
  const badge = ESTADO_BADGE[req.status] || "badge-gray";
  section.innerHTML = `
    <div class="result-box success">
      <h3><i class="ph ph-check-circle"></i> ${req.matched_product_name || "Consulta completada"}
        <span class="badge ${badge}">${req.status}</span>
      </h3>
      <p><strong>Nombre científico:</strong> ${req.scientific_name || "-"}</p>
      <p><strong>Partida arancelaria:</strong> ${req.tariff_heading || "-"}</p>
      <p><strong>Código Agrocalidad:</strong> ${req.agrocalidad_code || "-"}</p>
      <p><strong>Requisitos:</strong><br>${(req.requirements || "Sin requisitos registrados").replace(/\/\/\//g, "<br>")}</p>
    </div>`;
  section.classList.remove("hidden");
}

function showError(msg) {
  const section = document.getElementById("resultSection");
  section.innerHTML = `<div class="result-box error"><h3><i class="ph ph-x-circle"></i> Error</h3><p>${msg}</p></div>`;
  section.classList.remove("hidden");
}

async function cargarHistorial() {
  const speciesId = document.getElementById("filter_species").value;
  const countryId = document.getElementById("filter_country").value;
  const params = new URLSearchParams();
  if (speciesId) params.set("species_id", speciesId);
  if (countryId) params.set("country_id", countryId);

  const tbody = document.getElementById("historyBody");
  tbody.innerHTML = `<tr><td colspan="8" class="loading">Cargando...</td></tr>`;

  try {
    const rows = await apiGet(`/agrocalidad/requisitos?${params.toString()}`);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin consultas registradas</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.species_name}</td>
        <td>${r.country_name}</td>
        <td>${r.trade_type}</td>
        <td>${r.area_code}</td>
        <td><span class="badge ${ESTADO_BADGE[r.status] || "badge-gray"}">${r.status}</span></td>
        <td>${r.agrocalidad_code || "-"}</td>
        <td>${r.tariff_heading || "-"}</td>
        <td>${new Date(r.queried_at).toLocaleDateString("es-EC")}</td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="error">${err.message}</td></tr>`;
  }
}

document.getElementById("filter_species").addEventListener("change", cargarHistorial);
document.getElementById("filter_country").addEventListener("change", cargarHistorial);

initCatalogo().then(cargarHistorial);
