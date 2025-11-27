"""
Wrapper simple para ejecutar el scraper del Boletín Concursal desde este repo.

Uso:

    python3 backend/scraper_boletin.py

Genera data/remates.json en la raíz del proyecto.
"""

from pathlib import Path

from backend.remates_scraper.main import main as run_main


def cli() -> None:
    # Ejecuta main() con los argumentos por defecto
    # (output = data/remates.json, lookback 30 días, etc.)
    raise SystemExit(run_main())


if __name__ == "__main__":
    cli()
