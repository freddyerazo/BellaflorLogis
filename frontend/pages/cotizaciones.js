import { apiGet } from "../js/api.js";

/* ═══════════════════════════════════════════════════════════════════════
   COTIZACIONES — Wizard interactivo de costos de exportación (5 pasos)
   Paso 1: País Origen / País Destino / Moneda
   Paso 2: Producto floral (especie, variedad, FOB)
   Paso 3: Empaque (caja, tallos, cajas)
   Paso 4: Ruta aérea (aerolínea, tarifa flete)
   Paso 5: Costos en destino (agente, handling, logística)
   ═══════════════════════════════════════════════════════════════════════ */

/* ─── Estado global ──────────────────────────────────────────────────── */
const state = {
  step: 1,
  catalogo: null,

  // Paso 1 — Ruta, aeropuerto destino, incoterm y moneda
  pais_origen_id:       null,
  pais_origen_nombre:   "Ecuador",
  pais_destino_id:      null,
  pais_destino_nombre:  "",
  aeropuerto_origen:    null,   // iata_code del aeropuerto de origen
  aeropuerto_destino:   null,   // iata_code del aeropuerto de destino
  aeropuerto_origen_id:  null,  // UUID del aeropuerto de origen
  aeropuerto_destino_id: null,  // UUID del aeropuerto de destino
  incoterm_id:          null,
  incoterm_code:        "",
  moneda: "USD",                // "USD" | "EUR"

  // Paso 2 — Producto
  especie_id:       null,
  variedad_id:      null,
  grado_id:         null,
  especie_nombre:   "",
  variedad_nombre:  "",
  fob_usd:          0.53,
  comision_pct:     9,

  // Paso 3 — Empaque (multi-caja)
  cajas_config: [{ id: 1, cantidad: 1, box_type_id: null }],
  stems_per_box: 150,   // tallos por caja (global, aplica a todas las filas)
  // Campos legacy usados como fallback cuando cajas_config está vacío
  box_type_id:   null,
  box_code:      "",
  length_cm:     100,
  width_cm:      50,
  height_cm:     20,
  kg_per_box:    14,
  cajas:         12,

  // Paso 4 — Ruta aérea
  aerolinea_id:     null,
  aeropuerto_orig:  "GYE",
  aeropuerto_dest:  "AMS",
  flete_eur_kg:     2.73,
  vol_factor:       6000,

  // Paso 5 — Costos destino
  proveedor_id:           null,
  due_carrier_eur:        73.92,
  import_decl_eur:        0,
  seguro_eur:             0,
  handling_kn_eur:        50,
  transport_aalsmeer_eur: 25,
  fitosanitario_eur:      0,
  handling_tallo_eur:     0.025,
  transport_dest_eur:     8,
  eur_to_usd:             1.19,
};

const TOTAL_STEPS = 5;

/* Catálogo cargado en init() — disponible globalmente para calcular() */
let _catalog = null;

