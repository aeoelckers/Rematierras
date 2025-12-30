// --- Referencias a elementos del DOM --- //
const els = {
  tipoRemate: document.getElementById("tipo-remate"),
  region: document.getElementById("region"),
  comuna: document.getElementById("comuna"),
  fechaDesde: document.getElementById("fecha-desde"),
  fechaHasta: document.getElementById("fecha-hasta"),
  busqueda: document.getElementById("busqueda-palabras"),
  aplicar: document.getElementById("btn-aplicar"),
  results: document.getElementById("results"),
  resultCount: document.getElementById("result-count"),
  error: document.getElementById("error"),
  lastUpdate: document.getElementById("last-update"),
  modal: document.getElementById("modal-remate"),
  modalTitle: document.getElementById("modal-titulo"),
  modalInfo: document.getElementById("modal-info"),
  modalDescripcion: document.getElementById("modal-descripcion"),
};

let remates = [];
let rematesFiltrados = [];

// --- Cargar datos desde data/remates.json --- //
async function cargarDatos() {
  try {
    const res = await fetch("data/remates.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const payload = await res.json();

    // Soportar dos formatos:
    // - array simple
    // - objeto { records: [...] }
    if (Array.isArray(payload)) {
      remates = payload;
    } else if (Array.isArray(payload.records)) {
      remates = payload.records;
    } else {
      remates = [];
    }

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
        "No se pudo cargar data/remates.json. Verifica que exista y tenga formato correcto.";
    }
  }
}

// --- Poblar selects de tipo, región, comuna --- //
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
      .sort((a, b) => a.localeCompare(b, "es-CL"))
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

