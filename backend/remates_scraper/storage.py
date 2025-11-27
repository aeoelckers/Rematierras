from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class RemateRecord:
    codigo_validacion: str
    tipo_bien: str
    fecha_publicacion: date
    fecha_remate: Optional[datetime]
    tipo_procedimiento: Optional[str]
    rol_causa: Optional[str]
    tribunal: Optional[str]
    deudor_nombre: Optional[str]
    deudor_rut: Optional[str]
    liquidador: Optional[str]
    region: Optional[str]
    comuna: Optional[str]
    direccion: Optional[str]
    descripcion: Optional[str]
    tipo_bienes: Optional[str]
    valor_minimo: Optional[int]
    comision: Optional[str]
    ente_publicador: Optional[str]
    procedimiento: Optional[str]
    fuente_url: str

    def as_serializable(self) -> dict:
        payload = asdict(self)
        payload["fecha_publicacion"] = self.fecha_publicacion.isoformat()
        payload["fecha_remate"] = self.fecha_remate.isoformat() if self.fecha_remate else None
        return payload


def write_dataset(path: Path, records: Iterable[RemateRecord]) -> None:
    payload = {
        "updated_at": datetime.now(UTC).isoformat() + "Z",
        "records": [record.as_serializable() for record in records],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["RemateRecord", "write_dataset"]
