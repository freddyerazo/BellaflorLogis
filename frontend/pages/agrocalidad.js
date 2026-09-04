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
      /* n_requisitos viene de la vista y cubre tambien las filas del scraping
         viejo, que tienen los requisitos en texto plano y 0 items. */
      const n = f.n_requisitos ?? (f.requisitos || []).length;
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

/* ─── Navegación por pestañas ─────────────────────────────────────────── */
document.querySelectorAll(".subtab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".subtab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".subpanel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`panel-${tab.dataset.tab}`).classList.add("active");
    if (tab.dataset.tab === "comparacion") {
      cargarVerificacion(false);
      cargarComparacion(false);
    }
  });
});

/* ─── Agrocalidad vs Ventas vs VUE ────────────────────────────────────────
   Cruza cada combinación especie+país realmente exportada contra los
   requisitos de Agrocalidad. Es por especie Y país porque los requisitos
   dependen de ambos: los de rosa a Estados Unidos no son los de rosa a Rusia.

   VUE todavía no tiene datos cargados; la pantalla lo dice en vez de aparentar
   una comparación completa.
   ───────────────────────────────────────────────────────────────────────── */

let comparacion = null;
let cancelarPendientes = false;

const $dinero = (v) =>
  "$" + new Intl.NumberFormat("es-EC", { maximumFractionDigits: 0 }).format(v || 0);
const $num = (v) => new Intl.NumberFormat("es-EC").format(v || 0);

/* Estado de una combinación: es lo que ordena toda la pantalla. */
function estadoDe(c) {
  if (!c.id_producto_agrocalidad) return "sin_mapeo";
  if (c.n_requisitos === null || c.n_requisitos === undefined) return "sin_consultar";
  if (c.n_requisitos === 0) return "sin_requisitos";
  return "con_requisitos";
}

const ETIQUETA_VUE = {
  autorizado:    { txt: "autorizado", clase: "badge-green" },
  no_autorizado: { txt: "NO autorizado", clase: "badge-red" },
  sin_registro:  { txt: "sin registro VUE", clase: "badge-gray" },
  sin_datos:     { txt: "falta consultar", clase: "badge-gray" },
};

const ETIQUETA = {
  con_requisitos: { txt: "con requisitos", clase: "badge-green" },
  sin_consultar: { txt: "sin consultar", clase: "badge-amber" },
  sin_mapeo: { txt: "sin mapeo", clase: "badge-red" },
  sin_requisitos: { txt: "sin requisitos publicados", clase: "badge-gray" },
};

async function cargarComparacion(forzar) {
  if (comparacion && !forzar) return;
  const caja = document.getElementById("compEstado");
  caja.innerHTML = `<div class="ag-cargando"><span></span> Cruzando ventas contra Agrocalidad…</div>`;
  try {
    comparacion = await apiGet("/agrocalidad/comparacion");
    renderComparacion();
  } catch (err) {
    caja.innerHTML = `<div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> No se pudo cargar</h3>
      <p>${esc(err.message)}</p></div>`;
  }
}

