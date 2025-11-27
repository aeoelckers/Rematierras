from __future__ import annotations

import argparse
import calendar
import html
import sys
import textwrap
import unicodedata
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .client import BoletinClient, PageRequest
from .parser import parse_remate_pdf
from .storage import RemateRecord, write_dataset

# Endpoints del boletín (muebles / inmuebles)
ENDPOINTS: List[Dict[str, str]] = [
    {"slug": "muebles", "endpoint": "/boletin/getRMP/", "tipo_bien": "mueble"},
    {"slug": "inmuebles", "endpoint": "/boletin/getRIP/", "tipo_bien": "inmueble"},
]

DATE_FORMAT = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Helpers de fechas / argumentos
# ---------------------------------------------------------------------------
def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"La fecha '{value}' no tiene el formato esperado {DATE_FORMAT}"
        ) from exc


def parse_month(value: str) -> Tuple[date, date]:
    try:
        year_str, month_str = value.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        last_day = calendar.monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, last_day)
        return start, end
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            "El mes debe tener formato YYYY-MM (por ejemplo 2025-10)"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrae remates del Boletín Concursal")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/remates.json"),
        help="Ruta del archivo JSON a generar (por defecto data/remates.json)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Días máximos hacia atrás según la fecha de publicación (por defecto, 30)",
    )
    parser.add_argument("--start-date", type=parse_date, help="Fecha mínima de publicación (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=parse_date, help="Fecha máxima de publicación (YYYY-MM-DD)")
    parser.add_argument("--month", type=parse_month, help="Mes objetivo YYYY-MM para acotar el periodo")
    parser.add_argument("--page-size", type=int, default=100, help="Tamaño de página para DataTables")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de remates (para pruebas)")
    parser.add_argument(
        "--keywords",
        nargs="+",
        help="Palabras clave para filtrar remates (descripción, tipo_bienes, etc.)",
    )
    parser.add_argument(
        "--match-fields",
        nargs="+",
        default=["descripcion", "tipo_bienes", "tipo_bien", "tipo_procedimiento"],
        help="Campos de RemateRecord a revisar al aplicar palabras clave",
    )
    parser.add_argument(
        "--match-mode",
        choices=("any", "all"),
        default="any",
        help="Modo de coincidencia para palabras clave: any (alguna) / all (todas)",
    )
    parser.add_argument(
        "--only-matching",
        action="store_true",
        help="Si se usa, solo se guardan los remates que coincidan con las palabras clave",
    )
    parser.add_argument(
        "--html-output",
        type=Path,
        help="Ruta de un informe HTML opcional con los remates recopilados",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Normalización de texto / filtros
# ---------------------------------------------------------------------------
def normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode()
    ascii_text = ascii_text.replace("\n", " ")
    return " ".join(ascii_text.lower().split())


def resolve_match_fields(requested_fields: Sequence[str]) -> Tuple[List[str], List[str]]:
    dataclass_fields = set(RemateRecord.__dataclass_fields__)
    valid = [field for field in requested_fields if field in dataclass_fields]
    invalid = [field for field in requested_fields if field not in dataclass_fields]
    if not valid:
        valid = ["descripcion"]
    return valid, invalid


def _field_to_text(record: RemateRecord, field: str) -> str:
    value = getattr(record, field, None)
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def filter_records(
    records: List[RemateRecord],
    keywords: Sequence[str],
    fields: Sequence[str],
    match_mode: str,
) -> List[RemateRecord]:
    normalized_keywords = [normalize_text(keyword) for keyword in keywords if normalize_text(keyword)]
    if not normalized_keywords:
        return []

    filtered: List[RemateRecord] = []
    for record in records:
        haystack = normalize_text(" ".join(_field_to_text(record, field) for field in fields))
        if not haystack:
            continue
        if match_mode == "all":
            matched = all(keyword in haystack for keyword in normalized_keywords)
        else:
            matched = any(keyword in haystack for keyword in normalized_keywords)
        if matched:
            filtered.append(record)
    return filtered


# ---------------------------------------------------------------------------
# Formateo y resúmenes (para consola / HTML opcional)
# ---------------------------------------------------------------------------
def format_record_summary(record: RemateRecord) -> str:
    descripcion = record.descripcion or record.tipo_bienes or "(sin descripcion disponible)"
    descripcion_line = " ".join(descripcion.split())
    descripcion_short = textwrap.shorten(descripcion_line, width=140, placeholder="...")
    fecha_remate = (
        record.fecha_remate.strftime("%Y-%m-%d %H:%M")
        if record.fecha_remate
        else "sin fecha remate"
    )
    region = record.region or "Sin region"
    comuna = record.comuna or "Sin comuna"
    return (
        f"{record.fecha_publicacion.isoformat()} | remate {fecha_remate} | {record.tipo_bien} | "
        f"{region} / {comuna} | {descripcion_short} | codigo {record.codigo_validacion}"
    )


def print_summary(
    records: List[RemateRecord],
    title: str,
    total_records: Optional[int] = None,
) -> None:
    print()
    if not records:
        if total_records is not None:
            print(f"{title}: 0 de {total_records} remates")
        else:
            print(f"{title}: no hay remates para mostrar")
        return

    header = f"{title}: {len(records)} remates"
    if total_records is not None:
        header = f"{title}: {len(records)} de {total_records} remates"
    print(header)
    for record in sorted(
        records,
        key=lambda item: (item.fecha_publicacion, item.codigo_validacion),
        reverse=True,
    ):
        print(f"- {format_record_summary(record)}")
        print(f"  URL: {record.fuente_url}")
    print()


def build_category_stats(records: Sequence[RemateRecord]) -> Tuple[Counter, Counter]:
    tipo_bien_counts: Counter[str] = Counter()
    tipo_bienes_counts: Counter[str] = Counter()
    for record in records:
        if record.tipo_bien:
            tipo_bien_counts[record.tipo_bien] += 1
        if record.tipo_bienes:
            tipo_bienes_counts[record.tipo_bienes] += 1
    return tipo_bien_counts, tipo_bienes_counts


def print_category_summary(label: str, counter: Counter, *, limit: Optional[int] = None) -> None:
    print()
    if not counter:
        print(f"{label}: sin datos")
        return

    print(f"{label}:")
    items = counter.most_common(limit)
    for name, qty in items:
        display = name or "(sin valor)"
        print(f"- {display}: {qty}")
    if limit is not None and len(counter) > limit:
        print(f"... y {len(counter) - limit} categorias mas")


def render_html(
    path: Path,
    records: Sequence[RemateRecord],
    *,
    title: str,
    generated_at: datetime,
    keywords: Optional[Sequence[str]],
    match_fields: Sequence[str],
    tipo_bien_counts: Counter,
    tipo_bienes_counts: Counter,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_label = generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    keyword_text = ", ".join(keywords) if keywords else "(sin filtro de palabras clave)"
    fields_text = ", ".join(match_fields)

    rows_html: List[str] = []
    for record in records:
        descripcion = record.descripcion or record.tipo_bienes or "(sin descripcion disponible)"
        descripcion_html = html.escape(descripcion).replace("\n", "<br>")
        tipo_bienes = html.escape(record.tipo_bienes or "-")
        deudor_nombre = html.escape(record.deudor_nombre or "-")
        region = html.escape(record.region or "-")
        comuna = html.escape(record.comuna or "-")
        direccion = html.escape(record.direccion or "-")
        tipo_procedimiento = html.escape(record.tipo_procedimiento or "-")
        liquidador = html.escape(record.liquidador or "-")
        valor_minimo = (
            f"${record.valor_minimo:,}".replace(",", ".")
            if record.valor_minimo is not None
            else "-"
        )
        fecha_remate = (
            record.fecha_remate.strftime("%Y-%m-%d %H:%M")
            if record.fecha_remate
            else "-"
        )
        fecha_publicacion = record.fecha_publicacion.isoformat()
        descripcion_busqueda = normalize_text(
            " ".join(
                [
                    descripcion,
                    record.tipo_bienes or "",
                    record.tipo_bien,
                    record.tipo_procedimiento or "",
                    record.deudor_nombre or "",
                    record.region or "",
                    record.comuna or "",
                    record.direccion or "",
                ]
            )
        )
        row = (
            f"<tr data-search=\"{html.escape(descripcion_busqueda)}\">"
            f"<td>{fecha_publicacion}</td>"
            f"<td>{fecha_remate}</td>"
            f"<td>{html.escape(record.tipo_bien)}</td>"
            f"<td>{tipo_procedimiento}</td>"
            f"<td>{deudor_nombre}</td>"
            f"<td>{liquidador}</td>"
            f"<td>{region}</td>"
            f"<td>{comuna}</td>"
            f"<td>{direccion}</td>"
            f"<td>{tipo_bienes}</td>"
            f"<td>{descripcion_html}</td>"
            f"<td>{valor_minimo}</td>"
            f"<td><a href=\"{html.escape(record.fuente_url)}\" target=\"_blank\" rel=\"noopener noreferrer\">PDF</a></td>"
            "</tr>"
        )
        rows_html.append(row)

    lines: List[str] = [
        "<!DOCTYPE html>",
        "<html lang=\"es\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        f"  <title>{html.escape(title)}</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2933; background-color: #f8fafc; }",
        "    h1 { margin-bottom: 0.25rem; }",
        "    .meta { margin: 0.25rem 0; font-size: 0.95rem; color: #52606d; }",
        "    .summary { margin: 1.5rem 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }",
        "    .summary article { background: #fff; border: 1px solid #d2d6dc; border-radius: 6px; padding: 0.75rem 1rem; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12); }",
        "    .summary h2 { margin: 0 0 0.5rem 0; font-size: 1rem; color: #0f172a; }",
        "    .summary ul { margin: 0; padding-left: 1.1rem; color: #364152; }",
        "    .filters { margin: 1rem 0; }",
        "    input[type='search'] { padding: 0.5rem; width: 320px; }",
        "    table { width: 100%; border-collapse: collapse; background: white; }",
        "    thead { background: #0f172a; color: white; }",
        "    th, td { padding: 0.5rem; border: 1px solid #cbd2d9; vertical-align: top; }",
        "    tbody tr:nth-child(even) { background: #f1f5f9; }",
        "    tbody tr[hidden] { display: none; }",
        "    .count { margin-bottom: 0.5rem; font-size: 0.9rem; color: #364152; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>{html.escape(title)}</h1>",
        f"  <p class=\"meta\">Generado el {html.escape(generated_label)}</p>",
        f"  <p class=\"meta\">Palabras clave: {html.escape(keyword_text)} | Campos: {html.escape(fields_text)}</p>",
    ]

    if tipo_bien_counts or tipo_bienes_counts:
        lines.append("  <section class=\"summary\">")
        if tipo_bien_counts:
            lines.append("    <article>")
            lines.append("      <h2>Tipos de bien</h2>")
            lines.append("      <ul>")
            for name, qty in tipo_bien_counts.most_common():
                label = html.escape(name or "(sin valor)")
                lines.append(f"        <li>{label}: {qty}</li>")
            lines.append("      </ul>")
            lines.append("    </article>")
        if tipo_bienes_counts:
            lines.append("    <article>")
            lines.append("      <h2>Categorias de bienes</h2>")
            lines.append("      <ul>")
            for name, qty in tipo_bienes_counts.most_common(10):
                label = html.escape(name or "(sin valor)")
                lines.append(f"        <li>{label}: {qty}</li>")
            if len(tipo_bienes_counts) > 10:
                lines.append(f"        <li>... y {len(tipo_bienes_counts) - 10} categorias mas</li>")
            lines.append("      </ul>")
            lines.append("    </article>")
        lines.append("  </section>")

    lines.extend(
        [
            "  <div class=\"filters\">",
            "    <label for=\"text-filter\">Filtrar en esta pagina:</label>",
            "    <input id=\"text-filter\" type=\"search\" placeholder=\"Escribe para filtrar...\">",
            "  </div>",
            f"  <p class=\"count\">Mostrando <span id=\"visible-count\">{len(records)}</span> de {len(records)} remates.</p>",
            "  <div class=\"table-wrapper\">",
            "    <table>",
            "      <thead>",
            "        <tr>",
            "          <th>Publicacion</th>",
            "          <th>Fecha remate</th>",
            "          <th>Tipo bien</th>",
            "          <th>Procedimiento</th>",
            "          <th>Deudor</th>",
            "          <th>Liquidador</th>",
            "          <th>Region</th>",
            "          <th>Comuna</th>",
            "          <th>Direccion</th>",
            "          <th>Tipo bienes</th>",
            "          <th>Descripcion</th>",
            "          <th>Valor minimo</th>",
            "          <th>Documento</th>",
            "        </tr>",
            "      </thead>",
            "      <tbody>",
        ]
    )

    if rows_html:
        lines.extend(f"        {row}" for row in rows_html)
    lines.append("      </tbody>")
    lines.extend(
        [
            "    </table>",
            "  </div>",
            "  <script>",
            "    const filterInput = document.querySelector('#text-filter');",
            "    const rows = Array.from(document.querySelectorAll('tbody tr'));",
            "    const visibleCount = document.querySelector('#visible-count');",
            "    filterInput.addEventListener('input', () => {",
            "      const needle = filterInput.value.trim().toLowerCase();",
            "      let visible = 0;",
            "      rows.forEach((row) => {",
            "        const text = row.dataset.search || '';",
            "        const shouldShow = !needle || text.includes(needle);",
            "        row.hidden = !shouldShow;",
            "        if (shouldShow) visible += 1;",
            "      });",
            "      visibleCount.textContent = visible;",
            "    });",
            "  </script>",
            "</body>",
            "</html>",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()

    start_date = args.start_date
    end_date = args.end_date
    if args.month:
        if start_date or end_date:
            print("[WARN] Se ignoran --start-date/--end-date porque se utilizó --month.", file=sys.stderr)
        start_date, end_date = args.month

    cutoff_date: Optional[date] = None
    if args.lookback_days:
        cutoff_date = (datetime.now(UTC) - timedelta(days=args.lookback_days)).date()

    effective_start = start_date or cutoff_date
    if start_date and cutoff_date:
        effective_start = max(start_date, cutoff_date)

    client = BoletinClient()
    client.bootstrap()

    records: List[RemateRecord] = []
    seen_codigos: set[str] = set()

    for config in ENDPOINTS:
        endpoint = config["endpoint"]
        tipo_bien = config["tipo_bien"]
        page_request = PageRequest(endpoint=endpoint, length=args.page_size)

        for page in client.iter_pages(page_request):
            entries = page.get("data", [])
            if not entries:
                break

            too_old_counter = 0
            for entry in entries:
                codigo = entry.get("codigoValidacion")
                if not codigo or codigo in seen_codigos:
                    continue

                try:
                    fecha_publicacion = datetime.strptime(entry["fchPublicacion"], "%Y-%m-%d").date()
                except (KeyError, ValueError):
                    print(f"[WARN] No se pudo procesar fecha de publicacion para codigo {codigo}", file=sys.stderr)
                    continue

                if effective_start and fecha_publicacion < effective_start:
                    too_old_counter += 1
                    continue

                if end_date and fecha_publicacion > end_date:
                    continue

                try:
                    pdf_bytes = client.download_pdf(codigo)
                    detail = parse_remate_pdf(codigo, pdf_bytes)
                except Exception as exc:  # pylint: disable=broad-except
                    print(f"[ERROR] No se pudo descargar/parsear PDF {codigo}: {exc}", file=sys.stderr)
                    continue

                record = RemateRecord(
                    codigo_validacion=codigo,
                    tipo_bien=tipo_bien,
                    fecha_publicacion=fecha_publicacion,
                    fecha_remate=detail.fecha_remate,
                    tipo_procedimiento=detail.tipo_procedimiento or entry.get("tipoProcedimiento"),
                    rol_causa=detail.rol_causa,
                    tribunal=detail.tribunal,
                    deudor_nombre=detail.deudor or entry.get("deudorNombre"),
                    deudor_rut=detail.deudor_rut,
                    liquidador=detail.liquidador,
                    region=detail.region,
                    comuna=detail.comuna,
                    direccion=detail.direccion,
                    descripcion=detail.descripcion,
                    tipo_bienes=detail.tipo_bienes,
                    valor_minimo=detail.valor_minimo,
                    comision=detail.comision,
                    ente_publicador=entry.get("entePublicador"),
                    procedimiento=entry.get("procedimiento"),
                    fuente_url=f"https://boletinconcursal.cl/boletin/downloadDocumentoByCodigo?codigoValidacion={codigo}",
                )
                records.append(record)
                seen_codigos.add(codigo)

                if args.limit and len(records) >= args.limit:
                    break

            if args.limit and len(records) >= args.limit:
                break
            if effective_start and too_old_counter == len(entries):
                break

        if args.limit and len(records) >= args.limit:
            break

    records.sort(key=lambda item: (item.fecha_publicacion, item.codigo_validacion), reverse=True)

    print_summary(records, "Remates obtenidos en el periodo")
    tipo_bien_counts, tipo_bienes_counts = build_category_stats(records)
    print_category_summary("Tipos de bien", tipo_bien_counts)
    print_category_summary("Categorias de bienes (top 10)", tipo_bienes_counts, limit=10)

    valid_match_fields, invalid_match_fields = resolve_match_fields(args.match_fields)
    if invalid_match_fields:
        print(
            f"[WARN] Los siguientes campos no existen en RemateRecord y se ignorarán: {', '.join(invalid_match_fields)}",
            file=sys.stderr,
        )

    keyword_matches: List[RemateRecord] = []
    if args.keywords:
        keyword_matches = filter_records(records, args.keywords, valid_match_fields, args.match_mode)
        keywords_label = ", ".join(args.keywords)
        fields_label = ", ".join(valid_match_fields)
        title = f"Coincidencias para ({keywords_label}) en campos [{fields_label}]"
        print_summary(keyword_matches, title, total_records=len(records))
        if keyword_matches:
            matched_bien_counts, matched_bienes_counts = build_category_stats(keyword_matches)
            print_category_summary("Tipos de bien (coincidencias)", matched_bien_counts)
            print_category_summary(
                "Categorias de bienes (coincidencias, top 10)",
                matched_bienes_counts,
                limit=10,
            )

    records_to_persist = records
    if args.only_matching:
        if not args.keywords:
            print("[WARN] --only-matching requiere utilizar --keywords; se guardarán todos los remates.", file=sys.stderr)
        else:
            records_to_persist = keyword_matches

    write_dataset(args.output, records_to_persist)
    print(f"Se guardaron {len(records_to_persist)} remates en {args.output}")

    if args.html_output:
        html_records = records_to_persist if args.only_matching and args.keywords else records
        html_bien_counts, html_bienes_counts = build_category_stats(html_records)
        render_html(
            args.html_output,
            html_records,
            title=f"Remates boletin concursal ({len(html_records)})",
            generated_at=datetime.now(UTC),
            keywords=args.keywords,
            match_fields=valid_match_fields,
            tipo_bien_counts=html_bien_counts,
            tipo_bienes_counts=html_bienes_counts,
        )
        print(f"Se generó el informe HTML en {args.html_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
