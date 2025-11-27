import json
import requests
from bs4 import BeautifulSoup

BASE = "https://licitaciones.bienes.cl"
LIST_URL = BASE + "/licitaciones/licitaciones-actuales/"

headers = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}

def scrape_bienes():
    r = requests.get(LIST_URL, headers=headers, timeout=15)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    cards = soup.select("div.card")

    data = []
    for i, card in enumerate(cards, start=1):
        title_el = card.find("h3") or card.find("h2")
        titulo = title_el.get_text(strip=True) if title_el else "Licitación Bienes Nacionales"

        body = card.find("div", class_="card-body") or card

        texto = body.get_text("\n", strip=True)
        lineas = [l.strip() for l in texto.splitlines()]

        def busca(prefix):
            for l in lineas:
                if l.startswith(prefix):
                    return l.replace(prefix, "").strip()
            return ""

        region = busca("Región:")
        prov_comuna = busca("Provincia y comuna:")
        superficie = busca("Superficie:")

        estado = "Vigente"
        badge = card.find("span", string=lambda t: t and isinstance(t, str) and t.strip())
        if badge and "suspendida" in badge.text.lower():
            estado = "Suspendida"

        btn = card.find("a", string=lambda t: t and "Ver licitación" in t)
        if btn and btn.get("href"):
            href = btn["href"]
            if href.startswith("/"):
                url = BASE + href
            else:
                url = href
        else:
            url = LIST_URL

        item = {
            "id": f"bienes-{i}",
            "tipo_remate": f"Bienes Nacionales ({estado})",
            "tipo_inmueble": titulo,
            "region": region,
            "comuna": prov_comuna,
            "fecha_remate": None,
            "precio_minimo": None,
            "moneda": "",
            "source": "bienes_nacionales",
            "source_url": url,
            "superficie": superficie,
        }
        data.append(item)

    return data

def main():
    datos = scrape_bienes()
    with open("data/remates.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"Guardadas {len(datos)} licitaciones en data/remates.json")

if __name__ == "__main__":
    main()