function renderComparacion() {
  const d = comparacion;
  const combos = d.combinaciones || [];
  const por = (e) => combos.filter((c) => estadoDe(c) === e);
  const suma = (arr) => arr.reduce((a, c) => a + Number(c.dolares || 0), 0);

  const conReq = por("con_requisitos");
  const sinCon = por("sin_consultar");
  const sinMap = por("sin_mapeo");
  const sinReq = por("sin_requisitos");

  /* Lo que queda fuera del cruce. Se dice explícito: una cobertura calculada
     sobre la mitad de las ventas, presentada como si fuera del total, engaña. */
  const sp = d.sin_pais || {};
  const avisos = [];
  if (sp.lineas) {
    avisos.push(`<li><strong>${$num(sp.lineas)} líneas (${$dinero(sp.dolares)})
      quedan fuera del cruce</strong> porque no tienen país: se importaron con
      archivos anteriores a que Dartis agregara la columna <code>paisVenta</code>
      (${esc(sp.desde)} a ${esc(sp.hasta)}). Para incluirlas hay que re-importar
      esos meses con el formato nuevo.</li>`);
  }
  if (!d.pendientes.vue) {
    avisos.push(`<li><strong>VUE no tiene datos cargados.</strong> Falta definir
      el archivo de la Ventanilla Única y su importador; hasta entonces la
      comparación es Agrocalidad contra Ventas.</li>`);
  }

  document.getElementById("compEstado").innerHTML = `
    ${avisos.length ? `
      <div class="ag-pendiente">
        <h4><i class="ph ph-warning-circle"></i> Alcance de esta comparación</h4>
        <ul>${avisos.join("")}</ul>
      </div>` : ""}

    <p class="ag-rango">
      Ventas cruzadas del <strong>${esc(d.rango?.desde || "—")}</strong> al
      <strong>${esc(d.rango?.hasta || "—")}</strong> · ${combos.length} combinaciones especie+país
    </p>

    <div class="comp-tarjetas">
      ${tarjeta(conReq.length, "con requisitos averiguados", suma(conReq), "")}
      ${tarjeta(sinCon.length, "sin consultar", suma(sinCon), sinCon.length ? "comp-tarjeta--aviso" : "")}
      ${tarjeta(sinMap.length, "sin mapeo en Agrocalidad", suma(sinMap), sinMap.length ? "comp-tarjeta--alerta" : "")}
      ${tarjeta(sinReq.length, "sin requisitos publicados", suma(sinReq), "")}
    </div>

    ${sinCon.length ? `
      <div class="comp-accion">
        <button class="btn btn-primary" id="btnConsultarPendientes">
          <i class="ph ph-list-magnifying-glass"></i>
          Consultar las ${sinCon.length} pendientes
        </button>
        <button class="btn btn-secondary hidden" id="btnCancelarPendientes">
          <i class="ph ph-x"></i> Cancelar
        </button>
        <span class="ag-hint" id="pendHint"></span>
      </div>
      <div id="pendProgreso" class="hidden">
        <div class="progress-bar"><div id="pendFill" class="progress-fill"></div></div>
        <p class="progress-msg" id="pendMsg"></p>
      </div>` : ""}

    <div class="comp-filtros">
      <label><input type="checkbox" class="comp-filtro" value="con_requisitos" checked> con requisitos</label>
      <label><input type="checkbox" class="comp-filtro" value="sin_consultar" checked> sin consultar</label>
      <label><input type="checkbox" class="comp-filtro" value="sin_mapeo" checked> sin mapeo</label>
      <label><input type="checkbox" class="comp-filtro" value="sin_requisitos"> sin requisitos publicados</label>
    </div>

    <div class="ag-tabla-scroll">
      <table class="cot-tabla" id="tablaComparacion">
        <thead>
          <tr>
            <th>Especie</th><th>País</th>
            <th class="num">Facturado</th><th class="num">Tallos</th>
            <th>Agrocalidad</th><th class="num">Requisitos</th><th></th>
          </tr>
        </thead>
        <tbody id="compFilas"></tbody>
      </table>
    </div>`;

  document.querySelectorAll(".comp-filtro").forEach((ch) =>
    ch.addEventListener("change", pintarFilas));
  const btn = document.getElementById("btnConsultarPendientes");
  if (btn) btn.addEventListener("click", () => consultarPendientes(sinCon));
  const btnC = document.getElementById("btnCancelarPendientes");
  if (btnC) btnC.addEventListener("click", () => { cancelarPendientes = true; });

  pintarFilas();
}

function tarjeta(n, etiqueta, usd, clase) {
  return `
    <div class="comp-tarjeta ${clase}">
      <span class="comp-num">${n}</span>
      <span class="comp-lbl">${etiqueta}</span>
      <span class="comp-usd">${$dinero(usd)}</span>
    </div>`;
}

