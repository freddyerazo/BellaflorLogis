import { apiGet } from "../js/api.js";

/* ─── Módulos principales ─────────────────────────────────────────── */
const MODULES = [
  { key: "species",        label: "Especies",       description: "Catálogo floral",        href: "/pages/especies.html",    icon: "✦", tone: "green"   },
  { key: "varieties",      label: "Variedades",      description: "Portafolio disponible",  href: "/pages/variedades.html",  icon: "❋", tone: "emerald" },
  { key: "product_sizes",  label: "Grados",          description: "Clasificación comercial",href: "/pages/grados.html",      icon: "↕", tone: "amber"   },
  { key: "box_types",      label: "Tipos de caja",   description: "Opciones de empaque",    href: "/pages/tipos-caja.html",  icon: "□", tone: "orange"  },
  { key: "airports",       label: "Aeropuertos",     description: "Puntos logísticos",      href: "/pages/aeropuertos.html", icon: "⌁", tone: "blue"    },
  { key: "airlines",       label: "Aerolíneas",      description: "Socios de transporte",   href: "/pages/aerolineas.html",  icon: "➤", tone: "cyan"    },
  { key: "customers",      label: "Clientes",        description: "Cuentas comerciales",    href: "/pages/clientes.html",    icon: "◉", tone: "violet"  },
  { key: "markets",        label: "Mercados",        description: "Destinos comerciales",   href: "#",                       icon: "◈", tone: "teal"    },
  { key: "providers",      label: "Proveedores",     description: "Agentes de carga",       href: "#",                       icon: "◐", tone: "slate"   },
  { key: "incoterms",      label: "Incoterms",       description: "Términos de comercio",   href: "#",                       icon: "⊞", tone: "amber"   },
  { key: "cost_components",label: "Costos",          description: "Componentes de flete",   href: "#",                       icon: "⊟", tone: "orange"  },
  { key: "profiles",       label: "Usuarios",        description: "Accesos configurados",   href: "/pages/configuracion.html",icon: "◎", tone: "slate"  },
];

const fmt = (v) => new Intl.NumberFormat("es-EC").format(v ?? 0);
const fmtUSD = (v) => v != null ? `$${new Intl.NumberFormat("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v)}` : "—";
const fmtKg  = (v) => v != null ? `${new Intl.NumberFormat("es-EC", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v)} kg` : "—";