// --- Aplicar filtros --- //
function aplicarFiltros() {
  const tipo = els.tipoRemate?.value || "";
  const region = els.region?.value || "";
  const comuna = els.comuna?.value || "";
  const desde = els.fechaDesde?.value || ""; // formato YYYY-MM-DD
  const hasta = els.fechaHasta?.value || "";
  const busqueda = els.busqueda?.value || "";
  const palabras = busqueda
    .toLowerCase()
    .split(/\s+/)
    .map((p) => p.trim())
    .filter(Boolean);

  rematesFiltrados = remates.filter((r) => {
    if (tipo && r.tipo_bien !== tipo) return false;
    if (region && r.region !== region) return false;
    if (comuna && r.comuna !== comuna) return false;

    // fecha_remate (ISO) o fecha_publicacion (YYYY-MM-DD)
    let fechaBase = r.fecha_remate || r.fecha_publicacion;
    if (!fechaBase) return true;

    // Normalizamos a string ISO comparable
    if (typeof fechaBase === "string") {
      if (fechaBase.length === 10) {
        // YYYY-MM-DD
        fechaBase = `${fechaBase}T00:00:00`;
      }
    }

    if (desde && fechaBase < `${desde}T00:00:00`) return false;
    if (hasta && fechaBase > `${hasta}T23:59:59`) return false;

    if (palabras.length > 0) {
      const texto =
        [
          r.tipo_bien,
          r.deudor_nombre,
          r.region,
          r.comuna,
          r.direccion,
          r.tipo_procedimiento,
          r.procedimiento,
          r.fecha_publicacion,
          r.fecha_remate,
          r.valor_minimo,
          r.descripcion,
          r.tipo_bienes,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

      const todasIncluidas = palabras.every((palabra) =>
        texto.includes(palabra)
      );
      if (!todasIncluidas) return false;
    }

    return true;
  });

  renderizarResultados();
}

// --- Render de tarjetas --- //
function renderizarResultados() {
  if (!els.results) return;

  els.results.innerHTML = "";

  rematesFiltrados.forEach((r, index) => {
    const card = document.createElement("article");
    card.className = "remate-card";

    const tipoBien = r.tipo_bien || "Remate";
    const deudor = r.deudor_nombre || "Deudor no indicado";
    const region = r.region || "-";
    const comuna = r.comuna || "-";
    const direccion = r.direccion || "-";
    const proc = r.tipo_procedimiento || r.procedimiento || "";
    const fechaPub = r.fecha_publicacion || "-";
    const fechaRem = r.fecha_remate
      ? r.fecha_remate.slice(0, 16).replace("T", " ")
      : "Sin fecha remate";

    const valor = r.valor_minimo
      ? `$${Number(r.valor_minimo).toLocaleString("es-CL")}`
      : "Sin mínimo publicado";

    const descripcion =
      r.descripcion || r.tipo_bienes || "(sin descripción disponible)";

    const urlPdf = r.fuente_url || "#";

    card.innerHTML = `
      <header class="remate-card__header">
        <h3>${tipoBien} – ${deudor}</h3>
        ${
          proc
            ? `<span class="remate-card__tag">${proc}</span>`
            : ""
        }
      </header>

      <p class="remate-card__meta">
        <strong>Publicación:</strong> ${fechaPub} |
        <strong>Remate:</strong> ${fechaRem}
      </p>
      <p class="remate-card__meta">
        <strong>Ubicación:</strong> ${region} / ${comuna}<br>
        <strong>Dirección:</strong> ${direccion}
      </p>
      <p class="remate-card__meta">
        <strong>Valor mínimo:</strong> ${valor}
      </p>
      <p class="remate-card__desc">
        ${descripcion}
      </p>
      <footer class="remate-card__footer">
        <a
          class="btn-pdf"
          href="#"
          data-index="${index}"
          role="button"
        >
          Ver detalle del remate
        </a>
      </footer>
    `;

    els.results.appendChild(card);
  });

  if (els.resultCount) {
    els.resultCount.textContent = `${rematesFiltrados.length} remates encontrados`;
  }
}

function abrirModalRemate(remate) {
  if (!els.modal || !els.modalTitle || !els.modalInfo || !els.modalDescripcion) {
    return;
  }

  const tipoBien = remate.tipo_bien || "Remate";
  const deudor = remate.deudor_nombre || "Deudor no indicado";
  els.modalTitle.textContent = `${tipoBien} – ${deudor}`;

  const campos = [
    { label: "Publicación", value: remate.fecha_publicacion },
    { label: "Remate", value: remate.fecha_remate },
    { label: "Tipo procedimiento", value: remate.tipo_procedimiento },
    { label: "Procedimiento", value: remate.procedimiento },
    { label: "Rol causa", value: remate.rol_causa },
    { label: "Tribunal", value: remate.tribunal },
    { label: "Región", value: remate.region },
    { label: "Comuna", value: remate.comuna },
    { label: "Dirección", value: remate.direccion },
    { label: "Valor mínimo", value: remate.valor_minimo },
    { label: "Comisión", value: remate.comision },
    { label: "Liquidador", value: remate.liquidador },
    { label: "Ente publicador", value: remate.ente_publicador },
    { label: "Código validación", value: remate.codigo_validacion },
    { label: "Fuente PDF", value: remate.fuente_url },
  ];

  els.modalInfo.innerHTML = campos
    .filter((item) => item.value)
    .map(
      (item) => `
        <div>
          <div class="modal__label">${item.label}</div>
          <div>${item.value}</div>
        </div>
      `
    )
    .join("");

  const descripcion =
    remate.descripcion || remate.tipo_bienes || "Sin descripción disponible.";
  els.modalDescripcion.textContent = descripcion;

  els.modal.classList.add("is-open");
  els.modal.setAttribute("aria-hidden", "false");
}

function cerrarModalRemate() {
  if (!els.modal) return;
  els.modal.classList.remove("is-open");
  els.modal.setAttribute("aria-hidden", "true");
}

// --- Inicialización --- //
document.addEventListener("DOMContentLoaded", () => {
  if (els.aplicar) {
    els.aplicar.addEventListener("click", aplicarFiltros);
  }
  if (els.results) {
    els.results.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const link = target.closest(".btn-pdf");
      if (!link) return;
      const index = Number(link.getAttribute("data-index"));
      const remate = rematesFiltrados[index];
      if (!remate) return;

      event.preventDefault();
      abrirModalRemate(remate);
    });
  }
  if (els.modal) {
    els.modal.addEventListener("click", (event) => {
      if (event.target === els.modal) {
        cerrarModalRemate();
      }
    });
    const closeBtn = els.modal.querySelector(".modal__close");
    if (closeBtn) {
      closeBtn.addEventListener("click", cerrarModalRemate);
    }
  }
  cargarDatos();
});