/* ─── Formateo dinámico según moneda elegida ─────────────────────────── */
const $f2 = (v) =>
  new Intl.NumberFormat("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v ?? 0);

function $money(usd) {
  if (state.moneda === "EUR") {
    return `€${$f2(usd / state.eur_to_usd)}`;
  }
  return `$${$f2(usd)}`;
}
const $usd = (v) => `$${$f2(v)}`;
const $eur = (v) => `€${$f2(v)}`;
const $kg  = (v) =>
  new Intl.NumberFormat("es-EC", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v ?? 0) + " kg";

/* ─── Cálculo central ────────────────────────────────────────────────── */
function calcular() {
  const s = state;

  // ── Pesos y tallos: multi-caja cuando hay config, legado en caso contrario ──
  let total_stems = 0, total_kg_real = 0, total_chargeable = 0, total_vol_weight = 0, total_cajas = 0;
  const configs = (s.cajas_config || []).filter((c) => c.box_type_id && c.cantidad > 0);

  if (configs.length > 0 && _catalog) {
    for (const conf of configs) {
      const bt = (_catalog.box_types || []).find((b) => b.id === conf.box_type_id);
      if (!bt) continue;
      const kg  = parseFloat(bt.reference_weight_kg) || 0;
      const vol = (bt.length_cm * bt.width_cm * bt.height_cm) / s.vol_factor;
      total_kg_real    += kg * conf.cantidad;
      total_vol_weight += vol * conf.cantidad;
      total_chargeable += Math.max(kg, vol) * conf.cantidad;
      total_stems      += s.stems_per_box * conf.cantidad;
      total_cajas      += conf.cantidad;
    }
  } else {
    // Fallback legado (sin config multi-caja)
    const vol_per_box = (s.length_cm * s.width_cm * s.height_cm) / s.vol_factor;
    total_stems      = s.stems_per_box * s.cajas;
    total_kg_real    = s.kg_per_box    * s.cajas;
    total_vol_weight = vol_per_box     * s.cajas;
    total_chargeable = Math.max(s.kg_per_box, vol_per_box) * s.cajas;
    total_cajas      = s.cajas;
  }

  // Promedios por caja (para displays individuales en paso 4)
  const vol_weight_per_box = total_cajas > 0 ? total_vol_weight / total_cajas : 0;
  const chargeable_per_box = total_cajas > 0 ? total_chargeable / total_cajas : 0;

  const s1_usd       = s.fob_usd * total_stems;
  const comision_usd = s1_usd * (s.comision_pct / 100);

  const s2_eur = s.due_carrier_eur + s.import_decl_eur + s.seguro_eur +
                 s.handling_kn_eur + s.transport_aalsmeer_eur;
  const s2_usd = s2_eur * s.eur_to_usd;

  const s3_eur = s.flete_eur_kg * total_chargeable;
  const s3_usd = s3_eur * s.eur_to_usd;

  const s4_eur = s.fitosanitario_eur;
  const s4_usd = s4_eur * s.eur_to_usd;

  const s5_eur = (s.handling_tallo_eur * total_stems) + s.transport_dest_eur;
  const s5_usd = s5_eur * s.eur_to_usd;

  const total_usd     = s1_usd + s2_usd + s3_usd + s4_usd + s5_usd;
  const cost_per_stem = total_stems > 0 ? total_usd / total_stems : 0;
  const cost_per_box  = total_cajas  > 0 ? total_usd / total_cajas  : 0;

  return {
    total_stems, total_kg_real, total_vol_weight, total_chargeable, total_cajas,
    vol_weight_per_box, chargeable_per_box,
    s1_usd, comision_usd,
    s2_eur, s2_usd,
    s3_eur, s3_usd,
    s4_eur, s4_usd,
    s5_eur, s5_usd,
    total_usd, cost_per_stem, cost_per_box,
  };
}

/* ─── SVG Donut chart ────────────────────────────────────────────────── */
const SECTION_COLORS = ["#388e3c", "#f57c00", "#1976d2", "#7b1fa2", "#00897b"];

function buildDonut(c) {
  const slices = [
    { label: "Producto",    val: c.s1_usd, color: SECTION_COLORS[0] },
    { label: "Documentos",  val: c.s2_usd, color: SECTION_COLORS[1] },
    { label: "Flete aéreo", val: c.s3_usd, color: SECTION_COLORS[2] },
    { label: "Importación", val: c.s4_usd, color: SECTION_COLORS[3] },
    { label: "Logística",   val: c.s5_usd, color: SECTION_COLORS[4] },
  ].filter((s) => s.val > 0);

  const total = slices.reduce((a, s) => a + s.val, 0);
  if (total === 0) return `<div class="donut-empty">Sin datos aún</div>`;

  const R = 70, cx = 90, cy = 90, strokeW = 28;
  const circ = 2 * Math.PI * R;
  let offset = 0, paths = "", legend = "";

  for (const sl of slices) {
    const pct  = sl.val / total;
    const dash = pct * circ;
    paths += `<circle cx="${cx}" cy="${cy}" r="${R}"
      fill="none" stroke="${sl.color}" stroke-width="${strokeW}"
      stroke-dasharray="${dash.toFixed(2)} ${(circ - dash).toFixed(2)}"
      stroke-dashoffset="${(-offset * circ + circ / 4).toFixed(2)}"
      class="donut-slice" />`;
    legend += `<div class="legend-row">
      <span class="legend-dot" style="background:${sl.color}"></span>
      <span class="legend-label">${sl.label}</span>
      <span class="legend-pct">${Math.round(pct * 100)}%</span>
      <span class="legend-val">${$money(sl.val)}</span>
    </div>`;
    offset += pct;
  }

  return `
    <svg viewBox="0 0 180 180" class="donut-svg">
      ${paths}
      <text x="${cx}" y="${cy - 6}" text-anchor="middle" class="donut-center-label">Total</text>
      <text x="${cx}" y="${cy + 14}" text-anchor="middle" class="donut-center-value">${$money(total)}</text>
    </svg>
    <div class="donut-legend">${legend}</div>`;
}

/* ─── Actualizar panel de preview ────────────────────────────────────── */
function updatePreview() {
  const c = calcular();
  const s = state;

  // Encabezado de ruta
  const ruta = [s.pais_origen_nombre, s.pais_destino_nombre].filter(Boolean).join(" → ") || "—";
  const monedaBadge = s.moneda === "EUR" ? "€ EUR" : "$ USD";
  document.getElementById("prev-ruta").textContent      = ruta;
  document.getElementById("prev-moneda").textContent    = monedaBadge;
  const aeroEl = document.getElementById("prev-aeropuerto");
  const rutaAero = [s.aeropuerto_origen, s.aeropuerto_destino].filter(Boolean).join(" → ");
  if (aeroEl) aeroEl.textContent = rutaAero || "—";
  const incEl = document.getElementById("prev-incoterm");
  if (incEl) incEl.textContent = s.incoterm_code || "—";

  const nombre = [s.especie_nombre, s.variedad_nombre].filter(Boolean).join(" · ") || "—";
  document.getElementById("prev-producto").textContent  = nombre;
  document.getElementById("prev-stems").textContent     = `${c.total_stems.toLocaleString("es-EC")} tallos · ${s.cajas} cajas`;
  document.getElementById("prev-peso-real").textContent = $kg(c.total_kg_real);
  document.getElementById("prev-peso-vol").textContent  = $kg(c.total_chargeable);

  document.getElementById("prev-s1").textContent = $money(c.s1_usd);
  document.getElementById("prev-s2").textContent = $money(c.s2_usd);
  document.getElementById("prev-s3").textContent = $money(c.s3_usd);
  document.getElementById("prev-s4").textContent = $money(c.s4_usd);
  document.getElementById("prev-s5").textContent = $money(c.s5_usd);

  const totalEl = document.getElementById("prev-total");
  const newTotal = $money(c.total_usd);
  if (totalEl.textContent !== newTotal) {
    totalEl.classList.remove("total-pop");
    void totalEl.offsetWidth;
    totalEl.classList.add("total-pop");
  }
  totalEl.textContent = newTotal;
  document.getElementById("prev-per-stem").textContent = `${$money(c.cost_per_stem)}/tallo`;
  document.getElementById("prev-per-box").textContent  = `${$money(c.cost_per_box)}/caja`;

  document.getElementById("prev-donut").innerHTML = buildDonut(c);

  actualizarIndicador();
}

function actualizarIndicador() {
  const done = [
    state.pais_origen_id && state.pais_destino_id,  // paso 1 — Ruta
    state.cajas > 0 && state.box_type_id,            // paso 2 — Empaque
    state.fob_usd > 0,                               // paso 3 — Producto
    state.flete_eur_kg > 0,                          // paso 4 — Ruta aérea
    state.eur_to_usd > 0,                            // paso 5 — Costos
  ];
  done.forEach((ok, i) => {
    const el = document.querySelector(`.step-circle[data-step="${i + 1}"]`);
    if (el) el.classList.toggle("done", ok);
  });
}

/* ─── Cambio de paso ─────────────────────────────────────────────────── */
function goStep(n) {
  const dir = n > state.step ? "slide-fwd" : "slide-back";
  state.step = n;
  document.querySelectorAll(".step-panel").forEach((p) =>
    p.classList.remove("active", "slide-fwd", "slide-back")
  );
  document.querySelectorAll(".step-indicator .step-item").forEach((it) => {
    const sn = parseInt(it.dataset.step);
    it.classList.toggle("active",  sn === n);
    it.classList.toggle("visited", sn < n);
  });
  const panel = document.getElementById(`step-${n}`);
  if (panel) {
    panel.classList.add("active", dir);
    panel.addEventListener("animationend", () => panel.classList.remove(dir), { once: true });
  }

  document.getElementById("btn-prev").disabled = n === 1;
  const btnNext = document.getElementById("btn-next");
  const dots    = document.querySelectorAll(".nav-dot");
  dots.forEach((d) => d.classList.toggle("active", parseInt(d.dataset.step) === n));

  if (n === TOTAL_STEPS) {
    btnNext.innerHTML = '<i class="ph ph-check-circle"></i> Ver resumen';
    btnNext.classList.add("btn-success");
  } else {
    btnNext.innerHTML = 'Siguiente <i class="ph ph-arrow-right"></i>';
    btnNext.classList.remove("btn-success");
  }
}

/* ─── Helper select ──────────────────────────────────────────────────── */
function buildOptions(data, valueFn, labelFn, placeholder = "Selecciona...") {
  return `<option value="">${placeholder}</option>` +
    (data ?? []).map((d) => `<option value="${valueFn(d)}">${labelFn(d)}</option>`).join("");
}

/* ════════════════════════════════════════════════════════════════════════
   RENDERS DE PASOS
   ════════════════════════════════════════════════════════════════════════ */

/* ── PASO 1: País origen / destino / moneda ──────────────────────────── */
function renderStep1(cat) {
  const paisOrigOpts = buildOptions(cat.paises_origen, (p) => p.id, (p) => `${p.code} · ${p.name}`, "Selecciona país...");
  const paisDestOpts = buildOptions(cat.paises_destino, (p) => p.id, (p) => `${p.code} · ${p.name}`, "Selecciona país...");
  const incotermOpts = buildOptions(
    cat.incoterms,
    (i) => i.id,
    (i) => `${i.code} — ${i.name}${i.description ? ' (' + i.description + ')' : ''}`,
    "Selecciona incoterm..."
  );

  // Banderas emoji por código de país
  const FLAG = { EC:"🇪🇨", NL:"🇳🇱", DE:"🇩🇪", ES:"🇪🇸", US:"🇺🇸" };

  return `
  <div class="step-card step-card--teal">
    <div class="step-card-header">
      <span class="step-icon"><i class="ph ph-map-trifold"></i></span>
      <div>
        <h2>Ruta de exportación</h2>
        <p>Define el origen, destino, aeropuerto, incoterm y moneda de la cotización</p>
      </div>
    </div>
    <div class="step-fields">

      <!-- País de Origen -->
      <div class="field-group">
        <label for="sel-pais-origen">País de Origen</label>
        <select id="sel-pais-origen">${paisOrigOpts}</select>
      </div>

      <!-- Aeropuerto de origen -->
      <div class="field-group">
        <label for="sel-aeropuerto-origen">Aeropuerto de origen</label>
        <select id="sel-aeropuerto-origen" disabled>
          <option value="">Primero selecciona el país de origen</option>
        </select>
      </div>

      <!-- Visualización animada de ruta -->
      <div class="ruta-arrow">
        <div class="ruta-pais" id="ruta-orig-pill">
          <span class="ruta-code" id="ruta-orig-flag">EC</span>
          <span id="ruta-orig-label">Ecuador</span>
        </div>
        <div class="ruta-flight-line">
          <div class="rfl-track"></div>
          <div class="rfl-fill" id="rfl-fill"></div>
          <div class="rfl-plane" id="rfl-plane"><i class="ph ph-airplane-tilt"></i></div>
        </div>
        <div class="ruta-pais" id="ruta-dest-pill">
          <span class="ruta-code" id="ruta-dest-flag">?</span>
          <span id="ruta-dest-label">Destino</span>
        </div>
      </div>

      <!-- País de Destino -->
      <div class="field-group">
        <label for="sel-pais-destino">País de Destino</label>
        <select id="sel-pais-destino">${paisDestOpts}</select>
      </div>

      <!-- Aeropuerto de destino -->
      <div class="field-group">
        <label for="sel-aeropuerto-destino">Aeropuerto de destino</label>
        <select id="sel-aeropuerto-destino" disabled>
          <option value="">Primero selecciona el país de destino</option>
        </select>
      </div>

      <!-- Incoterm de venta -->
      <div class="field-group">
        <label for="sel-incoterm">Incoterm de venta</label>
        <select id="sel-incoterm">${incotermOpts}</select>
        <small id="incoterm-ruta-note" style="color:#e65100;font-size:.78rem;margin-top:4px;display:none">
          <i class="ph ph-warning"></i> Sin tarifa registrada para este destino — solo disponible FOB
        </small>
      </div>

      <!-- Aerolínea -->
      <div class="field-group">
        <label for="sel-aerolinea-ruta">Aerolínea</label>
        <select id="sel-aerolinea-ruta" disabled>
          <option value="">Selecciona los aeropuertos primero</option>
        </select>
      </div>

      <!-- Moneda -->
      <div class="field-group">
        <label>Moneda de la cotización</label>
        <div class="moneda-selector">
          <button class="moneda-btn ${state.moneda === 'USD' ? 'active' : ''}" data-moneda="USD">
            <span class="moneda-symbol">$</span>
            <span class="moneda-name">Dólares</span>
            <span class="moneda-code">USD</span>
          </button>
          <button class="moneda-btn ${state.moneda === 'EUR' ? 'active' : ''}" data-moneda="EUR">
            <span class="moneda-symbol">€</span>
            <span class="moneda-name">Euros</span>
            <span class="moneda-code">EUR</span>
          </button>
        </div>
      </div>

      <div class="field-note">
        La moneda define cómo se presentan los totales en la cotización. Los cálculos internos se realizan en USD y se convierten con el tipo de cambio configurado en el Paso 5.
      </div>

    </div>
  </div>`;
}

/* ── PASO 2: Producto floral ─────────────────────────────────────────── */
function renderStep2(cat) {
  const especiesOpts = buildOptions(cat.especies, (e) => e.id, (e) => e.name, "Selecciona una especie...");
  const gradosOpts   = buildOptions(
    cat.grados, (g) => g.id,
    (g) => `${g.size_code}${g.description ? ' — ' + g.description : ''}${g.species_name ? ' (' + g.species_name + ')' : ''}`,
    "Todos los grados"
  );

  return `
  <div class="step-card step-card--green">
    <div class="step-card-header">
      <span class="step-icon"><i class="ph ph-flower"></i></span>
      <div>
        <h2>Producto floral</h2>
        <p>Define la especie, variedad y precio de salida (FOB)</p>
      </div>
    </div>
    <div class="step-fields">

      <div class="field-group">
        <label for="sel-especie">Especie</label>
        <select id="sel-especie">${especiesOpts}</select>
      </div>

      <div class="field-group">
        <label for="sel-variedad">Variedad</label>
        <select id="sel-variedad" disabled>
          <option value="">Primero selecciona la especie</option>
        </select>
      </div>

      <div class="field-group">
        <label for="sel-grado">Grado (opcional)</label>
        <select id="sel-grado">${gradosOpts}</select>
      </div>

      <div class="field-row">
        <div class="field-group">
          <label for="inp-fob">Precio FOB por tallo (USD)</label>
          <div class="input-prefix"><span>$</span>
            <input type="number" id="inp-fob" step="0.01" min="0" value="${state.fob_usd}" />
          </div>
        </div>
        <div class="field-group">
          <label for="inp-comision">Comisión grower (%)</label>
          <div class="input-prefix"><span>%</span>
            <input type="number" id="inp-comision" step="0.5" min="0" max="30" value="${state.comision_pct}" />
          </div>
        </div>
      </div>

      <div class="field-note">
        Referencia: Amaranthus $0.53 · Phlox $0.03 · Lisimachia $0.05
      </div>

    </div>
  </div>`;
}

/* ── PASO 2 (antes 3): Empaque ───────────────────────────────────────── */
function renderStep3(cat) {
  function buildRowOpts(selectedId) {
    return `<option value="">Tipo de caja...</option>` +
      cat.box_types.map((b) =>
        `<option value="${b.id}"${b.id === selectedId ? " selected" : ""}>${b.box_code}${b.box_name ? " — " + b.box_name : ""} (${b.length_cm}×${b.width_cm}×${b.height_cm} cm${b.reference_weight_kg ? ", ref. " + b.reference_weight_kg + " kg" : ""})</option>`
      ).join("");
  }

  const rowsHTML = state.cajas_config.map((conf) => `
    <div class="caja-row" data-row-id="${conf.id}">
      <input type="number" class="caja-row-qty" value="${conf.cantidad}" min="1" max="999" />
      <select class="caja-row-type">${buildRowOpts(conf.box_type_id)}</select>
      <button class="caja-row-remove" title="Eliminar fila"><i class="ph ph-x"></i></button>
    </div>`).join("");

  const initTallos = state.stems_per_box * state.cajas_config.reduce((a, c) => a + c.cantidad, 0);

  return `
  <div class="step-card step-card--amber">
    <div class="step-card-header">
      <span class="step-icon"><i class="ph ph-package"></i></span>
      <div>
        <h2>Configuración de empaque</h2>
        <p>Agrega los tipos de caja y piezas del embarque</p>
      </div>
    </div>
    <div class="step-fields">

      <!-- Tabla multi-caja -->
      <div class="cajas-multi-table">
        <div class="cajas-multi-header">
          <span>Piezas</span>
          <span>Tipo Caja</span>
          <span></span>
        </div>
        <div id="cajas-rows-container">${rowsHTML}</div>
      </div>
      <button class="btn-add-caja-row" id="btn-add-caja-row">
        <i class="ph ph-list-plus"></i> Agregar Nuevo
      </button>

      <!-- Totales derivados -->
      <div class="derived-row" style="margin-top:14px">
        <span>Total tallos: <b id="der-total-stems">${initTallos.toLocaleString("es-EC")}</b></span>
        <span>Peso total: <b id="der-total-kg">—</b></span>
      </div>

    </div>
  </div>`;
}

/* ── PASO 4: Ruta aérea ──────────────────────────────────────────────── */
function renderStep4(cat) {
  const airOpts  = buildOptions(cat.aerolineas, (a) => a.id, (a) => `${a.airline_code} — ${a.airline_name}`, "Selecciona aerolínea...");
  const origOpts = buildOptions(cat.aeropuertos, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city}`, "Origen...");
  const destOpts = buildOptions(cat.aeropuertos, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city}`, "Destino...");

  return `
  <div class="step-card step-card--blue">
    <div class="step-card-header">
      <span class="step-icon"><i class="ph ph-airplane-takeoff"></i></span>
      <div>
        <h2>Ruta aérea y flete</h2>
        <p>Aerolínea, ruta y tarifa de flete por kilogramo facturable</p>
      </div>
    </div>
    <div class="step-fields">

      <div class="field-group">
        <label for="sel-aerolinea">Aerolínea</label>
        <select id="sel-aerolinea">${airOpts}</select>
      </div>

      <div class="field-row">
        <div class="field-group">
          <label for="sel-orig">Aeropuerto origen</label>
          <select id="sel-orig">${origOpts}</select>
        </div>
        <div class="field-group">
          <label for="sel-dest">Aeropuerto destino</label>
          <select id="sel-dest">${destOpts}</select>
        </div>
      </div>

      <div class="field-row">
        <div class="field-group">
          <label for="inp-flete">Tarifa all-in (EUR/kg)</label>
          <div class="input-prefix"><span>€</span>
            <input type="number" id="inp-flete" step="0.01" min="0" value="${state.flete_eur_kg}" />
          </div>
        </div>
        <div class="field-group">
          <label for="inp-volfactor">Factor volumétrico (cm³/kg)</label>
          <input type="number" id="inp-volfactor" step="100" min="1000" value="${state.vol_factor}" />
        </div>
      </div>

      <div class="weight-calc-panel">
        <div class="wc-header"><i class="ph ph-scales"></i> Cálculo de peso</div>
        <div class="wc-grid">
          <div class="wc-row"><span>Peso real total</span><strong id="wc-real">—</strong></div>
          <div class="wc-row"><span>Peso volumétrico total</span><strong id="wc-vol">—</strong></div>
          <div class="wc-row wc-highlight"><span>✦ Peso facturable (MAX)</span><strong id="wc-fact">—</strong></div>
          <div class="wc-row"><span>Costo de flete estimado</span><strong id="wc-cost">—</strong></div>
        </div>
      </div>

      <div class="field-note">
        Referencia: Tarifa 2.73 EUR/kg all-in · Factor IATA estándar 6000
      </div>

    </div>
  </div>`;
}

