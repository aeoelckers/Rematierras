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

// 👇 ESTA es la parte clave: lee SOLO el JSON local
async function cargarDatos() {
  try {
    const res = await fetch("data/remates.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    remates = await res.json();
    rematesFiltrados = [...remates];

    poblarFiltros();
    renderizarResultados();
    elements.lastUpdate.textContent = "Datos cargados desde data/remates.json";
  } catch (err) {
    console.error(err);
    elements.error.style.display = "block";
    elements.error.textContent =
      "No se pudo cargar data/remates.json. Revisa que exista y tenga formato JSON válido.";
  }
}

// … (de aquí hacia abajo dejas todo tu código de filtros y render tal como lo tenías)
elements.btnAplicar.addEventListener("click", () => aplicarFiltros());
cargarDatos();
