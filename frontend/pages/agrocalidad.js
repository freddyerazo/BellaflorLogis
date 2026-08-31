/* ═══════════════════════════════════════════════════════════════════════
   AGROCALIDAD — Requisitos fitosanitarios por especie y país de destino.

   Consulta en vivo la API de Agrocalidad a través del backend: es síncrona
   (~3 s en vivo, ~1 s si reutiliza un resultado de las últimas 24 h), así que
   no hay cola ni polling. Antes esto encolaba una solicitud y sondeaba cada
   4 s a la espera de un worker en GitHub Actions.
   ═══════════════════════════════════════════════════════════════════════ */

import { apiGet, apiPost } from "/js/api.js";

let catalogo = { especies: [], paises: [], movimientos: [], areas: [] };
/* Países que Agrocalidad reconoce para la especie elegida. Se cruzan contra
   los de BLIS para no ofrecer destinos que van a devolver vacío. */
let paisesDisponibles = null;

/* ─── Utilidades ─────────────────────────────────────────────────────── */
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function llenarSelect(select, items, { value, label, placeholder }) {
  select.innerHTML = placeholder ? `<option value="">${esc(placeholder)}</option>` : "";
  for (const item of items) {
    const opt = document.createElement("option");
    opt.value = item[value];
    opt.textContent = item[label];
    select.appendChild(opt);
  }
}

/* ─── Carga inicial ──────────────────────────────────────────────────── */
async function initCatalogo() {
  catalogo = await apiGet("/agrocalidad/catalogo");

  llenarSelect(document.getElementById("species_id"), catalogo.especies, {
    value: "id", label: "name", placeholder: "Selecciona especie…",
  });
  llenarSelect(document.getElementById("trade_type"),
    catalogo.movimientos.map((m) => ({ v: m })), { value: "v", label: "v" });
  llenarSelect(document.getElementById("area_code"),
    catalogo.areas.map((a) => ({ v: a })), { value: "v", label: "v" });
  document.getElementById("trade_type").value = "Exportación";
  document.getElementById("area_code").value = "SV";

  llenarSelect(document.getElementById("filter_species"), catalogo.especies, {
    value: "id", label: "name", placeholder: "Todas",
  });
  llenarSelect(document.getElementById("filter_country"), catalogo.paises, {
    value: "id", label: "name_es", placeholder: "Todos",
  });

  initFormularioPais();

  const sinMapeo = catalogo.especies_sin_mapeo;
  document.getElementById("nota_especies").textContent = sinMapeo
    ? `${catalogo.especies.length} especies disponibles · ${sinMapeo} sin mapear en Agrocalidad`
    : `${catalogo.especies.length} especies disponibles`;
}

/* ─── Al elegir especie: acotar los destinos a los que sí tienen datos ── */
async function alCambiarEspecie() {
  const selPais = document.getElementById("country_id");
  const nota = document.getElementById("nota_paises");
  const especie = catalogo.especies.find(
    (e) => e.id === document.getElementById("species_id").value);

  paisesDisponibles = null;

  if (!especie) {
    selPais.disabled = true;
    selPais.innerHTML = `<option value="">Elige una especie primero…</option>`;
    nota.textContent = "";
    return;
  }

  selPais.disabled = true;
  selPais.innerHTML = `<option value="">Consultando destinos…</option>`;
  nota.textContent = "";

  const movimiento = document.getElementById("trade_type").value;

  try {
    const disponibles = await apiGet(
      `/agrocalidad/paises-disponibles/${especie.id_producto_agrocalidad}` +
      `?movimiento=${encodeURIComponent(movimiento)}`);

    paisesDisponibles = new Set(disponibles.map((p) => p.id_localizacion));
    const conDatos = catalogo.paises.filter(
      (p) => paisesDisponibles.has(p.id_localizacion_agrocalidad));

    if (!conDatos.length) {
      selPais.innerHTML = `<option value="">Sin destinos con requisitos publicados</option>`;
      nota.textContent = "Agrocalidad no publica requisitos de esta especie para ningún país del catálogo de BLIS.";
      return;
    }

    llenarSelect(selPais, conDatos, {
      value: "id", label: "name_es", placeholder: "Selecciona país…",
    });
    selPais.disabled = false;
    nota.textContent = `${conDatos.length} destinos con requisitos publicados` +
      (disponibles.length > conDatos.length
        ? ` (Agrocalidad lista ${disponibles.length}, el resto no está en BLIS)` : "");
  } catch (err) {
    /* Si falla el acotado, se ofrecen todos: es preferible a bloquear la pantalla. */
    llenarSelect(selPais, catalogo.paises, {
      value: "id", label: "name_es", placeholder: "Selecciona país…",
    });
    selPais.disabled = false;
    nota.textContent = `No se pudieron acotar los destinos (${err.message}). Se muestran todos.`;
  }
}