/* ── PASO 5: Costos en destino ───────────────────────────────────────── */
function renderStep5(cat) {
  const provOpts = buildOptions(cat.proveedores, (p) => p.id, (p) => `${p.provider_code} — ${p.provider_name}`, "Sin proveedor asignado");

  return `
  <div class="step-card step-card--violet">
    <div class="step-card-header">
      <span class="step-icon"><i class="ph ph-buildings"></i></span>
      <div>
        <h2>Costos en destino</h2>
        <p>Documentos de exportación, agente K&amp;N y logística en destino</p>
      </div>
    </div>
    <div class="step-fields">

      <div class="field-group">
        <label for="sel-proveedor">Agente / Proveedor</label>
        <select id="sel-proveedor">${provOpts}</select>
      </div>

      <div class="cost-section-block" style="--accent:#f57c00">
        <div class="csb-header"><i class="ph ph-file-text"></i> Sección 2 — Documentos de exportación</div>
        <div class="field-row">
          <div class="field-group">
            <label for="inp-due-carrier">Due carrier / Agente (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-due-carrier" step="0.01" min="0" value="${state.due_carrier_eur}" />
            </div>
          </div>
          <div class="field-group">
            <label for="inp-import-decl">Declaración importación (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-import-decl" step="0.01" min="0" value="${state.import_decl_eur}" />
            </div>
          </div>
        </div>
        <div class="field-row">
          <div class="field-group">
            <label for="inp-seguro">Cargo de seguridad (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-seguro" step="0.01" min="0" value="${state.seguro_eur}" />
            </div>
          </div>
          <div class="field-group">
            <label for="inp-handling-kn">Handling K&amp;N NL (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-handling-kn" step="0.01" min="0" value="${state.handling_kn_eur}" />
            </div>
          </div>
        </div>
        <div class="field-group">
          <label for="inp-transport-aalsmeer">Transporte Aalsmeer (EUR)</label>
          <div class="input-prefix"><span>€</span>
            <input type="number" id="inp-transport-aalsmeer" step="0.01" min="0" value="${state.transport_aalsmeer_eur}" />
          </div>
        </div>
      </div>

      <div class="cost-section-block" style="--accent:#7b1fa2">
        <div class="csb-header"><i class="ph ph-shield-check"></i> Sección 4 — Derechos de importación</div>
        <div class="field-group">
          <label for="inp-fitosanitario">Fitosanitario (EUR)</label>
          <div class="input-prefix"><span>€</span>
            <input type="number" id="inp-fitosanitario" step="0.01" min="0" value="${state.fitosanitario_eur}" />
          </div>
        </div>
      </div>

      <div class="cost-section-block" style="--accent:#00897b">
        <div class="csb-header"><i class="ph ph-truck"></i> Sección 5 — Logística en destino</div>
        <div class="field-row">
          <div class="field-group">
            <label for="inp-handling-tallo">Handling por tallo (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-handling-tallo" step="0.005" min="0" value="${state.handling_tallo_eur}" />
            </div>
          </div>
          <div class="field-group">
            <label for="inp-transport-dest">Transporte a mercado (EUR)</label>
            <div class="input-prefix"><span>€</span>
              <input type="number" id="inp-transport-dest" step="0.01" min="0" value="${state.transport_dest_eur}" />
            </div>
          </div>
        </div>
      </div>

      <div class="field-row">
        <div class="field-group">
          <label for="inp-fx">Tipo de cambio EUR → USD</label>
          <div class="input-prefix"><span>×</span>
            <input type="number" id="inp-fx" step="0.001" min="0.5" max="3" value="${state.eur_to_usd}" />
          </div>
        </div>
        <div class="field-note" style="align-self:flex-end;padding:0 0 4px">
          Referencia: 1 EUR = 1.19 USD
        </div>
      </div>

    </div>
  </div>`;
}

