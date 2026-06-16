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

  // Paso 3 — Empaque
  box_type_id:      null,
  box_code:         "",
  length_cm:        100,
  width_cm:         50,
  height_cm:        20,
  stems_per_box:    150,
  kg_per_box:       14,
  cajas:            12,

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
  const total_stems      = s.stems_per_box * s.cajas;
  const total_kg_real    = s.kg_per_box    * s.cajas;

  const vol_weight_per_box = (s.length_cm * s.width_cm * s.height_cm) / s.vol_factor;
  const chargeable_per_box = Math.max(s.kg_per_box, vol_weight_per_box);
  const total_chargeable   = chargeable_per_box * s.cajas;

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
  const cost_per_box  = s.cajas    > 0 ? total_usd / s.cajas    : 0;

  return {
    total_stems, total_kg_real, vol_weight_per_box, chargeable_per_box, total_chargeable,
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

  document.getElementById("prev-total").textContent    = $money(c.total_usd);
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
  state.step = n;
  document.querySelectorAll(".step-panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".step-indicator .step-item").forEach((it) => {
    const sn = parseInt(it.dataset.step);
    it.classList.toggle("active",  sn === n);
    it.classList.toggle("visited", sn < n);
  });
  const panel = document.getElementById(`step-${n}`);
  if (panel) panel.classList.add("active");

  document.getElementById("btn-prev").disabled = n === 1;
  const btnNext = document.getElementById("btn-next");
  const dots    = document.querySelectorAll(".nav-dot");
  dots.forEach((d) => d.classList.toggle("active", parseInt(d.dataset.step) === n));

  if (n === TOTAL_STEPS) {
    btnNext.textContent = "Ver resumen ✓";
    btnNext.classList.add("btn-success");
  } else {
    btnNext.textContent = "Siguiente →";
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
      <span class="step-icon">🌍</span>
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

      <!-- Flecha visual origen → destino -->
      <div class="ruta-arrow">
        <div class="ruta-pais" id="ruta-orig-pill">
          <span class="ruta-flag" id="ruta-orig-flag">🌐</span>
          <span id="ruta-orig-label">Origen</span>
        </div>
        <div class="ruta-connector">✈ ──────────────</div>
        <div class="ruta-pais" id="ruta-dest-pill">
          <span class="ruta-flag" id="ruta-dest-flag">🌐</span>
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

      <!-- Aerolínea -->
      <div class="field-group">
        <label for="sel-aerolinea-ruta">Aerolínea</label>
        <select id="sel-aerolinea-ruta" disabled>
          <option value="">Selecciona los aeropuertos primero</option>
        </select>
      </div>

      <!-- Incoterm de venta -->
      <div class="field-group">
        <label for="sel-incoterm">Incoterm de venta</label>
        <select id="sel-incoterm">${incotermOpts}</select>
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
        💡 La moneda define cómo se presentan los totales en la cotización. Los cálculos internos se realizan en USD y se convierten con el tipo de cambio configurado en el Paso 5.
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
      <span class="step-icon">🌸</span>
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
        💡 Referencia Excel: Amaranthus $0.53 · Phlox $0.03 · Lisimachia $0.05
      </div>

    </div>
  </div>`;
}

/* ── PASO 2 (antes 3): Empaque ───────────────────────────────────────── */
function renderStep3(cat) {
  const cajasOpts = buildOptions(
    cat.box_types, (b) => b.id,
    (b) => `${b.box_code}${b.box_name ? ' — ' + b.box_name : ''} (${b.length_cm}×${b.width_cm}×${b.height_cm} cm${b.reference_weight_kg ? ', ref. ' + b.reference_weight_kg + ' kg' : ''})`,
    "Selecciona tipo de caja..."
  );

  return `
  <div class="step-card step-card--amber">
    <div class="step-card-header">
      <span class="step-icon">📦</span>
      <div>
        <h2>Configuración de empaque</h2>
        <p>Selecciona el tipo de caja y la cantidad del embarque</p>
      </div>
    </div>
    <div class="step-fields">

      <!-- Resumen de caja (primero) -->
      <div class="caja-info">
        <span class="caja-dim-badge">
          <b id="ci-code">—</b>
          <span id="ci-dims">Selecciona un tipo de caja</span>
        </span>
        <div class="caja-metrics">
          <div><label>Peso real/caja</label><strong id="ci-kg-ref">—</strong></div>
          <div><label>Peso volumétrico/caja</label><strong id="ci-vol-w">—</strong></div>
          <div><label>Peso facturable/caja</label><strong id="ci-fact">—</strong></div>
        </div>
      </div>

      <!-- Tipo de caja -->
      <div class="field-group">
        <label for="sel-caja">Tipo de caja</label>
        <select id="sel-caja">${cajasOpts}</select>
      </div>

      <!-- Número de cajas -->
      <div class="field-group">
        <label for="inp-cajas">Número de cajas: <strong id="cajas-display">${state.cajas}</strong></label>
        <div class="slider-wrap">
          <input type="range" id="inp-cajas" min="1" max="200" step="1" value="${state.cajas}" />
          <span class="slider-min">1</span>
          <span class="slider-max">200</span>
        </div>
        <div class="field-group" style="margin-top:8px">
          <input type="number" id="inp-cajas-num" min="1" max="999" value="${state.cajas}"
            placeholder="O ingresa el número directo" style="max-width:160px" />
        </div>
        <div class="derived-row">
          <span>Total tallos: <b id="der-total-stems">${(state.stems_per_box * state.cajas).toLocaleString("es-EC")}</b></span>
          <span>Peso total: <b id="der-total-kg">${$kg(state.kg_per_box * state.cajas)}</b></span>
        </div>
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
      <span class="step-icon">✈️</span>
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
        <div class="wc-header">⚖️ Cálculo de peso</div>
        <div class="wc-grid">
          <div class="wc-row"><span>Peso real total</span><strong id="wc-real">—</strong></div>
          <div class="wc-row"><span>Peso volumétrico total</span><strong id="wc-vol">—</strong></div>
          <div class="wc-row wc-highlight"><span>✦ Peso facturable (MAX)</span><strong id="wc-fact">—</strong></div>
          <div class="wc-row"><span>Costo de flete estimado</span><strong id="wc-cost">—</strong></div>
        </div>
      </div>

      <div class="field-note">
        💡 Referencia: Tarifa 2.73 EUR/kg all-in · Factor IATA estándar 6000
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
      <span class="step-icon">🏢</span>
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
        <div class="csb-header">📄 Sección 2 — Documentos de exportación</div>
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
        <div class="csb-header">🛃 Sección 4 — Derechos de importación</div>
        <div class="field-group">
          <label for="inp-fitosanitario">Fitosanitario (EUR)</label>
          <div class="input-prefix"><span>€</span>
            <input type="number" id="inp-fitosanitario" step="0.01" min="0" value="${state.fitosanitario_eur}" />
          </div>
        </div>
      </div>

      <div class="cost-section-block" style="--accent:#00897b">
        <div class="csb-header">🚚 Sección 5 — Logística en destino</div>
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

function updateAerolineasRuta(cat) {
  const sel    = document.getElementById("sel-aerolinea-ruta");
  if (!sel) return;
  const origId = state.aeropuerto_origen_id;
  const destId = state.aeropuerto_destino_id;

  if (!origId || !destId) {
    sel.innerHTML      = `<option value="">Selecciona los aeropuertos primero</option>`;
    sel.disabled       = true;
    state.aerolinea_id = null;
    return;
  }

  const airlineIds = new Set(
    (cat.rutas_activas ?? [])
      .filter((r) => r.origin_airport_id === origId && r.destination_airport_id === destId)
      .map((r) => r.airline_id)
  );
  const filtered = (cat.aerolineas ?? []).filter((a) => airlineIds.has(a.id));

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

function bindStep1(cat) {
  const FLAG = { EC:"🇪🇨", NL:"🇳🇱", DE:"🇩🇪", ES:"🇪🇸", US:"🇺🇸" };

  const selOrig = document.getElementById("sel-pais-origen");
  const selDest = document.getElementById("sel-pais-destino");

  selOrig.addEventListener("change", () => {
    const p = cat.paises_origen.find((x) => x.id === selOrig.value);
    state.pais_origen_id     = selOrig.value || null;
    state.pais_origen_nombre = p?.name || "";
    document.getElementById("ruta-orig-flag").textContent  = FLAG[p?.code] || "🌐";
    document.getElementById("ruta-orig-label").textContent = p?.name || "Origen";

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
    document.getElementById("ruta-dest-flag").textContent  = FLAG[p?.code] || "🌐";
    document.getElementById("ruta-dest-label").textContent = p?.name || "Destino";

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
    document.getElementById("ruta-orig-flag").textContent  = FLAG["EC"];
    document.getElementById("ruta-orig-label").textContent = ecuador.name;

    // Cargar aeropuertos de Ecuador
    const selAeroOrig  = document.getElementById("sel-aeropuerto-origen");
    const airportsEc   = cat.aeropuertos.filter((a) => a.country_id === ecuador.id);
    if (airportsEc.length > 0) {
      selAeroOrig.innerHTML = buildOptions(airportsEc, (a) => a.iata_code, (a) => `${a.iata_code} · ${a.city} — ${a.airport_name}`, "Selecciona aeropuerto...");
      selAeroOrig.disabled  = false;
    }
  }
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
  const selCaja = document.getElementById("sel-caja");

  function updateCajaInfo() {
    const caja = cat.box_types.find((b) => b.id === selCaja.value);
    if (!caja) return;
    state.box_type_id = caja.id;
    state.box_code    = caja.box_code;
    state.length_cm   = caja.length_cm;
    state.width_cm    = caja.width_cm;
    state.height_cm   = caja.height_cm;
    // Peso por caja desde la tabla (valor por defecto)
    if (caja.reference_weight_kg) state.kg_per_box = parseFloat(caja.reference_weight_kg);

    document.getElementById("ci-code").textContent = caja.box_code;
    document.getElementById("ci-dims").textContent = `${caja.length_cm} × ${caja.width_cm} × ${caja.height_cm} cm`;
    refreshWeightBadges();
    updateDerived();
    updatePreview();
  }

  function refreshWeightBadges() {
    const vol  = (state.length_cm * state.width_cm * state.height_cm) / state.vol_factor;
    const fact = Math.max(state.kg_per_box, vol);
    const kgEl = document.getElementById("ci-kg-ref");
    const vEl  = document.getElementById("ci-vol-w");
    const fEl  = document.getElementById("ci-fact");
    if (kgEl) kgEl.textContent = $kg(state.kg_per_box);
    if (vEl)  vEl.textContent  = $kg(vol);
    if (fEl)  fEl.textContent  = $kg(fact);
  }

  function updateDerived() {
    const ts = document.getElementById("der-total-stems");
    const tk = document.getElementById("der-total-kg");
    if (ts) ts.textContent = (state.stems_per_box * state.cajas).toLocaleString("es-EC");
    if (tk) tk.textContent = $kg(state.kg_per_box * state.cajas);
  }

  selCaja.addEventListener("change", updateCajaInfo);

  // Slider de cajas
  document.getElementById("inp-cajas").addEventListener("input", (e) => {
    state.cajas = parseInt(e.target.value) || 1;
    document.getElementById("cajas-display").textContent = state.cajas;
    const num = document.getElementById("inp-cajas-num");
    if (num) num.value = state.cajas;
    updateDerived(); updatePreview();
  });

  // Input numérico directo
  document.getElementById("inp-cajas-num").addEventListener("input", (e) => {
    const v = parseInt(e.target.value) || 1;
    state.cajas = v;
    document.getElementById("cajas-display").textContent = v;
    const slider = document.getElementById("inp-cajas");
    if (slider) slider.value = Math.min(v, 200);
    updateDerived(); updatePreview();
  });
}

function bindStep4() {
  function refreshWeightCalc() {
    const c = calcular();
    const wR = document.getElementById("wc-real");
    const wV = document.getElementById("wc-vol");
    const wF = document.getElementById("wc-fact");
    const wC = document.getElementById("wc-cost");
    if (wR) wR.textContent = $kg(c.total_kg_real);
    if (wV) wV.textContent = $kg(c.vol_weight_per_box * state.cajas);
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
  btn.textContent = "✅ Guardado";
  btn.disabled    = true;
  setTimeout(() => { btn.textContent = "💾 Guardar cotización"; btn.disabled = false; }, 2000);
}

/* ─── Render principal de la página ─────────────────────────────────── */
function renderPage(cat) {
  const content = document.getElementById("content");

  const steps = [
    { n:1, icon:"🌍", label:"Ruta",       color:"teal"   },
    { n:2, icon:"📦", label:"Empaque",    color:"amber"  },
    { n:3, icon:"🌸", label:"Producto",   color:"green"  },
    { n:4, icon:"✈️", label:"Ruta aérea", color:"blue"  },
    { n:5, icon:"🏢", label:"Costos",     color:"violet" },
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
        <span class="eyebrow">Costing Engine</span>
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
          <button id="btn-prev" class="btn btn-secondary" disabled>← Anterior</button>
          <div class="step-nav-dots">${dotsHTML}</div>
          <button id="btn-next" class="btn btn-primary">Siguiente →</button>
        </div>

      </div>

      <aside class="cotiz-preview">
        <div class="preview-header"><span>💰 Cotización en tiempo real</span></div>

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
          <span class="prm-item">✈ <span id="prev-aeropuerto">—</span></span>
          <span class="prm-item">📋 <span id="prev-incoterm">—</span></span>
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
          <div class="ps-row ps-row--green"><span>🌸 S1 Valor producto</span><b id="prev-s1">$0.00</b></div>
          <div class="ps-row ps-row--amber"><span>📄 S2 Documentos</span><b id="prev-s2">$0.00</b></div>
          <div class="ps-row ps-row--blue"><span>✈️ S3 Flete aéreo</span><b id="prev-s3">$0.00</b></div>
          <div class="ps-row ps-row--violet"><span>🛃 S4 Importación</span><b id="prev-s4">$0.00</b></div>
          <div class="ps-row ps-row--teal"><span>🚚 S5 Logística</span><b id="prev-s5">$0.00</b></div>
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

        <button class="btn btn-save" id="btn-guardar">💾 Guardar cotización</button>
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
}

/* ─── Init ───────────────────────────────────────────────────────────── */
async function init() {
  const content = document.getElementById("content");
  content.innerHTML = `<div class="dashboard-loading"><span></span><p>Cargando catálogos...</p></div>`;

  try {
    const cat = await apiGet("/cotizacion/catalogo");
    state.catalogo = cat;

    // Tipo de cambio desde BD: tabla tiene columna usd_to_eur → invertir para eur_to_usd
    const latestFx = cat.exchange_rates?.[0];
    if (latestFx?.usd_to_eur && latestFx.usd_to_eur > 0) {
      state.eur_to_usd = parseFloat((1 / latestFx.usd_to_eur).toFixed(4));
    }

    renderPage(cat);
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
