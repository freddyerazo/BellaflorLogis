import { apiGet } from "/js/api.js";

const api = {
  categorias: () => apiGet("/proveedores/categorias"),
  exportadores: (params) => apiGet(`/proveedores/exportadores?${new URLSearchParams(params)}`),
};

const $ = (sel) => document.querySelector(sel);
const PAGE_SIZE = 50;

let ultimaLista = []; // resultado crudo de la consulta al gateway
let filtradas = []; // tras aplicar país + búsqueda en vivo
let pagina = 1;

// ---------- utilidades ----------
function mostrarMensaje(mensaje, clase = "msg-info") {
  $("#resultado").innerHTML = "";
  const p = document.createElement("p");
  p.className = clase;
  p.textContent = mensaje;
  $("#resultado").appendChild(p);
}

function banderaDe(codigo) {
  if (!codigo || codigo.length !== 2) return "";
  const base = 0x1f1e6;
  const cc = codigo.toUpperCase();
  return String.fromCodePoint(base + (cc.charCodeAt(0) - 65)) +
    String.fromCodePoint(base + (cc.charCodeAt(1) - 65));
}

function listaProductos(str) {
  return (str || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

// ---------- carga de categorías ----------
async function cargarCategorias() {
  const select = $("#filtro-categoria");
  try {
    const cats = await api.categorias();
    select.innerHTML = "";
    if (!Array.isArray(cats) || cats.length === 0) {
      select.innerHTML = `<option value="">(sin categorías)</option>`;
      return;
    }
    cats.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.nombre;
      const n = (c.nombre || "").toUpperCase();
      if (n.includes("FLORES FRESCAS") || n.includes("FRESH CUT")) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (err) {
    select.innerHTML = `<option value="">Error al cargar</option>`;
    mostrarMensaje(`No se pudieron cargar las categorías: ${err.message}`, "msg-error");
  }
}

function poblarPaises(lista) {
  const select = $("#filtro-pais");
  const previo = select.value;
  const paises = [...new Set(lista.map((p) => p.pais).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b)
  );
  select.innerHTML = `<option value="">Todos</option>`;
  paises.forEach((pais) => {
    const opt = document.createElement("option");
    opt.value = pais;
    opt.textContent = pais;
    select.appendChild(opt);
  });
  if (previo && paises.includes(previo)) select.value = previo;
}

// ---------- render de tabla + paginación ----------
function totalPaginas() {
  return Math.max(1, Math.ceil(filtradas.length / PAGE_SIZE));
}

function renderPagina() {
  const div = $("#resultado");
  div.innerHTML = "";

  if (filtradas.length === 0) {
    mostrarMensaje("Sin proveedores para esta búsqueda.", "msg-info");
    $("#pag-info").textContent = "";
    $("#pag-prev").disabled = true;
    $("#pag-next").disabled = true;
    return;
  }

  const inicio = (pagina - 1) * PAGE_SIZE;
  const pageItems = filtradas.slice(inicio, inicio + PAGE_SIZE);

  const cont = document.createElement("div");
  cont.className = "prov-tabla-scroll";

  const tabla = document.createElement("table");
  tabla.className = "data-table";

  const thead = tabla.createTHead().insertRow();
  ["Proveedor", "País", "Contacto", "Web"].forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    thead.appendChild(th);
  });

  const tbody = tabla.createTBody();
  pageItems.forEach((p, idx) => {
    const tr = tbody.insertRow();
    tr.className = "fila-prov";

    // Proveedor (con caret + nombre)
    const cNombre = tr.insertCell();
    cNombre.innerHTML = `<span class="prov-nombre"><i class="ph ph-caret-right prov-caret"></i>${
      (p.nombre || "").replace(/</g, "&lt;")
    }</span>`;

    // País (bandera + nombre)
    const cPais = tr.insertCell();
    const flag = banderaDe(p.codigoPais);
    cPais.innerHTML = `${flag ? `<span class="prov-flag">${flag}</span> ` : ""}${
      (p.pais || "").replace(/</g, "&lt;")
    }`;

    // Contacto (botones correo / teléfono)
    const cContacto = tr.insertCell();
    const acc = document.createElement("span");
    acc.className = "contacto-acciones";
    const correo = p.contacto && p.contacto.includes("@") ? p.contacto : null;
    const tel = (p.telefono || "").trim();
    acc.innerHTML =
      (correo
        ? `<a class="btn-icono" href="mailto:${correo}" title="${correo}" onclick="event.stopPropagation()"><i class="ph ph-envelope-simple"></i></a>`
        : `<span class="btn-icono disabled"><i class="ph ph-envelope-simple"></i></span>`) +
      (tel
        ? `<a class="btn-icono" href="tel:${tel.replace(/\s+/g, "")}" title="${tel}" onclick="event.stopPropagation()"><i class="ph ph-phone"></i></a>`
        : `<span class="btn-icono disabled"><i class="ph ph-phone"></i></span>`);
    cContacto.appendChild(acc);

    // Web
    const cWeb = tr.insertCell();
    if (p.paginaWeb) {
      const url = p.paginaWeb.startsWith("http") ? p.paginaWeb : `https://${p.paginaWeb}`;
      cWeb.innerHTML = `<a class="btn-icono" href="${url}" target="_blank" rel="noopener" title="${url}" onclick="event.stopPropagation()"><i class="ph ph-globe"></i></a>`;
    }

    // Fila de detalle (productos), oculta hasta hacer clic
    const trDet = tbody.insertRow();
    trDet.className = "detalle-prov";
    trDet.style.display = "none";
    const celda = trDet.insertCell();
    celda.colSpan = 4;
    const prods = listaProductos(p.productos);
    if (prods.length) {
      celda.innerHTML =
        `<div class="productos-chips">` +
        prods.map((x) => `<span class="producto-chip">${x.replace(/</g, "&lt;")}</span>`).join("") +
        `</div>`;
    } else {
      celda.innerHTML = `<span class="detalle-vacio">Sin productos registrados.</span>`;
    }

    tr.addEventListener("click", () => {
      const abierto = trDet.style.display !== "none";
      trDet.style.display = abierto ? "none" : "";
      tr.classList.toggle("abierta", !abierto);
    });
  });

  cont.appendChild(tabla);
  div.appendChild(cont);

  // info + botones de paginación
  const fin = Math.min(inicio + PAGE_SIZE, filtradas.length);
  $("#pag-info").textContent = `${inicio + 1}–${fin} de ${filtradas.length}`;
  $("#pag-prev").disabled = pagina <= 1;
  $("#pag-next").disabled = pagina >= totalPaginas();
}

function actualizarKpis(lista) {
  const tarjetas = $("#tarjetas");
  if (!Array.isArray(lista) || lista.length === 0) {
    tarjetas.classList.add("hidden");
    return;
  }
  const paises = new Set(lista.map((p) => p.pais).filter(Boolean));
  $("#kpi-proveedores").textContent = lista.length;
  $("#kpi-paises").textContent = paises.size;
  tarjetas.classList.remove("hidden");
}

// ---------- aplicar filtros de país + búsqueda en vivo ----------
function aplicarVista() {
  const pais = $("#filtro-pais").value;
  const q = $("#buscar-vivo").value.trim().toLowerCase();

  filtradas = ultimaLista.filter((p) => {
    if (pais && p.pais !== pais) return false;
    if (!q) return true;
    const blob = `${p.nombre || ""} ${p.pais || ""} ${p.contacto || ""} ${p.telefono || ""} ${p.productos || ""}`.toLowerCase();
    return blob.includes(q);
  });

  pagina = 1;
  actualizarKpis(filtradas);
  $("#toolbar").classList.toggle("hidden", ultimaLista.length === 0);
  renderPagina();
}

// ---------- consulta al gateway ----------
async function consultar() {
  const categoria = $("#filtro-categoria").value;
  if (!categoria) {
    mostrarMensaje("Elige una categoría de mercancía primero.", "msg-error");
    return;
  }
  const params = { categoria };
  const exportador = $("#filtro-exportador").value.trim();
  const producto = $("#filtro-producto").value.trim();
  if (exportador) params.exportador = exportador;
  if (producto) params.producto = producto;

  mostrarMensaje("Consultando proveedores…", "msg-info");
  $("#btn-consultar").disabled = true;
  try {
    const lista = await api.exportadores(params);
    ultimaLista = lista || [];
    poblarPaises(ultimaLista);
    aplicarVista();
  } catch (err) {
    ultimaLista = [];
    $("#toolbar").classList.add("hidden");
    mostrarMensaje(`Error: ${err.message}`, "msg-error");
  } finally {
    $("#btn-consultar").disabled = false;
  }
}

// ---------- init ----------
let debounce;
function init() {
  cargarCategorias();
  $("#btn-consultar").addEventListener("click", consultar);
  $("#filtro-pais").addEventListener("change", aplicarVista);
  $("#buscar-vivo").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(aplicarVista, 180);
  });
  $("#pag-prev").addEventListener("click", () => {
    if (pagina > 1) {
      pagina--;
      renderPagina();
    }
  });
  $("#pag-next").addEventListener("click", () => {
    if (pagina < totalPaginas()) {
      pagina++;
      renderPagina();
    }
  });
  [$("#filtro-exportador"), $("#filtro-producto")].forEach((el) =>
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") consultar();
    })
  );
}

init();