function pintarFilas() {
  const activos = new Set(
    [...document.querySelectorAll(".comp-filtro:checked")].map((c) => c.value));
  const filas = (comparacion.combinaciones || []).filter((c) => activos.has(estadoDe(c)));
  const tbody = document.getElementById("compFilas");

  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">Nada que mostrar con estos filtros</td></tr>`;
    return;
  }

  tbody.innerHTML = filas.map((c) => {
    const e = estadoDe(c);
    const et = ETIQUETA[e];
    return `
      <tr>
        <td><b>${esc(c.especie)}</b></td>
        <td>${esc(c.pais)}</td>
        <td class="num">${$dinero(c.dolares)}</td>
        <td class="num">${$num(c.tallos)}</td>
        <td><span class="badge ${et.clase}">${et.txt}</span></td>
        <td class="num">${c.n_requisitos ?? "—"}</td>
        <td class="cot-acciones">
          ${c.requirement_id
            ? `<button class="btn-link comp-ver" data-id="${c.requirement_id}">Ver</button>`
            : (c.id_producto_agrocalidad
                ? `<button class="btn-link comp-consultar" data-esp="${c.species_id}" data-pais="${c.country_id}">Consultar</button>`
                : "")}
        </td>
      </tr>`;
  }).join("");

  tbody.querySelectorAll(".comp-ver").forEach((b) =>
    b.addEventListener("click", () => verGuardada(b.dataset.id)));
  tbody.querySelectorAll(".comp-consultar").forEach((b) =>
    b.addEventListener("click", () => consultarUna(b)));
}

async function consultarUna(boton) {
  boton.disabled = true;
  boton.textContent = "…";
  try {
    await apiPost("/agrocalidad/consultar", {
      species_id: boton.dataset.esp, country_id: boton.dataset.pais,
      trade_type: "Exportación", area_code: "SV",
    });
    await cargarVerificacion(true);
    await cargarComparacion(true);
  } catch (err) {
    boton.disabled = false;
    boton.textContent = "Consultar";
    alert(`No se pudo consultar: ${err.message}`);
  }
}

/* Consulta en tanda las combinaciones que faltan. Concurrencia baja: es un
   servicio público de un organismo del Estado. Medido: ~1,9 s de reloj por
   consulta con 3 en paralelo. */
const CONCURRENCIA_PEND = 3;

async function consultarPendientes(pendientes) {
  const minutos = Math.max(1, Math.round(pendientes.length * 1.9 / 60));
  if (!confirm(
    `Se van a consultar ${pendientes.length} combinaciones especie+país contra ` +
    `Agrocalidad.\n\nTarda alrededor de ${minutos} minuto(s) y necesita esta ` +
    `página abierta. ¿Continuar?`)) return;

  cancelarPendientes = false;
  const btn = document.getElementById("btnConsultarPendientes");
  const btnC = document.getElementById("btnCancelarPendientes");
  btn.disabled = true;
  btnC.classList.remove("hidden");
  document.getElementById("pendProgreso").classList.remove("hidden");

  const cola = [...pendientes];
  let hechas = 0, errores = 0;

  async function trabajador() {
    while (cola.length && !cancelarPendientes) {
      const c = cola.shift();
      try {
        await apiPost("/agrocalidad/consultar", {
          species_id: c.species_id, country_id: c.country_id,
          trade_type: "Exportación", area_code: "SV",
        });
      } catch (err) {
        errores += 1;
      }
      hechas += 1;
      document.getElementById("pendFill").style.width =
        `${Math.round((hechas / pendientes.length) * 100)}%`;
      document.getElementById("pendMsg").textContent =
        `${hechas} de ${pendientes.length} · ${c.especie} → ${c.pais}` +
        (errores ? ` · ${errores} con error` : "");
    }
  }

  await Promise.all(Array.from({ length: CONCURRENCIA_PEND }, () => trabajador()));

  document.getElementById("pendProgreso")?.classList.add("hidden");
  await cargarVerificacion(true);
  await cargarComparacion(true);
  cargarHistorial();
}

/* ─── Verificación diaria: lo que se despacha vs lo verificado ─────────────
   Ventana hoy ±N días, que es el horizonte de quien despacha. Por cada
   combinación fecha + país + especie que sale en ese rango se contrasta contra
   lo verificado en Agrocalidad, y lo que no cuadra salta como alerta.

   Sobre el grano, que conviene tener presente al leerlo: Dartis registra la
   variedad comercial (AKITO, PLAYA BLANCA, BRIGHTON) pero Agrocalidad no
   regula por variedad — su catálogo llega a especie. De 234 variedades de
   Dartis solo 8 existen como producto en Agrocalidad, y son follajes, no
   cultivares. Así que la verificación se resuelve a nivel especie+país y la
   variedad se muestra como detalle del despacho.
   ───────────────────────────────────────────────────────────────────────── */