/* ─── Render principal ────────────────────────────────────────────── */
function renderDashboard({ summary, top_species, box_distribution, last_scenario, cost_breakdown }) {
  const content = document.getElementById("content");
  const s = summary;
  const totalCatalog   = (s.species ?? 0) + (s.varieties ?? 0) + (s.product_sizes ?? 0);
  const totalLogistics = (s.box_types ?? 0) + (s.airports ?? 0) + (s.airlines ?? 0);
  const maxVal = Math.max(...MODULES.map((m) => s[m.key] ?? 0), 1);
  const today  = new Intl.DateTimeFormat("es-EC", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());

  content.innerHTML = `
    <!-- Hero -->
    <section class="dashboard-hero">
      <div>
        <span class="eyebrow">Centro de operaciones</span>
        <h1>Visión general de BLIS</h1>
        <p>Control centralizado de catálogos, clientes y red logística de Bellaflor.</p>
      </div>
      <div class="hero-meta">
        <span class="status-pill"><i></i> Sistema operativo</span>
        <span class="hero-date">${today}</span>
      </div>
    </section>

    <!-- Métricas superiores -->
    <section class="metric-grid">
      <article class="metric-card metric-featured">
        <div class="metric-icon">❋</div>
        <div>
          <span>Variedades activas</span>
          <strong>${fmt(s.varieties)}</strong>
          <small>en ${fmt(s.species)} especies</small>
        </div>
        <a href="/pages/variedades.html" aria-label="Ver variedades">→</a>
      </article>
      <article class="metric-card">
        <div class="metric-icon blue">◉</div>
        <div>
          <span>Clientes</span>
          <strong>${fmt(s.customers)}</strong>
          <small>${fmt(s.markets)} mercados destino</small>
        </div>
        <a href="/pages/clientes.html" aria-label="Ver clientes">→</a>
      </article>
      <article class="metric-card">
        <div class="metric-icon amber">⌁</div>
        <div>
          <span>Red logística</span>
          <strong>${fmt(totalLogistics)}</strong>
          <small>${fmt(s.airports)} aeropuertos · ${fmt(s.airlines)} aerolíneas</small>
        </div>
        <a href="/pages/aeropuertos.html" aria-label="Ver red logística">→</a>
      </article>
      <article class="metric-card">
        <div class="metric-icon violet">⊞</div>
        <div>
          <span>Escenarios</span>
          <strong>${fmt(s.scenarios)}</strong>
          <small>${fmt(s.cost_components)} componentes de costo</small>
        </div>
        <a href="#costing-panel" aria-label="Ver costing">→</a>
      </article>
    </section>

    <!-- Columnas principales -->
    <div class="dashboard-columns">

      <!-- Panel izquierdo: módulos -->
      <section class="panel overview-panel">
        <div class="panel-heading">
          <div><span class="eyebrow">Datos maestros</span><h2>Resumen por módulo</h2></div>
          <span class="panel-total">${fmt(totalCatalog + totalLogistics + (s.customers ?? 0))} registros</span>
        </div>
        <div class="module-list">
          ${MODULES.map((m) => {
            const value = s[m.key] ?? 0;
            return `<a class="module-row" href="${m.href}">
              <span class="module-icon ${m.tone}">${m.icon}</span>
              <span class="module-info"><strong>${m.label}</strong><small>${m.description}</small></span>
              <span class="module-progress"><i style="width:${Math.max((value / maxVal) * 100, value ? 4 : 0)}%"></i></span>
              <b>${fmt(value)}</b>
            </a>`;
          }).join("")}
        </div>
      </section>

      <!-- Columna derecha -->
      <aside class="dashboard-side">

        <!-- Accesos rápidos -->
        <section class="panel quick-panel">
          <div class="panel-heading"><div><span class="eyebrow">Gestión</span><h2>Accesos rápidos</h2></div></div>
          <div class="quick-grid">
            <a href="/pages/clientes.html"><span>＋</span><strong>Nuevo cliente</strong><small>Registrar cuenta</small></a>
            <a href="/pages/variedades.html"><span>＋</span><strong>Nueva variedad</strong><small>Ampliar catálogo</small></a>
            <a href="/pages/aeropuertos.html"><span>＋</span><strong>Aeropuerto</strong><small>Agregar destino</small></a>
            <a href="/pages/configuracion.html"><span>⚙</span><strong>Configuración</strong><small>Roles y usuarios</small></a>
          </div>
        </section>

        <!-- Insight: promedio variedades/especie -->
        <section class="insight-card">
          <span class="eyebrow">Indicador de portafolio</span>
          <div class="insight-value">
            ${s.species ? Math.round((s.varieties ?? 0) / s.species) : 0}<small>variedades / especie</small>
          </div>
          <p>Promedio de variedades registradas por cada especie floral en el catálogo.</p>
          <a href="/pages/especies.html">Revisar catálogo <b>→</b></a>
        </section>

      </aside>
    </div>

    <!-- ═══ ANÁLISIS VISUAL ════════════════════════════════════════════ -->
    <h2 class="section-divider">Análisis</h2>

    <div class="analysis-grid">

      <!-- Top 5 especies por variedades -->
      <section class="panel analysis-panel">
        <div class="panel-heading">
          <div><span class="eyebrow">Catálogo</span><h2>Top 5 especies con más variedades</h2></div>
        </div>
        <div class="chart-bars">
          ${(() => {
            if (!top_species?.length) return `<p class="chart-empty">Sin datos</p>`;
            const maxS = Math.max(...top_species.map((r) => r.variety_count), 1);
            return top_species.map((r, i) => `
              <div class="bar-row">
                <span class="bar-label">${r.species_name}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="width:${Math.max((r.variety_count / maxS) * 100, 4)}%;animation-delay:${i * 80}ms"></div>
                </div>
                <b>${fmt(r.variety_count)}</b>
              </div>`).join("");
          })()}
        </div>
      </section>

      <!-- Tipos de caja -->
      <section class="panel analysis-panel">
        <div class="panel-heading">
          <div><span class="eyebrow">Empaque</span><h2>Tipos de caja disponibles</h2></div>
        </div>
        <div class="box-grid">
          ${(() => {
            if (!box_distribution?.length) return `<p class="chart-empty">Sin datos</p>`;
            const colors = ["#2e7d32","#1565c0","#7b1fa2","#e65100","#00695c","#6d4c41","#37474f","#c62828"];
            return box_distribution.map((b, i) => `
              <div class="box-chip" style="border-color:${colors[i % colors.length]}22;background:${colors[i % colors.length]}0d">
                <strong style="color:${colors[i % colors.length]}">${b.box_code}</strong>
                <span>${b.box_name ?? ""}</span>
                <small>${b.length_cm} × ${b.width_cm} × ${b.height_cm} cm</small>
              </div>`).join("");
          })()}
        </div>
      </section>

    </div>

    <!-- ═══ COSTING ENGINE ═════════════════════════════════════════════ -->
    <h2 class="section-divider" id="costing-panel">Costing Engine</h2>

    ${last_scenario ? `
    <div class="costing-grid">

      <!-- Resumen del último escenario -->
      <section class="panel costing-summary-panel">
        <div class="panel-heading">
          <div>
            <span class="eyebrow">Último escenario calculado</span>
            <h2>${last_scenario.scenario_name ?? last_scenario.scenario_code}</h2>
          </div>
          <span class="scenario-code-badge">${last_scenario.scenario_code}</span>
        </div>
        <div class="costing-kpis">
          <div class="kpi-item">
            <span>Cajas totales</span>
            <strong>${fmt(last_scenario.total_boxes)}</strong>
          </div>
          <div class="kpi-item">
            <span>Peso facturable</span>
            <strong>${fmtKg(last_scenario.total_chargeable_kg)}</strong>
          </div>
          <div class="kpi-item kpi-highlight">
            <span>Costo total estimado</span>
            <strong>${fmtUSD(last_scenario.total_cost_usd)}</strong>
          </div>
          ${last_scenario.total_boxes && last_scenario.total_cost_usd ? `
          <div class="kpi-item">
            <span>Costo por caja</span>
            <strong>${fmtUSD(last_scenario.total_cost_usd / last_scenario.total_boxes)}</strong>
          </div>` : ""}
        </div>
      </section>

      <!-- Desglose de costos -->
      <section class="panel costing-breakdown-panel">
        <div class="panel-heading">
          <div><span class="eyebrow">Desglose</span><h2>Componentes de costo</h2></div>
        </div>
        <div class="cost-breakdown-list">
          ${(() => {
            if (!cost_breakdown?.length) return `<p class="chart-empty">Sin componentes registrados</p>`;
            const total = cost_breakdown.reduce((a, c) => a + (c.amount ?? 0), 0);
            return cost_breakdown.map((c) => {
              const pct = total > 0 ? Math.round((c.amount / total) * 100) : 0;
              return `
              <div class="cost-row">
                <span class="cost-name">${c.component_name}</span>
                <div class="cost-track">
                  <div class="cost-bar" style="width:${Math.max(pct, 2)}%"></div>
                </div>
                <span class="cost-pct">${pct}%</span>
                <b class="cost-amount">${fmtUSD(c.amount)}</b>
              </div>`;
            }).join("");
          })()}
        </div>
      </section>

    </div>
    ` : `
    <section class="panel costing-empty">
      <span class="eyebrow">Costing Engine</span>
      <p>No hay escenarios calculados aún. Cuando se registre el primer escenario aparecerá aquí el análisis de costos.</p>
    </section>
    `}
  `;
}

/* ─── Init ────────────────────────────────────────────────────────── */
async function init() {
  const content = document.getElementById("content");
  content.innerHTML = `<div class="dashboard-loading"><span></span><p>Preparando tu panel de control...</p></div>`;
  try {
    renderDashboard(await apiGet("/dashboard/summary"));
  } catch (err) {
    content.innerHTML = `<div class="dashboard-error">
      <strong>No se pudo cargar el dashboard</strong>
      <p>${err.message}</p>
      <button class="btn btn-primary" onclick="location.reload()">Reintentar</button>
    </div>`;
  }
}

init();
