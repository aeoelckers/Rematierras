// Rematierras - app.js (versión Boletín Concursal)
// En vez de leer data/remates.json, cargamos directamente desde
// https://www.boletinconcursal.cl/boletin/procedimientos

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

// ===================== CARGA DE DATOS ======================

// Versión que carga directamente desde Boletín Concursal
async function cargarDesdeBoletinConcursal() {
  const url = "https://www.boletinconcursal.cl/boletin/procedimientos";

  const res = await fetch(url, { mode: "cors" });
  if (!res.ok) throw new Error(`HTTP ${res.status} al consultar boletinconcursal`);

  const html = await res.text();

  // Parsear el HTML que llega
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  // ⚠️ IMPORTANTE:
  // Acá es donde hay que ajustar los selectores según la estructura real
  // de https://www.boletinconcursal.cl/boletin/procedimientos.
  //
  // Yo asumo que hay una tabla con filas <tr> que representan procedimientos.
  // Cambia 'table tbody tr' y los índices de celdas por lo que ya usaste en tu
  // proyecto rema-t (puedes copiar esos mismos selectores/celdas).

  const filas = doc.querySelectorAll("table tbody tr");
  const data = [];

  filas.forEach((tr, idx) => {
    const celdas = tr.querySelectorAll("td");
    if (celdas.length === 0) return;

    // EJEMPLO genérico: ajusta según la tabla real
    const tribunal = celdas[0]?.textContent.trim() || "";
    const rol = celdas[1]?.textContent.trim() || "";
    const deudor = celdas[2]?.textContent.trim() || "";
    const ciudad = celdas[3]?.textContent.trim() || "";
    const fechaTexto = celdas[4]?.textContent.trim() || "";

    // Fecha en formato "YYYY-MM-DD" si es posible
    let fechaISO = null;
    if (fechaTexto) {
      const partes = fechaTexto.split("-").map((p) => p.trim());
      if (partes.length === 3) {
        // asumo formato DD-MM-YYYY -> ajusta si es distinto
        const [dd, mm, yyyy] = partes;
        fechaISO = `${yyyy}-${mm}-${dd}`;
      }
    }

    // Link al detalle (si existe un <a> en alguna celda)
    const linkEl = tr.querySelector("a");
    const link =
      linkEl && linkEl.href ? linkEl.href : "https://www.boletinconcursal.cl/boletin/procedimientos";

    // Adaptamos al formato interno de Rematierras
    data.push({
      id: `boletin-${idx + 1}`,
      tipo_remate: "Boletín concursal",
      tipo_inmueble: "Procedimiento concursal", // por ahora usamos este texto
      region: "", // si de la tabla puedes distinguir región, ponla acá
      comuna: ciudad || "",
      fecha_remate: fechaISO, // se usa para los filtros de fecha
      precio_minimo: null,
      moneda: "",
      source: "boletin_concursal",
      source_url: link,
      // Campos extra que no usamos aún pero podrían servir
      tribunal,
      rol,
      deudor,
    });
  });

  return data;
}

// Cargar datos (para ahora usamos SIEMPRE boletin concursal)
async function cargarDatos() {
  try {
    remates = await cargarDesdeBoletinConcursal();
    rematesFiltrados = remates.slice();

    poblarFiltros();
    renderizarResultados();

    elements.lastUpdate.textContent =
      "Datos cargados en vivo desde boletinconcursal.cl (procedimientos concursales).";
  } catch (err) {
    console.error("Error cargando datos:", err);
    elements.error.style.display = "block";
    elements.error.textContent =
      "No se pudo cargar la información desde Boletín Concursal. Revisa la consola del navegador o CORS.";
  }
}

// ===================== FILTROS & RENDER ======================

function poblarFiltros() {
  const tiposRemate = new Set();
  const tiposInmueble = new Set();
  const regiones = new Set();

  remates.forEach((r) => {
    if (r.tipo_remate) tiposRemate.add(r.tipo_remate);
    if (r.tipo_inmueble) tiposInmueble.add(r.tipo_inmueble);
    if (r.region) regiones.add(r.region);
  });

  llenarSelect(elements.tipoRemate, tiposRemate, "Todos");
  llenarSelect(elements.tipoInmueble, tiposInmueble, "Todos");
  llenarSelect(elements.region, regiones, "Todas");
}

function llenarSelect(selectEl, valuesSet, defaultLabel) {
  const currentValue = selectEl.value;
  selectEl.innerHTML = `<option value="">${defaultLabel}</option>`;
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

function renderizarResultados() {
  elements.results.innerHTML = "";

  if (!rematesFiltrados.length) {
    elements.results.innerHTML =
      '<div class="empty-state">No se encontraron procedimientos con los filtros actuales.</div>';
    elements.resultCount.textContent = "0 resultados";
    return;
  }

  elements.resultCount.textContent =
    rematesFiltrados.length === 1
      ? "1 resultado encontrado"
      : `${rematesFiltrados.length} resultados encontrados`;

  rematesFiltrados.forEach((r) => {
    const card = document.createElement("article");
    card.className = "result-card";

    const titulo = document.createElement("div");
    titulo.className = "result-title";

    const tituloTexto = document.createElement("span");
    const tipoRemate = r.tipo_remate || "Procedimiento";
    const tipoInmueble = r.tipo_inmueble || "Concursal";
    const comuna = r.comuna || "Sin ciudad";
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
    regionSpan.textContent = `📍 ${r.comuna || "Sin ciudad"}`;

    const extraSpan = document.createElement("span");
    extraSpan.textContent = `⚖️ ${r.tribunal || ""} ${r.rol ? `(${r.rol})` : ""}`.trim();

    meta.appendChild(fechaSpan);
    meta.appendChild(regionSpan);
    meta.appendChild(extraSpan);

    const actions = document.createElement("div");
    actions.className = "result-actions";

    const leftInfo = document.createElement("div");
    leftInfo.className = "tiny-text";
    leftInfo.textContent = r.deudor ? `Deudor: ${r.deudor}` : `ID interno: ${r.id}`;

    const rightActions = document.createElement("div");
    rightActions.style.display = "flex";
    rightActions.style.gap = "0.4rem";

    if (r.source_url) {
      const link = document.createElement("a");
      link.href = r.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.className = "btn-link";
      link.textContent = "Ver procedimiento";
      rightActions.appendChild(link);
    }

    const pill = document.createElement("span");
    pill.className = "pill-small";
    pill.textContent = "Boletín concursal";

    rightActions.appendChild(pill);

    actions.appendChild(leftInfo);
    actions.appendChild(rightActions);

    card.appendChild(titulo);
    card.appendChild(meta);
    card.appendChild(actions);

    elements.results.appendChild(card);
  });
}

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