let verificacion = null;
let diasVentana = 5;

async function cargarVerificacion(forzar) {
  if (verificacion && !forzar) return;
  const caja = document.getElementById("verifEstado");
  caja.innerHTML = `<div class="ag-cargando"><span></span> Verificando los despachos de la ventana…</div>`;
  try {
    verificacion = await apiGet(`/agrocalidad/verificacion?dias=${diasVentana}`);
    renderVerificacion();
  } catch (err) {
    caja.innerHTML = `<div class="result-box error">
      <h3><i class="ph ph-x-circle"></i> No se pudo verificar</h3>
      <p>${esc(err.message)}</p></div>`;
  }
}

function renderVerificacion() {
  const d = verificacion;
  const filas = d.filas || [];
  const alertas = filas.filter((f) => f.alerta);
  const usdAlerta = alertas.reduce((a, f) => a + Number(f.dolares || 0), 0);
  const nAgro = filas.filter((f) => f.alerta_agrocalidad).length;
  const nVue = filas.filter((f) => f.alerta_vue).length;

  /* Alertas agrupadas por día: es como lo mira quien despacha. */
  const porDia = {};
  for (const f of filas) {
    porDia[f.fecha] ??= { fecha: f.fecha, total: 0, alertas: 0, usd: 0 };
    porDia[f.fecha].total += 1;
    if (f.alerta) {
      porDia[f.fecha].alertas += 1;
      porDia[f.fecha].usd += Number(f.dolares || 0);
    }
  }
  const dias = Object.values(porDia).sort((a, b) => a.fecha.localeCompare(b.fecha));
  const hoy = d.ventana.hoy;

  document.getElementById("verifEstado").innerHTML = `
    <div class="verif-cabecera">
      <label class="verif-dias">
        Ventana ±
        <select id="verifDias">
          ${[3, 5, 7, 10, 15].map((n) =>
            `<option value="${n}"${n === diasVentana ? " selected" : ""}>${n}</option>`).join("")}
        </select>
        días desde hoy (${esc(hoy)})
      </label>
      <button class="btn btn-secondary" id="btnRecargarVerif">
        <i class="ph ph-arrows-clockwise"></i> Actualizar
      </button>
    </div>

    ${alertas.length ? `
      <div class="verif-alerta">
        <i class="ph ph-warning"></i>
        <div>
          <strong>${alertas.length} despacho${alertas.length === 1 ? "" : "s"} con diferencias</strong>
          <p>
            ${nAgro ? `<b>${nAgro}</b> sin los requisitos de Agrocalidad averiguados. ` : ""}
            ${nVue ? `<b>${nVue}</b> <span class="txt-alerta">no autorizados en la VUE</span>. ` : ""}
            ${$dinero(usdAlerta)} en juego, saliendo en esta ventana.
          </p>
        </div>
        ${alertas.some((a) => a.id_producto_agrocalidad) ? `
          <button class="btn btn-primary" id="btnResolverAlertas">
            <i class="ph ph-list-magnifying-glass"></i>
            Consultar las ${alertas.filter((a) => a.id_producto_agrocalidad).length} consultables
          </button>` : ""}
      </div>` : `
      <div class="verif-ok">
        <i class="ph ph-check-circle"></i>
        <div><strong>Sin diferencias.</strong>
          <p>Todo lo que sale en esta ventana tiene requisitos verificados en Agrocalidad.</p></div>
      </div>`}

    <div class="verif-dias-grid">
      ${dias.map((x) => `
        <div class="verif-dia ${x.alertas ? "verif-dia--alerta" : ""} ${x.fecha === hoy ? "verif-dia--hoy" : ""}">
          <span class="verif-fecha">${esc(x.fecha)}${x.fecha === hoy ? " · hoy" : ""}</span>
          <span class="verif-n">${x.alertas}</span>
          <span class="verif-lbl">${x.alertas ? "alertas" : "sin alertas"} · ${x.total} combinaciones</span>
        </div>`).join("")}
    </div>

    <div class="comp-filtros">
      <label><input type="checkbox" id="soloAlertas" checked> Ver solo las alertas</label>
    </div>

    <div class="ag-tabla-scroll">
      <table class="cot-tabla">
        <thead>
          <tr>
            <th>Fecha</th><th>Empresa</th><th>País</th><th>Especie</th><th>Variedades</th>
            <th class="num">Facturado</th>
            <th>Agrocalidad</th><th>VUE</th><th></th>
          </tr>
        </thead>
        <tbody id="verifFilas"></tbody>
      </table>
    </div>`;

  document.getElementById("verifDias").addEventListener("change", (e) => {
    diasVentana = Number(e.target.value);
    cargarVerificacion(true);
  });
  document.getElementById("btnRecargarVerif")
    .addEventListener("click", () => cargarVerificacion(true));
  document.getElementById("soloAlertas")
    .addEventListener("change", pintarVerifFilas);
  const btnRes = document.getElementById("btnResolverAlertas");
  if (btnRes) btnRes.addEventListener("click", () =>
    consultarPendientes(alertas.filter((a) => a.id_producto_agrocalidad)));

  pintarVerifFilas();
}

