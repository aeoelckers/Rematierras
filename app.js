// =============================
// Rematierras - Versión Boletín Concursal (Remates)
// Lee datos directamente desde:
// https://www.boletinconcursal.cl/boletin/remates
// =============================

// Elementos UI
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

let remates = [];
let rematesFiltrados = [];

// =============================
// 1. Cargar datos desde Boletín Concursal
// =============================

async function cargarDesdeBoletinConcursal() {
  const url = "https://www.boletinconcursal.cl/boletin/remates";

  // Hacemos un fetch común: Boletín Concursal permite esto
  const res = await fetch(url, { mode: "cors" });
  const html = await res.text();

  // Parseo HTML
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // Seleccionamos las filas reales de la tabla
  const filas = doc.querySelectorAll("table tbody tr");

  const data = [];

  filas.forEach((tr, idx) => {
    const celdas = tr.querySelectorAll("td");
    if (celdas.length < 4) return;

    // Columnas reales:
    // 0 = Deudor
    // 1 = Fecha
    // 2 = Martillero
    // 3 = Documento (PDF con link)

    const deudor = celdas[0]?.textContent.trim() || "";
    const fechaTexto = celdas[1]?.textContent.trim() || "";
    const martillero = celdas[2]?.textContent.trim() || "";

    // Link del PDF
    let link = "";
    const pdfEl = celdas[3]?.querySelector("a");
    if (pdfEl && pdfEl.href) link = pdfEl.href;

    // Convertir fecha DD-MM-YYYY → YYYY-MM-DD
    let fechaISO = null;
    if (fechaTexto.includes("-")) {
      const [dd, mm, yyyy] = fechaTexto.split("-");
      fechaISO = `${yyyy}-${mm}-${dd}`;
    }

    // Agregar al formato Rematierras
    data.push({
      id: `boletin-${idx + 1}`,
      tipo_remate: "Remate concursal",
      tipo_inmueble: "Bien mueble",
      region: "",
      comuna: "",
      fecha_remate: fechaISO,
      precio_minimo: null,
      moneda: "",
      source: "boletin_concursal",
      source_url: link,
      deudor,
      martillero,
    });
  });

  return data;
}

// =============================
// 2. Cargar datos para Rematierras
// =============================

async function cargarDatos() {
  try {
    remates = await cargarDesdeBoletinConcursal();
    rematesFiltrados = [...remates];

    poblarFiltros();
    renderizarResultados();

    elements.lastUpdate.textContent =
      "Datos cargados directamente desde Boletín Concursal (Remates).";
  } catch (err) {
    console.error("Error cargando datos:", err);
    elements.error.style.display = "block";
    elements.error.textContent =
      "No se pudo cargar información desde Boletín Concursal.";
  }
}

// =============================
// 3. Filtros
// =============================

function poblarFiltros() {
  const tiposRemate = new Set();
  const tiposInmueble = new Set();

  remates.forEach((r) => {
    if (r.tipo_remate) tiposRemate.add(r.tipo_remate);
    if (r.tipo_inmueble) tiposInmueble.add(r.tipo_inmueble);
  });

  llenarSelect(elements.tipoRemate, tiposRemate, "Todos");
  llenarSelect(elements.tipoInmueble, tiposInmueble, "Todos");
}

function llenarSelect(selectEl, valuesSet, defaultLabel) {
  selectEl.innerHTML = `<option value="">${defaultLabel}</option>`;
  Array.from(valuesSet)
    .sort()
    .forEach((val) => {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      selectEl.appendChild(opt);
    });
}

function aplicarFiltros() {
  const tipoRemate = elements.tipoRemate.value;
  const tipoInmueble = elements.tipoInmueble.value;
  const comunaInput = elements.comuna.value.trim().toLowerCase();
  const fechaDesde = elements.fechaDesde.value;
  const fechaHasta = elements.fechaHasta.value;

  rematesFiltrados = remates.filter((r) => {
    if (tipoRemate && r.tipo_remate !== tipoRemate) return false;
    if (tipoInmueble && r.tipo_inmueble !== tipoInmueble) return false;

    if (comunaInput) {
      const comuna = (r.comuna || "").toLowerCase();
      if (!comuna.includes(comunaInput)) return false;
    }

    if (fechaDesde) {
      const d1 = new Date(fechaDesde);
      const dR = new Date(r.fecha_remate);
      if (dR < d1) return false;
    }

    if (fechaHasta) {
      const d2 = new Date(fechaHasta);
      const dR = new Date(r.fecha_remate);
      if (dR > d2) return false;
    }

    return true;
  });

  renderizarResultados();
}

// =============================
// 4. Renderizado
// =============================

function renderizarResultados() {
  elements.results.innerHTML = "";

  if (!rematesFiltrados.length) {
    elements.resultCount.textContent = "0 resultados";
    elements.results.innerHTML =
      '<div class="empty-state">No se encontraron remates.</div>';
    return;
  }

  elements.resultCount.textContent =
    rematesFiltrados.length === 1
      ? "1 resultado"
      : `${rematesFiltrados.length} resultados`;

  rematesFiltrados.forEach((r) => {
    const card = document.createElement("article");
    card.className = "result-card";

    const title = document.createElement("div");
    title.className = "result-title";
    title.innerHTML = `
      <span>${r.tipo_remate} – ${r.deudor}</span>
      <span class="badge green">Boletín</span>
    `;

    const meta = document.createElement("div");
    meta.className = "result-meta";
    meta.innerHTML = `
      <span>📅 ${formatoFecha(r.fecha_remate)}</span>
      <span>🔨 Martillero: ${r.martillero || "N/D"}</span>
    `;

    const actions = document.createElement("div");
    actions.className = "result-actions";

    const left = document.createElement("div");
    left.textContent = `ID interno: ${r.id}`;

    const right = document.createElement("div");
    right.style.display = "flex";
    right.style.gap = "0.5rem";

    if (r.source_url) {
      const link = document.createElement("a");
      link.href = r.source_url;
      link.target = "_blank";
      link.className = "btn-link";
      link.textContent = "Ver PDF";
      right.appendChild(link);
    }

    actions.appendChild(left);
    actions.appendChild(right);

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(actions);

    elements.results.appendChild(card);
  });
}

function formatoFecha(fecha) {
  if (!fecha) return "Fecha no disponible";
  const d = new Date(fecha);
  return d.toLocaleDateString("es-CL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// =============================
// 5. Inicio
// =============================

elements.btnAplicar.addEventListener("click", aplicarFiltros);
cargarDatos();
