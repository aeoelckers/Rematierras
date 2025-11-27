import json
import requests
from bs4 import BeautifulSoup

BASE = "https://licitaciones.bienes.cl"
LIST_URL = BASE + "/licitaciones/licitaciones-actuales/"

def scrape_bienes():
  r = requests.get(LIST_URL, timeout=15)
  r.raise_for_status()
  soup = BeautifulSoup(r.text, "html.parser")

  # Tarjetas de licitación (cada "caja" que ves en la página)
  cards = soup.select("div.card")  # si algún día cambia, afinamos esto

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

    # Estado: Vigente / Suspendida (si aparece)
    estado = "Vigente"
    badge = card.find("span", string=lambda t: t and isinstance(t, str) and t.strip())
    if badge and "suspendida" in badge.text.lower():
      estado = "Suspendida"

    # Link "Ver licitación"
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