function pintarVerifFilas() {
  const solo = document.getElementById("soloAlertas")?.checked;
  const filas = (verificacion.filas || []).filter((f) => !solo || f.alerta);
  const tbody = document.getElementById("verifFilas");

  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="9" class="empty">Nada que mostrar</td></tr>`;
    return;
  }

  tbody.innerHTML = filas.map((f, i) => {
    const vs = f.variedades || [];
    const estado = !f.id_producto_agrocalidad ? "sin_mapeo"
      : (f.alerta ? "sin_consultar" : "con_requisitos");
    const et = ETIQUETA[estado];
    const ev = ETIQUETA_VUE[f.vue_estado] || ETIQUETA_VUE.sin_datos;
    /* Un bouquet puede traer 125 variedades: se muestran las primeras y el
       resto se despliega, para que la fila siga siendo legible. */
    const visibles = vs.slice(0, 4).map(esc).join(", ");
    const resto = vs.length > 4
      ? ` <button class="btn-link verif-mas" data-i="${i}">+${vs.length - 4}</button>` : "";
    return `
      <tr>
        <td>${esc(f.fecha)}</td>
        <td class="ag-sub">${esc(String(f.empresa || "").replace(" CIA. LTDA.", "").replace(" CIA LTDA", ""))}</td>
        <td>${esc(f.pais)}</td>
        <td><b>${esc(f.especie)}</b></td>
        <td class="verif-vars">
          <span id="vars-${i}">${visibles}${resto}</span>
          <span class="ag-sub">${vs.length} variedad${vs.length === 1 ? "" : "es"} · ${$num(f.tallos)} tallos</span>
        </td>
        <td class="num">${$dinero(f.dolares)}</td>
        <td><span class="badge ${et.clase}">${et.txt}</span></td>
        <td><span class="badge ${ev.clase}">${ev.txt}</span></td>
        <td class="cot-acciones">
          ${f.requirement_id
            ? `<button class="btn-link comp-ver" data-id="${f.requirement_id}">Ver</button>`
            : (f.id_producto_agrocalidad
                ? `<button class="btn-link comp-consultar" data-esp="${f.species_id}" data-pais="${f.country_id}">Consultar</button>`
                : "")}
        </td>
      </tr>`;
  }).join("");

  tbody.querySelectorAll(".verif-mas").forEach((b) =>
    b.addEventListener("click", () => {
      const f = filas[Number(b.dataset.i)];
      document.getElementById(`vars-${b.dataset.i}`).textContent = f.variedades.join(", ");
    }));
  tbody.querySelectorAll(".comp-ver").forEach((b) =>
    b.addEventListener("click", () => verGuardada(b.dataset.id)));
  tbody.querySelectorAll(".comp-consultar").forEach((b) =>
    b.addEventListener("click", () => consultarUna(b)));
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
