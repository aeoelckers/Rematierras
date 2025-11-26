import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib

URL = "https://www.dicrep.cl/remates"

def get_html(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def extract_remates():
    soup = get_html(URL)

    remates = []
    blocks = soup.select(".remate-item")  # depende de la clase real; la ajustamos si la página cambia

    for b in blocks:
        titulo = b.select_one("h3").get_text(strip=True)
        link = b.select_one("a")["href"]
        fecha_texto = b.select_one(".fecha").get_text(strip=True) if b.select_one(".fecha") else ""

        # convertir fecha estimada
        try:
            fecha = datetime.strptime(fecha_texto, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            fecha = None

        detalle = get_html(link)
        texto_aviso = detalle.get_text(" ", strip=True).lower()

        palabras = ["terreno", "lote", "sitio", "parcela", "campo"]
        if not any(p in texto_aviso for p in palabras):
            continue  # solo terrenos

        remate = {
            "id": hashlib.md5((titulo + fecha_texto).encode()).hexdigest()[:10],
            "tipo_remate": "Dicrep",
            "tipo_inmueble": "Terreno",
            "region": None,
            "comuna": None,
            "fecha_remate": fecha,
            "precio_minimo": None,
            "moneda": "",
            "source": "dicrep",
            "source_url": link,
        }

        remates.append(remate)

    return remates


def save_json():
    datos = extract_remates()
    with open("../data/remates_dicrep.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"Guardados {len(datos)} remates desde DICREP.")


if __name__ == "__main__":
    save_json()