/* ─── Consulta ───────────────────────────────────────────────────────── */
document.getElementById("consultaForm").addEventListener("submit", (e) => {
  e.preventDefault();
  ejecutarConsulta(false);
});

async function ejecutarConsulta(forzar) {
  const btn = document.getElementById("btnConsultar");
  const seccion = document.getElementById("resultSection");

  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-circle-notch"></i> Consultando Agrocalidad…`;
  seccion.classList.remove("hidden");
  seccion.innerHTML = `<div class="ag-cargando"><span></span> Consultando en Agrocalidad…</div>`;

  try {
    const res = await apiPost(
      `/agrocalidad/consultar${forzar ? "?refrescar=true" : ""}`, {
        species_id: document.getElementById("species_id").value,
        country_id: document.getElementById("country_id").value,
        trade_type: document.getElementById("trade_type").value,
        area_code: document.getElementById("area_code").value,
      });
    mostrarResultado(res);
    cargarHistorial();
  } catch (err) {
    seccion.innerHTML = `<div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> No se pudo consultar</h3>
      <p>${esc(err.message)}</p></div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="ph ph-magnifying-glass"></i> Consultar`;
  }
}

function mostrarResultado(r) {
  const seccion = document.getElementById("resultSection");
  const reqs = r.requisitos || [];

  const ficha = `
    <table class="ag-ficha">
      <tr><th>Producto</th><td>${esc(r.matched_product_name || r.especie)}</td></tr>
      <tr><th>Nombre científico</th><td>${esc(r.scientific_name || "—")}</td></tr>
      <tr><th>Partida recomendada</th><td>${esc(r.tariff_heading || "—")}</td></tr>
      <tr><th>Código de Agrocalidad</th><td>${esc(r.agrocalidad_code || "—")}</td></tr>
    </table>`;

  const cuerpo = reqs.length
    ? reqs.map((q, i) => `
        <article class="ag-req">
          <header>
            <span class="ag-req-num">R${i + 1}</span>
            <h4>${esc(q.nombre)}</h4>
          </header>
          <pre class="ag-req-texto">${esc(q.requisito || "")}</pre>
          ${q.detalle_impreso ? `
            <p class="ag-req-impreso">
              <i class="ph ph-printer"></i>
              <span><strong>En el certificado impreso:</strong> ${esc(q.detalle_impreso)}</span>
            </p>` : ""}
        </article>`).join("")
    : `<p class="ag-vacio"><i class="ph ph-info"></i>
         Agrocalidad no tiene requisitos registrados para esta combinación.
         No significa que no se pueda exportar: puede que el destino no los
         tenga publicados.</p>`;

  seccion.innerHTML = `
    <div class="result-box ${reqs.length ? "success" : ""}">
      <h3>
        <i class="ph ph-${reqs.length ? "check-circle" : "info"}"></i>
        ${esc(r.especie)} → ${esc(r.pais)}
        <span class="badge ${reqs.length ? "badge-green" : "badge-gray"}">
          ${reqs.length} requisito${reqs.length === 1 ? "" : "s"}
        </span>
      </h3>
      ${avisoCache(r)}
      ${ficha}
      <div class="ag-reqs">${cuerpo}</div>
    </div>`;

  const btnRefrescar = document.getElementById("btnRefrescar");
  if (btnRefrescar) btnRefrescar.addEventListener("click", () => ejecutarConsulta(true));
}

/* Un resultado guardado hace menos de 24 h se reutiliza en vez de volver a
   pedírselo a Agrocalidad. Se avisa siempre, y se ofrece forzar la consulta:
   el usuario tiene que saber si está viendo dato fresco o guardado. */
function avisoCache(r) {
  if (!r.desde_cache) return "";
  const fecha = new Date(r.queried_at).toLocaleString("es-EC");
  return `
    <p class="ag-cache">
      <i class="ph ph-clock-counter-clockwise"></i>
      <span>Resultado guardado del <strong>${esc(fecha)}</strong>, no se volvió a
        consultar a Agrocalidad.</span>
      <button class="btn-link" id="btnRefrescar">Consultar de nuevo</button>
    </p>`;
}

