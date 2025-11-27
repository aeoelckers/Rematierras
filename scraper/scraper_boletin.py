import json
import requests
from bs4 import BeautifulSoup
import urllib3

# Desactivar warnings SSL por si el certificado no es perfecto
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://boletinconcursal.cl/boletin/remates"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}

def get_html(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def scrape_boletin():
    soup = get_html(URL)

    # Tomamos la primera tabla de la página (la que viste de "Publicaciones de Remates")
    table = soup.find("table")
    if not table:
        print("No se encontró tabla en Boletín Concursal.")
        return []

    rows = table.find("tbody").find_all("tr")
    data = []

    for i, tr in enumerate(rows, start=1):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        # Estructura de columnas que vimos:
        # 0 = Deudor
        # 1 = Fecha (dd-mm-aaaa)
        # 2 = Martillero
        # 3 = Documento (PDF con link) – si existe
        deudor = tds[0].get_text(strip=True)
        fecha_txt = tds[1].get_text(strip=True)
        martillero = tds[2].get_text(strip=True) if len(tds) > 2 else ""

        pdf_link = None
        if len(tds) > 3:
            a = tds[3].find("a")
            if a and a.get("href"):
                href = a["href"]
                if href.startswith("http"):
                    pdf_link = href
                else:
                    pdf_link = "https://boletinconcursal.cl" + href

        # Convertir fecha dd-mm-aaaa → aaaa-mm-dd
        fecha_iso = None
        parts = fecha_txt.split("-")
        if len(parts) == 3:
            dd, mm, yyyy = [p.strip() for p in parts]
            fecha_iso = f"{yyyy}-{mm}-{dd}"

        item = {
            "id": f"boletin-{i}",
            "tipo_remate": "Remate concursal",
            "tipo_inmueble": "Remate de bienes",   # texto genérico
            "region": "",
            "comuna": "",
            "fecha_remate": fecha_iso,
            "precio_minimo": None,
            "moneda": "",
            "source": "boletin_concursal",
            "source_url": pdf_link or URL,
            "deudor": deudor,
            "martillero": martillero,
        }
        data.append(item)

    return data

def main():
    datos = scrape_boletin()
    with open("data/remates.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"Guardados {len(datos)} remates desde Boletín Concursal en data/remates.json")

if __name__ == "__main__":
    main()