/* ════════════════════════════════════════════════════════════════════════
   BIND DE EVENTOS POR PASO
   ════════════════════════════════════════════════════════════════════════ */

function filterIncotermByRuta(cat) {
  const selInc = document.getElementById("sel-incoterm");
  const note   = document.getElementById("incoterm-ruta-note");
  if (!selInc) return;

  const origId = state.aeropuerto_origen_id;
  const destId = state.aeropuerto_destino_id;

  // Hay tarifa activa para esta ruta?
  const hasTarifa = !!(origId && destId &&
    (cat.rutas_activas ?? []).some(
      (r) => r.origin_airport_id === origId && r.destination_airport_id === destId
    )
  );

  // Habilitar/deshabilitar opciones no-FOB
  Array.from(selInc.options).forEach((opt) => {
    if (!opt.value) return;
    const inc = (cat.incoterms ?? []).find((i) => i.id === opt.value);
    opt.disabled = !hasTarifa && inc?.code !== "FOB";
    if (opt.disabled) opt.style.color = "#bbb";
    else opt.style.color = "";
  });

  // Si la opción actual quedó deshabilitada → forzar FOB
  const current = selInc.options[selInc.selectedIndex];
  if (current?.disabled) {
    const fobOpt = Array.from(selInc.options).find((o) => {
      const inc = (cat.incoterms ?? []).find((i) => i.id === o.value);
      return inc?.code === "FOB";
    });
    if (fobOpt) {
      selInc.value        = fobOpt.value;
      state.incoterm_id   = fobOpt.value;
      const inc = (cat.incoterms ?? []).find((i) => i.id === fobOpt.value);
      state.incoterm_code = inc?.code || "";
      updatePreview();
    }
  }

  // Mostrar/ocultar nota explicativa
  if (note) {
    note.style.display = hasTarifa ? "none" : "";
  }
}

