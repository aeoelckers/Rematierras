let remates = [];
let rematesFiltrados = [];

const els = {
  tipoRemate: document.getElementById("tipo-remate"),
  region: document.getElementById("region"),
  comuna: document.getElementById("comuna"),
  fechaDesde: document.getElementById("fecha-desde"),
  fechaHasta: document.getElementById("fecha-hasta"),
  aplicar: document.getElementById("btn-aplicar"),
  results: document.getElementById("results"),
  resultCount: document.getElementById("result-count"),
  error: document.getElementById("error"),
  lastUpdate: document.getElementById("last-update"),
};

async function cargarDatos() {
  try {
    const res = await fetch("data/remates.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();

    remates = Array.isArray(payload) ? payload : (payload.records || []);
    rematesFiltrados = [...remates];

    poblarFiltros();
    renderizarResultados();

    if (payload.updated_at && els.lastUpdate) {
      els.lastUpdate.textContent = `Actualizado: ${payload.updated_at}`;
    }
  } catch (err) {
    console.error(err);
    if (els.error) {
      els.error.style.display = "block";
      els.error.textContent =
        "No se pudo cargar data/remates.json. Revisa que exista en la carpeta data/.";
    }
  }
}

function poblarFiltros() {
  const tipos = new Set();
  const regiones = new Set();
  const comunas = new Set();

  remates.forEach((r) => {
    if (r.tipo_bien) tipos.add(r.tipo_bien);
    if (r.region) regiones.add(r.region);
    if (r.comuna) comunas.add(r.comuna);
  });

  const fillSelect = (select, values, labelTodos) => {
    if (!select) return;
    select.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = labelTodos;
    select.appendChild(optAll);
    Array.from(values)
      .sort()
      .forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        select.appendChild(opt);
      });
  };

  fillSelect(els.tipoRemate, tipos, "Todos los tipos");
  fillSelect(els.region, regiones, "Todas las regiones");
  fillSelect(els.comuna, comunas, "Todas las comunas");
}

function aplicarFiltros() {
  const tipo = els.tipoRemate?.value || "";
  const region = els.region?.value || "";
  const comuna = els.comuna?.value || "";
  const desde = els.fechaDesde?.value || "";
  const hasta = els.fechaHasta?.value || "";

  rematesFiltrados = remates.filter((r) => {
    if (tipo && r.tipo_bien !== tipo) return false;
    if (region && r.region !== region) return false;
    if (comuna && r.comuna !== comuna) return false;

    let fechaBase = r.fecha_remate || r.fecha_publicacion;
    if (typeof fechaBase === "string") {
      // fecha_publicacion viene como YYYY-MM-DD, fecha_remate como ISO
      if (fechaBase.length === 10) {
        fechaBase = `${fechaBase}T00:00:00`;
      }
    }

    if (desde && fechaBase) {
      if (fechaBase < `${desde}T00:00:00`) return false;
    }
    if (hasta && fechaBase) {
      if (fechaBase > `${hasta}T23:59:59`) return false;
    }

    return true;
  });

  renderizarResultados();
}

function renderizarResultados() {
  if (!els.results) return;
  els.results.innerHTML = "";

  rematesFiltrados.forEach((r) => {
    const card = document.createElement("article");
    card.className = "remate-card";

    const fechaPub = r.fecha_publicacion || "-";
    const fechaRem = r.fecha_remate ? r.fecha_remate.slice(0, 16).replace("T", " ") : "Sin fecha";
    const valor = r.valor_minimo
      ? `$${r.valor_minimo.toLocaleString("es-CL")}`
      : "Sin mínimo";

    card.innerHTML = `
      <header class="remate-card__header">
        <h3>${r.tipo_bien || "Remate"} – ${r.deudor_nombre || "Deudor no indicado"}</h3>
        <span class="remate-card__tag">${r.tipo_procedimiento || ""}</span>
      </header>
      <p class="remate-card__meta">
        <strong>Publicación:</strong> ${fechaPub} |
        <strong>Remate:</strong> ${fechaRem}
      </p>
      <p class="remate-card__meta">
        <strong>Ubicación:</strong> ${r.region || "-"} / ${r.comuna || "-"}<br>
        <strong>Dirección:</strong> ${r.direccion || "-"}
      </p>
      <p class="remate-card__meta">
        <strong>Valor mínimo:</strong> ${valor}
      </p>
      <p class="remate-card__desc">
        ${r.descripcion || "(sin descripción disponible)"}
      </p>
      <footer class="remate-card__footer">
        <a class="btn-pdf" href="${r.fuente_url}" target="_blank" rel="noopener noreferrer">
          Ver PDF en Boletín Concursal
        </a>
      </footer>
    `;

    els.results.appendChild(card);
  });

  if (els.resultCount) {
    els.resultCount.textContent = `${rematesFiltrados.length} remates encontrados`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (els.aplicar) {
    els.aplicar.addEventListener("click", aplicarFiltros);
  }
  cargarDatos();
});
