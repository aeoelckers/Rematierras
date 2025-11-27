from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pypdf import PdfReader


@dataclass
class RemateDetail:
    codigo_validacion: str
    fecha_remate: Optional[datetime]
    tipo_procedimiento: Optional[str]
    rol_causa: Optional[str]
    tribunal: Optional[str]
    deudor: Optional[str]
    deudor_rut: Optional[str]
    liquidador: Optional[str]
    region: Optional[str]
    comuna: Optional[str]
    direccion: Optional[str]
    descripcion: Optional[str]
    tipo_bienes: Optional[str]
    valor_minimo: Optional[int]
    comision: Optional[str]
    raw_text: str


def _to_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode()
    ascii_text = ascii_text.replace("\r", "\n")
    ascii_text = re.sub(r"\n{2,}", "\n", ascii_text)
    return ascii_text.strip()


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _to_ascii(text)


def _search(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_valor_minimo(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _extract_section(text: str, start_label: str, end_label: str) -> Optional[str]:
    pattern = rf"{re.escape(start_label)}\n(?P<body>.+?)(?:\n{re.escape(end_label)}|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    body = match.group("body").strip()
    body = re.sub(r"\n[A-Z ]+?:$", "", body)
    return body.strip() or None


def parse_remate_pdf(codigo_validacion: str, pdf_bytes: bytes) -> RemateDetail:
    text = extract_text(pdf_bytes)

    fecha_remate = _parse_datetime(_search(r"Fecha del Remate:\s*(.+)", text))
    tipo_procedimiento = _search(r"Tipo Procedimiento:\s*(.+)", text)
    rol_causa = _search(r"Rol Causa:\s*(.+)", text)
    tribunal = _search(r"Tribunal:\s*(.+)", text)
    deudor = _search(r"Deudor:\s*(.+)", text)
    deudor_rut = _search(r"Deudor Rut:\s*(.+)", text)
    liquidador = _search(r"Liquidador:\s*(.+)", text)

    region = comuna = None
    region_match = re.search(r"Region:\s*(.+?)\s+Comuna:\s*(.+)", text, re.IGNORECASE)
    if region_match:
        region = region_match.group(1).strip()
        comuna = region_match.group(2).strip()
    if not region:
        region = _search(r"Region:\s*(.+)", text)
    if not comuna:
        comuna = _search(r"Comuna:\s*(.+)", text)

    direccion = _search(r"Direccion:\s*(.+)", text)
    descripcion = _extract_section(text, "Detalle", "Tipo Bienes")
    tipo_bienes = _extract_section(text, "Tipo Bienes", "Valor Minimo")

    valor_match = re.search(r"Valor Minimo \(pesos\):\s*([0-9\.\s]*)", text, re.IGNORECASE)
    valor_minimo = _parse_valor_minimo(valor_match.group(1) if valor_match else None)

    comision = _search(r"Comision:\s*(.+)", text)

    return RemateDetail(
        codigo_validacion=codigo_validacion,
        fecha_remate=fecha_remate,
        tipo_procedimiento=tipo_procedimiento,
        rol_causa=rol_causa,
        tribunal=tribunal,
        deudor=deudor,
        deudor_rut=deudor_rut,
        liquidador=liquidador,
        region=region,
        comuna=comuna,
        direccion=direccion,
        descripcion=descripcion,
        tipo_bienes=tipo_bienes,
        valor_minimo=valor_minimo,
        comision=comision,
        raw_text=text,
    )


__all__ = ["RemateDetail", "parse_remate_pdf", "extract_text"]