function updateAerolineasRuta(cat) {
  const sel    = document.getElementById("sel-aerolinea-ruta");
  if (!sel) return;
  const origId = state.aeropuerto_origen_id;
  const destId = state.aeropuerto_destino_id;

  if (!origId || !destId) {
    sel.innerHTML      = `<option value="">Selecciona los aeropuertos primero</option>`;
    sel.disabled       = true;
    state.aerolinea_id = null;
    filterIncotermByRuta(cat);
    return;
  }

  const airlineIds = new Set(
    (cat.rutas_activas ?? [])
      .filter((r) => r.origin_airport_id === origId && r.destination_airport_id === destId)
      .map((r) => r.airline_id)
  );
  const filtered = (cat.aerolineas ?? []).filter((a) => airlineIds.has(a.id));

  filterIncotermByRuta(cat);

  if (filtered.length === 0) {
    sel.innerHTML      = `<option value="">Sin tarifa activa para esta ruta</option>`;
    sel.disabled       = true;
    state.aerolinea_id = null;
  } else {
    sel.innerHTML = buildOptions(filtered, (a) => a.id, (a) => `${a.airline_code} — ${a.airline_name}`, "Selecciona aerolínea...");
    sel.disabled  = false;
    if (filtered.length === 1) {
      sel.value          = filtered[0].id;
      state.aerolinea_id = filtered[0].id;
      const selStep4 = document.getElementById("sel-aerolinea");
      if (selStep4) selStep4.value = filtered[0].id;
    }
  }
}

function triggerFlightAnim() {
  const fill  = document.getElementById("rfl-fill");
  const plane = document.getElementById("rfl-plane");
  if (!fill || !plane) return;
  if (state.pais_origen_id && state.pais_destino_id) {
    fill.classList.add("active");
    plane.classList.add("in-flight");
    document.getElementById("ruta-orig-pill")?.classList.add("filled");
    document.getElementById("ruta-dest-pill")?.classList.add("filled");
  } else {
    fill.classList.remove("active");
    plane.classList.remove("in-flight");
  }
}

