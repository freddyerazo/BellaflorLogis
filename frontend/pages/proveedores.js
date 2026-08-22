import { apiGet } from "/js/api.js";

const api = {
  categorias: () => apiGet("/proveedores/categorias"),
  exportadores: (params) => apiGet(`/proveedores/exportadores?${new URLSearchParams(params)}`),
};

const $ = (sel) => document.querySelector(sel);

let ultimaLista = [];

function mostrarMensaje(mensaje, clase = "msg-info") {
  const div = $("#resultado");
  div.innerHTML = "";
  const p = document.createElement("p");
  p.className = clase;
  p.textContent = mensaje;
  div.appendChild(p);
}

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

function renderTabla(lista) {
  const div = $("#resultado");
  div.innerHTML = "";

  if (!Array.isArray(lista) || lista.length === 0) {
    mostrarMensaje("Sin proveedores para esta búsqueda.", "msg-info");
    return;
  }

  const conteo = document.createElement("p");
  conteo.className = "conteo";
  conteo.textContent = `${lista.length} proveedor(es)`;
  div.appendChild(conteo);

  const tabla = document.createElement("table");
  tabla.className = "data-table";

  const columnas = ["Proveedor", "País", "Contacto", "Teléfono", "Productos", "Web"];
  const thead = tabla.createTHead().insertRow();
  columnas.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = c;
    thead.appendChild(th);
  });

  const tbody = tabla.createTBody();
  lista.forEach((p) => {
    const tr = tbody.insertRow();
    tr.insertCell().textContent = p.nombre || "";
    tr.insertCell().textContent = p.pais || "";

    const cContacto = tr.insertCell();
    if (p.contacto && p.contacto.includes("@")) {
      const a = document.createElement("a");
      a.href = `mailto:${p.contacto}`;
      a.textContent = p.contacto;
      cContacto.appendChild(a);
    } else {
      cContacto.textContent = p.contacto || "";
    }

    tr.insertCell().textContent = p.telefono || "";

    const cProd = tr.insertCell();
    cProd.textContent = p.productos || "";
    cProd.title = p.productos || "";
    cProd.className = "celda-productos";

    const cWeb = tr.insertCell();
    if (p.paginaWeb) {
      const a = document.createElement("a");
      a.href = p.paginaWeb.startsWith("http") ? p.paginaWeb : `https://${p.paginaWeb}`;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "Sitio";
      cWeb.appendChild(a);
    }
  });

  div.appendChild(tabla);
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
    aplicarFiltroPais();
  } catch (err) {
    mostrarMensaje(`Error: ${err.message}`, "msg-error");
  } finally {
    $("#btn-consultar").disabled = false;
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
  // Conservar el pais elegido si sigue presente en los nuevos resultados.
  if (previo && paises.includes(previo)) select.value = previo;
}

function aplicarFiltroPais() {
  const pais = $("#filtro-pais").value;
  const visible = pais ? ultimaLista.filter((p) => p.pais === pais) : ultimaLista;
  renderTabla(visible);
  actualizarKpis(visible);
}

function init() {
  cargarCategorias();
  $("#btn-consultar").addEventListener("click", consultar);
  $("#filtro-pais").addEventListener("change", aplicarFiltroPais);
  [$("#filtro-exportador"), $("#filtro-producto")].forEach((el) =>
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") consultar();
    })
  );
}

init();
