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

async function cargarDatos() {
  try {
    const res = await fetch("data/remates.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    remates = await res.json();
    rematesFiltrados = [...remates];

    poblarFiltros();
    renderizarResultados();
    elements.lastUpdate.textContent = "Datos cargados desde data/remates.json (Boletín Concursal).";
  } catch (err) {
    console.error(err);
    elements.error.style.display = "block";
    elements.er