/* ─── Historial ──────────────────────────────────────────────────────── */
async function cargarHistorial() {
  const params = new URLSearchParams();
  const esp = document.getElementById("filter_species").value;
  const pais = document.getElementById("filter_country").value;
  if (esp) params.set("species_id", esp);
  if (pais) params.set("country_id", pais);

  const tbody = document.getElementById("historyBody");
  tbody.innerHTML = `<tr><td colspan="8" class="loading">Cargando…</td></tr>`;

  try {
    const filas = await apiGet(`/agrocalidad/requisitos?${params.toString()}`);
    if (!filas.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty">Sin consultas registradas</td></tr>`;
      return;
    }
    tbody.innerHTML = filas.map((f) => {
      const n = (f.requisitos || []).length;
      return `
        <tr>
          <td>${esc(f.especie)}</td>
          <td>${esc(f.pais)}</td>
          <td>${esc(f.trade_type)}</td>
          <td class="num"><span class="badge ${n ? "badge-green" : "badge-gray"}">${n}</span></td>
          <td>${esc(f.tariff_heading || "—")}</td>
          <td>${esc(f.agrocalidad_code || "—")}</td>
          <td>${new Date(f.queried_at).toLocaleDateString("es-EC")}
            ${f.fuente === "scraping" ? `<span class="ag-sub">scraping</span>` : ""}</td>
          <td><button class="btn-link ag-ver" data-id="${f.requirement_id}">Ver</button></td>
        </tr>`;
    }).join("");

    tbody.querySelectorAll(".ag-ver").forEach((b) =>
      b.addEventListener("click", () => verGuardada(b.dataset.id)));
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="error">${esc(err.message)}</td></tr>`;
  }
}

async function verGuardada(id) {
  try {
    const r = await apiGet(`/agrocalidad/requisitos/${id}`);
    document.getElementById("resultSection").classList.remove("hidden");
    mostrarResultado(r);
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    alert(`No se pudo abrir la consulta: ${err.message}`);
  }
}

/* ─── Consulta por país: todo el catálogo contra un mismo destino ──────
   Equivalente al "Verificar catálogo completo para este país" del sitio de
   GitHub, pero sobre la API: allá cada especie tardaba 30-90 s con Playwright,
   acá ~3 s (y ~1 s si ya hay resultado guardado de las últimas 24 h).

   Se lanzan varias en paralelo pero con un tope bajo: es un servicio público
   de un organismo del Estado, no conviene saturarlo. Con 3 a la vez el
   catálogo completo tarda cerca de minuto y medio.
   ───────────────────────────────────────────────────────────────────── */

const CONCURRENCIA_PAIS = 3;
let cancelarPais = false;
let corriendoPais = false;

function initFormularioPais() {
  llenarSelect(document.getElementById("pais_country_id"), catalogo.paises, {
    value: "id", label: "name_es", placeholder: "Selecciona país…",
  });
  llenarSelect(document.getElementById("pais_trade_type"),
    catalogo.movimientos.map((m) => ({ v: m })), { value: "v", label: "v" });
  llenarSelect(document.getElementById("pais_area_code"),
    catalogo.areas.map((a) => ({ v: a })), { value: "v", label: "v" });
  document.getElementById("pais_trade_type").value = "Exportación";
  document.getElementById("pais_area_code").value = "SV";
  document.getElementById("pais_hint").textContent =
    `${catalogo.especies.length} especies del catálogo`;
}

function progresoPais(hechas, total, texto) {
  document.getElementById("paisProgresoFill").style.width =
    `${Math.round((hechas / total) * 100)}%`;
  document.getElementById("paisProgresoMsg").textContent =
    `${hechas} de ${total} · ${texto}`;
}

document.getElementById("paisForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (corriendoPais) return;

  const countryId = document.getElementById("pais_country_id").value;
  const pais = catalogo.paises.find((p) => p.id === countryId);
  const movimiento = document.getElementById("pais_trade_type").value;
  const area = document.getElementById("pais_area_code").value;
  const especies = catalogo.especies;

  /* Medido con concurrencia 3: ~1,9 s de reloj por especie en vivo (ese numero
     ya incluye el paralelismo, no hay que volver a dividir por la concurrencia).
     Las que salen de cache tardan ~0,4 s, asi que la estimacion es el techo. */
  const minutos = Math.max(1, Math.round(especies.length * 1.9 / 60));
  if (!confirm(
    `Se van a consultar las ${especies.length} especies del catálogo contra ` +
    `${pais.name_es} (${movimiento}, ${area}).\n\n` +
    `Cada consulta va en vivo a Agrocalidad; las que ya tengan resultado de las ` +
    `últimas 24 h se reutilizan y tardan mucho menos. La primera corrida completa ` +
    `toma alrededor de ${minutos} minuto(s) ` +
    `y necesita esta página abierta.\n\n¿Continuar?`)) return;

  corriendoPais = true;
  cancelarPais = false;
  const btn = document.getElementById("btnConsultarPais");
  const btnCancelar = document.getElementById("btnCancelarPais");
  btn.disabled = true;
  btn.innerHTML = `<i class="ph ph-circle-notch"></i> Consultando…`;
  btnCancelar.classList.remove("hidden");
  document.getElementById("paisProgreso").classList.remove("hidden");
  document.getElementById("paisResultado").classList.add("hidden");

  const filas = [];
  let hechas = 0;
  const cola = [...especies];

  async function trabajador() {
    while (cola.length && !cancelarPais) {
      const especie = cola.shift();
      try {
        const r = await apiPost("/agrocalidad/consultar", {
          species_id: especie.id, country_id: countryId,
          trade_type: movimiento, area_code: area,
        });
        filas.push({
          especie: especie.name,
          requisitos: (r.requisitos || []).length,
          partida: r.tariff_heading,
          codigo: r.agrocalidad_code,
          cache: r.desde_cache,
          error: null,
        });
      } catch (err) {
        filas.push({ especie: especie.name, requisitos: 0, error: err.message });
      }
      hechas += 1;
      progresoPais(hechas, especies.length, especie.name);
    }
  }

  await Promise.all(
    Array.from({ length: CONCURRENCIA_PAIS }, () => trabajador()));

  document.getElementById("paisProgreso").classList.add("hidden");
  btnCancelar.classList.add("hidden");
  btn.disabled = false;
  btn.innerHTML = `<i class="ph ph-list-magnifying-glass"></i> Consultar todo el catálogo`;
  corriendoPais = false;

  renderResultadoPais(pais, movimiento, area, filas, hechas, especies.length);
  cargarHistorial();
});

document.getElementById("btnCancelarPais").addEventListener("click", () => {
  cancelarPais = true;
  document.getElementById("paisProgresoMsg").textContent += " — cancelando…";
});

function renderResultadoPais(pais, movimiento, area, filas, hechas, total) {
  const seccion = document.getElementById("paisResultado");
  const conReq = filas.filter((f) => !f.error && f.requisitos > 0);
  const sinReq = filas.filter((f) => !f.error && f.requisitos === 0);
  const conError = filas.filter((f) => f.error);

  /* Solo se listan las que tienen requisitos: una especie sin requisitos
     publicados no aporta nada a la tabla y solo diluye lo accionable. El conteo
     de las que quedaron fuera sigue visible en el resumen de arriba.
     Los errores SI se muestran: no son "cero requisitos" sino consultas que
     fallaron, y ocultarlas haria pensar que el destino no exige nada. */
  const orden = [...conReq.sort((a, b) => b.requisitos - a.requisitos), ...conError];

  seccion.innerHTML = `
    <div class="result-box success">
      <h3>
        <i class="ph ph-globe-hemisphere-west"></i>
        ${esc(pais.name_es)} · ${esc(movimiento)} · ${esc(area)}
        ${hechas < total ? `<span class="badge badge-gray">cancelado en ${hechas}/${total}</span>` : ""}
      </h3>
      <p class="ag-resumen-pais">
        <strong>${conReq.length}</strong> especies con requisitos
        ${sinReq.length ? ` · ${sinReq.length} sin requisitos publicados (no se listan)` : ""}
        ${conError.length ? ` · <strong>${conError.length}</strong> con error` : ""}
      </p>
      ${orden.length ? `
      <div class="ag-tabla-scroll">
        <table class="cot-tabla">
          <thead>
            <tr><th>Especie</th><th class="num">Requisitos</th><th>Partida</th>
                <th>Código</th><th></th></tr>
          </thead>
          <tbody>
            ${orden.map((f) => `
              <tr>
                <td>${esc(f.especie)}</td>
                <td class="num">
                  ${f.error ? "—"
                    : `<span class="badge ${f.requisitos ? "badge-green" : "badge-gray"}">${f.requisitos}</span>`}
                </td>
                <td>${esc(f.partida || "—")}</td>
                <td>${esc(f.codigo || "—")}</td>
                <td class="ag-sub">${f.error ? esc(f.error) : (f.cache ? "guardado" : "")}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>` : `
      <p class="ag-vacio"><i class="ph ph-info"></i>
        Agrocalidad no publica requisitos de ninguna especie del catálogo para
        este destino, movimiento y área.</p>`}
    </div>`;
  seccion.classList.remove("hidden");
}

/* ─── Arranque ───────────────────────────────────────────────────────── */
document.getElementById("species_id").addEventListener("change", alCambiarEspecie);
document.getElementById("trade_type").addEventListener("change", alCambiarEspecie);
document.getElementById("filter_species").addEventListener("change", cargarHistorial);
document.getElementById("filter_country").addEventListener("change", cargarHistorial);

initCatalogo()
  .then(cargarHistorial)
  .catch((err) => {
    document.getElementById("content").innerHTML = `
      <div class="dashboard-error">
        <strong>No se pudo cargar el módulo Agrocalidad</strong>
        <p>${esc(err.message)}</p>
        <button class="btn btn-primary" onclick="location.reload()">Reintentar</button>
      </div>`;
  });