function bindStep1(cat) {
  const selOrig = document.getElementById("sel-pais-origen");
  const selDest = document.getElementById("sel-pais-destino");

  selOrig.addEventListener("change", () => {
    const p = cat.paises_origen.find((x) => x.id === selOrig.value);
    state.pais_origen_id     = selOrig.value || null;
    state.pais_origen_nombre = p?.name || "";
    document.getElementById("ruta-orig-flag").textContent  = p?.code || "?";
    document.getElementById("ruta-orig-label").textContent = p?.name || "Origen";
    triggerFlightAnim();

    // Filtrar aeropuertos por país de origen
    const selAeroOrig = document.getElementById("sel-aeropuerto-origen");
    const airportsOrig = cat.aeropuertos.filter((a) => a.country_id === selOrig.value);
    if (airportsOrig.length > 0) {
      selAeroOrig.innerHTML = buildOptions(airportsOrig, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city} — ${a.airport_name}`, "Selecciona aeropuerto...");
      selAeroOrig.disabled  = false;
      // Auto-seleccionar si solo hay uno
      if (airportsOrig.length === 1) {
        selAeroOrig.value           = airportsOrig[0].iata_code;
        state.aeropuerto_origen     = airportsOrig[0].iata_code;
        state.aeropuerto_origen_id  = airportsOrig[0].id;
      } else {
        state.aeropuerto_origen    = null;
        state.aeropuerto_origen_id = null;
      }
    } else {
      selAeroOrig.innerHTML = `<option value="">Sin aeropuertos registrados para este país</option>`;
      selAeroOrig.disabled  = true;
      state.aeropuerto_origen    = null;
      state.aeropuerto_origen_id = null;
    }

    updateAerolineasRuta(cat);
    updatePreview();
  });

  document.getElementById("sel-aeropuerto-origen").addEventListener("change", (e) => {
    state.aeropuerto_origen    = e.target.value || null;
    const aOrig = cat.aeropuertos.find((a) => a.iata_code === e.target.value);
    state.aeropuerto_origen_id = aOrig?.id ?? null;
    updateAerolineasRuta(cat);
    updatePreview();
  });

  selDest.addEventListener("change", () => {
    const p = cat.paises_destino.find((x) => x.id === selDest.value);
    state.pais_destino_id     = selDest.value || null;
    state.pais_destino_nombre = p?.name || "";
    document.getElementById("ruta-dest-flag").textContent  = p?.code || "?";
    document.getElementById("ruta-dest-label").textContent = p?.name || "Destino";
    triggerFlightAnim();

    // Filtrar aeropuertos por país de destino
    const selAero = document.getElementById("sel-aeropuerto-destino");
    const airports = cat.aeropuertos.filter((a) => a.country_id === selDest.value);
    if (airports.length > 0) {
      selAero.innerHTML = buildOptions(airports, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city} — ${a.airport_name}`, "Selecciona aeropuerto...");
      selAero.disabled  = false;
    } else {
      selAero.innerHTML = `<option value="">Sin aeropuertos registrados para este país</option>`;
      selAero.disabled  = true;
    }
    state.aeropuerto_destino    = null;
    state.aeropuerto_destino_id = null;

    updateAerolineasRuta(cat);
    updatePreview();
  });

  document.getElementById("sel-aeropuerto-destino").addEventListener("change", (e) => {
    state.aeropuerto_destino    = e.target.value || null;
    const aDest = cat.aeropuertos.find((a) => a.iata_code === e.target.value);
    state.aeropuerto_destino_id = aDest?.id ?? null;
    updateAerolineasRuta(cat);
    updatePreview();
  });

  document.getElementById("sel-aerolinea-ruta").addEventListener("change", (e) => {
    state.aerolinea_id = e.target.value || null;
    const selAirStep4  = document.getElementById("sel-aerolinea");
    if (selAirStep4) selAirStep4.value = e.target.value;
  });

  document.getElementById("sel-incoterm").addEventListener("change", (e) => {
    state.incoterm_id   = e.target.value || null;
    const inc           = cat.incoterms.find((i) => i.id === e.target.value);
    state.incoterm_code = inc?.code || "";
    updatePreview();
  });

  document.querySelectorAll(".moneda-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".moneda-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.moneda = btn.dataset.moneda;
      updatePreview();
    });
  });

  // Pre-seleccionar Ecuador como origen si existe
  const ecuador = cat.paises_origen.find((p) => p.code === "EC");
  if (ecuador) {
    selOrig.value = ecuador.id;
    state.pais_origen_id     = ecuador.id;
    state.pais_origen_nombre = ecuador.name;
    document.getElementById("ruta-orig-flag").textContent  = "EC";
    document.getElementById("ruta-orig-label").textContent = ecuador.name;
    document.getElementById("ruta-orig-pill")?.classList.add("filled");

    // Cargar aeropuertos de Ecuador
    const selAeroOrig  = document.getElementById("sel-aeropuerto-origen");
    const airportsEc   = cat.aeropuertos.filter((a) => a.country_id === ecuador.id);
    if (airportsEc.length > 0) {
      selAeroOrig.innerHTML = buildOptions(airportsEc, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city} — ${a.airport_name}`, "Selecciona aeropuerto...");
      selAeroOrig.disabled  = false;
    }
  }

  // Filtrar incoterm según tarifa al cargar
  filterIncotermByRuta(cat);
}

function bindStep2(cat) {
  const selEsp = document.getElementById("sel-especie");
  const selVar = document.getElementById("sel-variedad");

  selEsp.addEventListener("change", () => {
    const id = selEsp.value;
    state.especie_id     = id || null;
    state.especie_nombre = selEsp.options[selEsp.selectedIndex]?.text || "";
    const vars = cat.variedades.filter((v) => v.species_id === id);
    selVar.disabled = vars.length === 0;
    selVar.innerHTML = buildOptions(vars, (v) => v.id, (v) => v.name, "Selecciona variedad...");
    state.variedad_id     = null;
    state.variedad_nombre = "";
    updatePreview();
  });

  selVar.addEventListener("change", () => {
    state.variedad_id     = selVar.value || null;
    state.variedad_nombre = selVar.options[selVar.selectedIndex]?.text || "";
    updatePreview();
  });

  document.getElementById("sel-grado").addEventListener("change", (e) => {
    state.grado_id = e.target.value || null;
  });

  document.getElementById("inp-fob").addEventListener("input", (e) => {
    state.fob_usd = parseFloat(e.target.value) || 0;
    updatePreview();
  });

  document.getElementById("inp-comision").addEventListener("input", (e) => {
    state.comision_pct = parseFloat(e.target.value) || 0;
    updatePreview();
  });
}

function bindStep3(cat) {
  const container = document.getElementById("cajas-rows-container");

  function buildRowOpts(selectedId) {
    return `<option value="">Tipo de caja...</option>` +
      cat.box_types.map((b) =>
        `<option value="${b.id}"${b.id === selectedId ? " selected" : ""}>${b.box_code}${b.box_name ? " — " + b.box_name : ""} (${b.length_cm}×${b.width_cm}×${b.height_cm} cm${b.reference_weight_kg ? ", ref. " + b.reference_weight_kg + " kg" : ""})</option>`
      ).join("");
  }

  function updateDerived() {
    const c  = calcular();
    const ts = document.getElementById("der-total-stems");
    const tk = document.getElementById("der-total-kg");
    if (ts) ts.textContent = c.total_stems.toLocaleString("es-EC");
    if (tk) tk.textContent = $kg(c.total_kg_real);
    updatePreview();
  }

  function addRowListeners(rowEl) {
    const rowId = parseInt(rowEl.dataset.rowId);

    rowEl.querySelector(".caja-row-qty").addEventListener("input", (e) => {
      const conf = state.cajas_config.find((c) => c.id === rowId);
      if (conf) { conf.cantidad = parseInt(e.target.value) || 1; updateDerived(); }
    });

    rowEl.querySelector(".caja-row-type").addEventListener("change", (e) => {
      const conf = state.cajas_config.find((c) => c.id === rowId);
      if (conf) { conf.box_type_id = e.target.value || null; updateDerived(); }
    });

    rowEl.querySelector(".caja-row-remove").addEventListener("click", () => {
      if (state.cajas_config.length <= 1) return; // siempre mínimo 1 fila
      state.cajas_config = state.cajas_config.filter((c) => c.id !== rowId);
      rowEl.style.transition = "opacity .15s, transform .15s";
      rowEl.style.opacity = "0";
      rowEl.style.transform = "translateX(-8px)";
      setTimeout(() => { rowEl.remove(); updateDerived(); }, 160);
    });
  }

  // Adjuntar listeners a filas ya renderizadas
  container.querySelectorAll(".caja-row").forEach((row) => addRowListeners(row));

  // Botón "Agregar Nuevo"
  document.getElementById("btn-add-caja-row").addEventListener("click", () => {
    const newId = Date.now();
    state.cajas_config.push({ id: newId, cantidad: 1, box_type_id: null });

    const div = document.createElement("div");
    div.className = "caja-row";
    div.dataset.rowId = newId;
    div.innerHTML = `
      <input type="number" class="caja-row-qty" value="1" min="1" max="999" />
      <select class="caja-row-type">${buildRowOpts(null)}</select>
      <button class="caja-row-remove" title="Eliminar"><i class="ph ph-x"></i></button>`;
    div.style.opacity = "0";
    div.style.transform = "translateY(-6px)";
    container.appendChild(div);
    addRowListeners(div);
    requestAnimationFrame(() => {
      div.style.transition = "opacity .2s, transform .2s";
      div.style.opacity = "1";
      div.style.transform = "translateY(0)";
    });
  });

  updateDerived();
}

function bindStep4() {
  function refreshWeightCalc() {
    const c = calcular();
    const wR = document.getElementById("wc-real");
    const wV = document.getElementById("wc-vol");
    const wF = document.getElementById("wc-fact");
    const wC = document.getElementById("wc-cost");
    if (wR) wR.textContent = $kg(c.total_kg_real);
    if (wV) wV.textContent = $kg(c.total_vol_weight);
    if (wF) wF.textContent = $kg(c.total_chargeable);
    if (wC) wC.textContent = `${$eur(c.s3_eur)} / ${$usd(c.s3_usd)}`;
  }

  document.getElementById("sel-aerolinea").addEventListener("change", (e) => { state.aerolinea_id = e.target.value || null; });
  document.getElementById("sel-orig").addEventListener("change",      (e) => { state.aeropuerto_orig = e.target.value; });
  document.getElementById("sel-dest").addEventListener("change",      (e) => { state.aeropuerto_dest = e.target.value; });

  document.getElementById("inp-flete").addEventListener("input", (e) => {
    state.flete_eur_kg = parseFloat(e.target.value) || 0;
    refreshWeightCalc(); updatePreview();
  });
  document.getElementById("inp-volfactor").addEventListener("input", (e) => {
    state.vol_factor = parseFloat(e.target.value) || 6000;
    refreshWeightCalc(); updatePreview();
  });
  refreshWeightCalc();
}

function bindStep5() {
  const fieldMap = {
    "inp-due-carrier":        "due_carrier_eur",
    "inp-import-decl":        "import_decl_eur",
    "inp-seguro":             "seguro_eur",
    "inp-handling-kn":        "handling_kn_eur",
    "inp-transport-aalsmeer": "transport_aalsmeer_eur",
    "inp-fitosanitario":      "fitosanitario_eur",
    "inp-handling-tallo":     "handling_tallo_eur",
    "inp-transport-dest":     "transport_dest_eur",
    "inp-fx":                 "eur_to_usd",
  };
  for (const [id, key] of Object.entries(fieldMap)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.addEventListener("input", (e) => {
      state[key] = parseFloat(e.target.value) || 0;
      updatePreview();
    });
  }
}

/* ─── Guardar cotización ─────────────────────────────────────────────── */
function guardarCotizacion() {
  const c = calcular();
  const s = state;
  const cotiz = {
    id:              Date.now(),
    fecha:           new Date().toLocaleString("es-EC"),
    ruta:            `${s.pais_origen_nombre} → ${s.pais_destino_nombre}`,
    aeropuerto_orig: s.aeropuerto_origen  || "",
    aeropuerto_dest: s.aeropuerto_destino || "",
    incoterm:        s.incoterm_code || "",
    moneda:          s.moneda,
    producto:        `${s.especie_nombre} ${s.variedad_nombre}`.trim() || "Sin nombre",
    cajas:           s.cajas,
    total_stems:     c.total_stems,
    fob_usd:         s.fob_usd,
    total_kg_real:   c.total_kg_real,
    total_chargeable:c.total_chargeable,
    s1_usd: c.s1_usd, s2_usd: c.s2_usd, s3_usd: c.s3_usd,
    s4_usd: c.s4_usd, s5_usd: c.s5_usd,
    total_usd:       c.total_usd,
    cost_per_stem:   c.cost_per_stem,
    cost_per_box:    c.cost_per_box,
  };
  const saved = JSON.parse(localStorage.getItem("blis_cotizaciones") || "[]");
  saved.unshift(cotiz);
  localStorage.setItem("blis_cotizaciones", JSON.stringify(saved.slice(0, 20)));

  const btn = document.getElementById("btn-guardar");
  btn.innerHTML = '<i class="ph ph-check-circle"></i> Guardado';
  btn.disabled  = true;
  setTimeout(() => {
    btn.innerHTML = '<i class="ph ph-floppy-disk"></i> Guardar cotización';
    btn.disabled  = false;
  }, 2000);
}

/* ─── Render principal de la página ─────────────────────────────────── */
function renderPage(cat) {
  const content = document.getElementById("content");

  const steps = [
    { n:1, icon:'<i class="ph ph-map-trifold"></i>',      label:"Ruta",       color:"teal"   },
    { n:2, icon:'<i class="ph ph-package"></i>',           label:"Empaque",    color:"amber"  },
    { n:3, icon:'<i class="ph ph-flower"></i>',            label:"Producto",   color:"green"  },
    { n:4, icon:'<i class="ph ph-airplane-takeoff"></i>',  label:"Ruta aérea", color:"blue"   },
    { n:5, icon:'<i class="ph ph-buildings"></i>',         label:"Costos",     color:"violet" },
  ];

  const stepIndicatorHTML = steps.map((st, i) => `
    <div class="step-item${st.n === 1 ? ' active' : ''}" data-step="${st.n}">
      <div class="step-circle step-circle--${st.color}" data-step="${st.n}">${st.icon}</div>
      <span>${st.label}</span>
    </div>
    ${i < steps.length - 1 ? '<div class="step-connector"></div>' : ''}
  `).join("");

  const dotsHTML = steps.map((st) =>
    `<span class="nav-dot${st.n === 1 ? ' active' : ''}" data-step="${st.n}"></span>`
  ).join("");

  content.innerHTML = `
    <section class="cotiz-hero">
      <div>
        <h1>Cotizador de exportación</h1>
        <p>Simula el costo total de un embarque floral en ${TOTAL_STEPS} pasos. Cada cambio actualiza la cotización en tiempo real.</p>
      </div>
    </section>

    <div class="cotiz-layout">

      <div class="cotiz-wizard">

        <div class="step-indicator">${stepIndicatorHTML}</div>

        <div id="step-1" class="step-panel active">${renderStep1(cat)}</div>
        <div id="step-2" class="step-panel">${renderStep3(cat)}</div>
        <div id="step-3" class="step-panel">${renderStep2(cat)}</div>
        <div id="step-4" class="step-panel">${renderStep4(cat)}</div>
        <div id="step-5" class="step-panel">${renderStep5(cat)}</div>

        <div class="step-nav">
          <button id="btn-prev" class="btn btn-secondary" disabled><i class="ph ph-arrow-left"></i> Anterior</button>
          <div class="step-nav-dots">${dotsHTML}</div>
          <button id="btn-next" class="btn btn-primary">Siguiente <i class="ph ph-arrow-right"></i></button>
        </div>

      </div>

      <aside class="cotiz-preview">
        <div class="preview-header"><i class="ph ph-currency-dollar"></i><span>Cotización en tiempo real</span></div>

        <!-- Ruta, aeropuerto, incoterm y moneda -->
        <div class="preview-ruta-block">
          <div class="prb-ruta">
            <span class="eyebrow">Ruta</span>
            <strong id="prev-ruta">—</strong>
          </div>
          <div class="prb-moneda">
            <span id="prev-moneda">$ USD</span>
          </div>
        </div>
        <div class="preview-ruta-meta">
          <span class="prm-item"><i class="ph ph-airplane"></i><span id="prev-aeropuerto">—</span></span>
          <span class="prm-item"><i class="ph ph-clipboard-text"></i><span id="prev-incoterm">—</span></span>
        </div>

        <div class="preview-product-tag">
          <span class="eyebrow">Producto</span>
          <strong id="prev-producto">—</strong>
          <small id="prev-stems">0 tallos · 0 cajas</small>
        </div>

        <div class="preview-weight-row">
          <div><label>Peso real</label><span id="prev-peso-real">—</span></div>
          <div><label>Peso facturable</label><span id="prev-peso-vol">—</span></div>
        </div>

        <div class="preview-sections">
          <div class="ps-row ps-row--green"><span><i class="ph ph-flower"></i>S1 Valor producto</span><b id="prev-s1">$0.00</b></div>
          <div class="ps-row ps-row--amber"><span><i class="ph ph-file-text"></i>S2 Documentos</span><b id="prev-s2">$0.00</b></div>
          <div class="ps-row ps-row--blue"><span><i class="ph ph-airplane"></i>S3 Flete aéreo</span><b id="prev-s3">$0.00</b></div>
          <div class="ps-row ps-row--violet"><span><i class="ph ph-shield-check"></i>S4 Importación</span><b id="prev-s4">$0.00</b></div>
          <div class="ps-row ps-row--teal"><span><i class="ph ph-truck"></i>S5 Logística</span><b id="prev-s5">$0.00</b></div>
        </div>

        <div class="preview-total-block">
          <div class="ptb-total">
            <span>Total embarque</span>
            <strong id="prev-total">$0.00</strong>
          </div>
          <div class="ptb-per">
            <span id="prev-per-stem">$0.00/tallo</span>
            <span id="prev-per-box">$0.00/caja</span>
          </div>
        </div>

        <div class="preview-donut" id="prev-donut">
          <div class="donut-empty">Completa los pasos para ver el análisis</div>
        </div>

        <button class="btn btn-save" id="btn-guardar"><i class="ph ph-floppy-disk"></i> Guardar cotización</button>
      </aside>

    </div>`;

  // Bind listeners
  bindStep1(cat);
  bindStep2(cat);
  bindStep3(cat);
  bindStep4();
  bindStep5();

  // Navegación
  document.getElementById("btn-next").addEventListener("click", () => {
    if (state.step < TOTAL_STEPS) goStep(state.step + 1);
  });
  document.getElementById("btn-prev").addEventListener("click", () => {
    if (state.step > 1) goStep(state.step - 1);
  });
  document.querySelectorAll(".nav-dot").forEach((dot) => {
    dot.addEventListener("click", () => goStep(parseInt(dot.dataset.step)));
  });
  document.querySelectorAll(".step-indicator .step-item").forEach((it) => {
    it.addEventListener("click", () => goStep(parseInt(it.dataset.step)));
  });
  document.getElementById("btn-guardar").addEventListener("click", guardarCotizacion);

  updatePreview();

  // Stagger de entrada en los step items (una sola vez al cargar)
  document.querySelectorAll(".step-item").forEach((el, i) => {
    el.style.opacity = "0";
    el.style.transform = "translateY(6px)";
    el.style.transition = "opacity 220ms var(--ease-out), transform 220ms var(--ease-out)";
    setTimeout(() => {
      el.style.opacity = "";
      el.style.transform = "";
    }, 60 + i * 55);
  });
}

/* ─── Init ───────────────────────────────────────────────────────────── */
async function init() {
  const content = document.getElementById("content");
  content.innerHTML = `<div class="dashboard-loading"><span></span><p>Cargando catálogos...</p></div>`;

  try {
    const cat = await apiGet("/cotizacion/catalogo");
    _catalog = cat;
    state.catalogo = cat;

    // Tipo de cambio desde BD: tabla tiene columna usd_to_eur → invertir para eur_to_usd
    const latestFx = cat.exchange_rates?.[0];
    if (latestFx?.usd_to_eur && latestFx.usd_to_eur > 0) {
      state.eur_to_usd = parseFloat((1 / latestFx.usd_to_eur).toFixed(4));
    }

    renderPage(cat);

    // Aviso si no hay tarifas vigentes (debe ir después de renderPage que resetea innerHTML)
    if (!cat.rutas_activas?.length) {
      const banner = document.createElement("div");
      banner.className = "tariff-warning-banner";
      banner.innerHTML = `<i class="ph ph-warning-circle"></i>
        <span>No hay tarifas aéreas vigentes. Los selects de país y aerolínea estarán vacíos.
        Ve a <a href="/pages/tarifas-aerolinea.html">Tarifas Aerolínea</a> para cargar tarifas activas.</span>`;
      document.getElementById("content").prepend(banner);
    }
  } catch (err) {
    content.innerHTML = `
      <div class="dashboard-error">
        <strong>No se pudo cargar el cotizador</strong>
        <p>${err.message}</p>
        <button class="btn btn-primary" onclick="location.reload()">Reintentar</button>
      </div>`;
  }
}

init();
