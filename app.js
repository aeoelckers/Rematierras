// Rematierras - app.js
// MVP: carga un JSON local y permite filtrar remates.

let remates = [];
let rematesFiltrados = [];

const elements = {
  tipoRemate: document.getElementById("tipo-remate"),
  tipoInmueble: document.getElementById("tipo-inmueble"),
  region: document.getElementById("region"),
  comuna: document.getElementById("comuna"),
  fechaDesde: document.getElementById("fecha-desde"),
  fechaHasta: document.getElementById("fecha-hasta"),
  btnAplicar: document.getElementById("btn-aplicar"),
  results: document.getElementById("results"),
  resultCount: document.getElementById("result-count"),
  error: document.getElementById("error"),
  lastUpdate: document.getElementById("last-update"),
};

// Cargar datos desde data/remates.json
async function cargarDatos() {
  try {
    const res = await fetch("data/remates.json");
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    remates = Array.isArray(data) ? data : [];
    rematesFiltrados = remates.slice();

    poblarFiltros();
    renderizarResultados();

    elements.lastUpdate.textContent =
      "Datos de ejemplo cargados desde data/remates.json. Cuando tengamos scraper, se reemplaza por datos reales.";
  } catch (err) {
    console.error("Error cargando datos:", err);
    elements.error.style.display = "block";
    elements.error.textContent =
      "No se pudo cargar data/remates.json. Revisa la ruta, el archivo y GitHub Pages (HTTPS).";
  }
}

// Llena los select únicos a partir de la data
function poblarFiltros() {
  const tiposRemate = new Set();
  const tiposInmueble = new Set();
  const regiones = new Set();

  remates.forEach((r) => {
    if (r.tipo_remate) tiposRemate.add(r.tipo_remate);
    if (r.tipo_inmueble) tiposInmueble.add(r.tipo_inmueble);
    if (r.region) regiones.add(r.region);
  });

  llenarSelect(elements.tipoRemate, tiposRemate);
  llenarSelect(elements.tipoInmueble, tiposInmueble);
  llenarSelect(elements.region, regiones);
}

// Helper para llenar un select
function llenarSelect(selectEl, valuesSet) {
  const currentValue = selectEl.value;
  selectEl.innerHTML = "<option value=''>Todos</option>";
  Array.from(valuesSet)
    .sort((a, b) => a.localeCompare(b, "es"))
    .forEach((val) => {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      selectEl.appendChild(opt);
    });
  if (Array.from(valuesSet).includes(currentValue)) {
    selectEl.value = currentValue;
  }
}

// Aplica filtros sobre la lista original de remates
function aplicarFiltros() {
  const tipoRemate = elements.tipoRemate.value;
  const tipoInmueble = elements.tipoInmueble.value;
  const region = elements.region.value;
  const comunaInput = elements.comuna.value.trim().toLowerCase();
  const fechaDesde = elements.fechaDesde.value;
  const fechaHasta = elements.fechaHasta.value;

  rematesFiltrados = remates.filter((r) => {
    if (tipoRemate && r.tipo_remate !== tipoRemate) return false;
    if (tipoInmueble && r.tipo_inmueble !== tipoInmueble) return false;
    if (region && r.region !== region) return false;

    if (comunaInput) {
      const comunaRemate = (r.comuna || "").toLowerCase();
      if (!comunaRemate.includes(comunaInput)) return false;
    }

    if (fechaDesde) {
      const d1 = new Date(fechaDesde);
      const dRemate = new Date(r.fecha_remate);
      if (dRemate < d1) return false;
    }

    if (fechaHasta) {
      const d2 = new Date(fechaHasta);
      const dRemate = new Date(r.fecha_remate);
      if (dRemate > d2) return false;
    }

    return true;
  });

  renderizarResultados();
}

// Renderiza tarjetas de resultados
function renderizarResultados() {
  elements.results.innerHTML = "";

  if (!rematesFiltrados.length) {
    elements.results.innerHTML =
      '<div class="empty-state">No se encontraron remates con los filtros actuales. Prueba ampliando fechas, región o tipo de remate.</div>';
    elements.resultCount.textContent = "0 remates";
    return;
  }

  elements.resultCount.textContent =
    rematesFiltrados.length === 1
      ? "1 remate encontrado"
      : `${rematesFiltrados.length} remates encontrados`;

  rematesFiltrados.forEach((r) => {
    const card = document.createElement("article");
    card.className = "result-card";

    const titulo = document.createElement("div");
    titulo.className = "result-title";

    const tituloTexto = document.createElement("span");
    const tipoRemate = r.tipo_remate || "Remate";
    const tipoInmueble = r.tipo_inmueble || "Inmueble";
    const comuna = r.comuna || "Sin comuna";
    tituloTexto.textContent = `${tipoRemate} – ${tipoInmueble} – ${comuna}`;

    const badge = document.createElement("span");
    badge.className = "badge green";
    badge.textContent = r.source || "Fuente";

    titulo.appendChild(tituloTexto);
    titulo.appendChild(badge);

    const meta = document.createElement("div");
    meta.className = "result-meta";

    const fechaSpan = document.createElement("span");
    fechaSpan.textContent = `📅 ${formatoFecha(r.fecha_remate)}`;

    const regionSpan = document.createElement("span");
    regionSpan.textContent = `📍 ${(r.region || "Sin región") + (r.comuna ? `, ${r.comuna}` : "")}`;

    const precioSpan = document.createElement("span");
    const precio = r.precio_minimo != null ? r.precio_minimo : "S/I";
    const moneda = r.moneda || "";
    precioSpan.textContent = `💰 Base: ${precio} ${moneda}`.trim();

    meta.appendChild(fechaSpan);
    meta.appendChild(regionSpan);
    meta.appendChild(precioSpan);

    const actions = document.createElement("div");
    actions.className = "result-actions";

    const leftInfo = document.createElement("div");
    leftInfo.className = "tiny-text";
    leftInfo.textContent = r.id ? `ID interno: ${r.id}` : "ID sin definir";

    const rightActions = document.createElement("div");
    rightActions.style.display = "flex";
    rightActions.style.gap = "0.4rem";

    if (r.source_url) {
      const link = document.createElement("a");
      link.href = r.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.className = "btn-link";
      link.textContent = "Ver aviso";
      rightActions.appendChild(link);
    }

    const pill = document.createElement("span");
    pill.className = "pill-small";
    pill.textContent = r.tipo_remate || "Tipo desconocido";

    rightActions.appendChild(pill);

    actions.appendChild(leftInfo);
    actions.appendChild(rightActions);

    card.appendChild(titulo);
    card.appendChild(meta);
    card.appendChild(actions);

    elements.results.appendChild(card);
  });
}

// Formatea fechas tipo YYYY-MM-DD a algo legible
function formatoFecha(str) {
  if (!str) return "Fecha sin definir";
  const d = new Date(str);
  if (isNaN(d.getTime())) return str;
  return d.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Eventos
elements.btnAplicar.addEventListener("click", () => {
  aplicarFiltros();
});

// Inicializar
cargarDatos();
