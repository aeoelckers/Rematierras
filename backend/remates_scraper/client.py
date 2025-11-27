from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

import requests

# Dominio del Boletín
DEFAULT_BASE_URL = "https://boletinconcursal.cl"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36"
)


@dataclass
class PageRequest:
    endpoint: str
    start: int = 0
    length: int = 100
    draw: int = 1


class BoletinClient:
    """HTTP client para los remates del Boletín Concursal."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._csrf_token: Optional[str] = None
        self._csrf_header_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Bootstrap & CSRF
    # ------------------------------------------------------------------
    def bootstrap(self) -> None:
        """Carga /boletin/remates y captura los tokens CSRF."""
        url = f"{self.base_url}/boletin/remates"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        html = response.text

        token_match = re.search(r'<meta[^>]*name="_csrf"[^>]*content="([^"]+)"[^>]*>', html)
        header_match = re.search(r'<meta[^>]*name="_csrf_header"[^>]*content="([^"]+)"[^>]*>', html)
        if not token_match or not header_match:
            raise RuntimeError("No se pudo obtener el token CSRF desde la página inicial")

        self._csrf_token = token_match.group(1)
        self._csrf_header_name = header_match.group(1)

    @property
    def csrf_token(self) -> str:
        if not self._csrf_token:
            raise RuntimeError("Cliente no inicializado. Ejecuta bootstrap() primero.")
        return self._csrf_token

    @property
    def csrf_header_name(self) -> str:
        if not self._csrf_header_name:
            raise RuntimeError("Cliente no inicializado. Ejecuta bootstrap() primero.")
        return self._csrf_header_name

    def _csrf_headers(self) -> Dict[str, str]:
        return {
            self.csrf_header_name: self.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/boletin/remates",
            "Origin": self.base_url,
        }

    # ------------------------------------------------------------------
    # Iterador de DataTables
    # ------------------------------------------------------------------
    def iter_pages(self, page_request: PageRequest) -> Iterator[Dict]:
        """Va devolviendo las páginas JSON del listado de remates."""
        start = page_request.start
        draw = page_request.draw

        while True:
            payload = {
                "draw": str(draw),
                "start": str(start),
                "length": str(page_request.length),
                "columns[0][data]": "deudorNombre",
                "columns[0][searchable]": "false",
                "columns[0][orderable]": "false",
                "columns[0][search][value]": "",
                "columns[0][search][regex]": "false",
                "columns[1][data]": "fchPublicacion",
                "columns[1][searchable]": "false",
                "columns[1][orderable]": "false",
                "columns[1][search][value]": "",
                "columns[1][search][regex]": "false",
                "columns[2][data]": "entePublicador",
                "columns[2][searchable]": "false",
                "columns[2][orderable]": "false",
                "columns[2][search][value]": "",
                "columns[2][search][regex]": "false",
                "columns[3][data]": "codigoValidacion",
                "columns[3][searchable]": "false",
                "columns[3][orderable]": "false",
                "columns[3][search][value]": "",
                "columns[3][search][regex]": "false",
                "search[value]": "",
                "search[regex]": "false",
            }

            url = f"{self.base_url}{page_request.endpoint}"
            response = self.session.post(
                url,
                data=payload,
                headers=self._csrf_headers() | {"Accept": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            entries: List[Dict] = data.get("data", [])
            if not entries:
                break

            yield data
            start += page_request.length
            draw += 1

    # ------------------------------------------------------------------
    # Descarga de PDF
    # ------------------------------------------------------------------
    def download_pdf(self, codigo_validacion: str) -> bytes:
        url = f"{self.base_url}/boletin/downloadDocumentoByCodigo"
        headers = self._csrf_headers() | {
            "Accept": "application/pdf,application/octet-stream",
        }
        response = self.session.post(
            url,
            data={"codigoValidacion": codigo_validacion},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content


__all__ = ["BoletinClient", "PageRequest"]
