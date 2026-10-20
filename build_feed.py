"""Feed de Google Merchant Center (listados gratis) para la Pop-Up Store de Printify.

Autónomo: lee el token de la variable de entorno PRINTIFY_TOKEN (o de ../.printify_token en local)
y escribe public/feed.txt (texto separado por tabuladores, una fila por variante).
Pensado para GitHub Actions (cron diario) + GitHub Pages; Merchant Center lo recoge cada día.
"""
import html, json, os, re, time, urllib.request, urllib.error
from pathlib import Path

SHOP = 29354750
API = "https://api.printify.com/v1"
BRAND = "Smells Like Label Co"
TIPOS = {  # blueprint -> (categoría Google, tipo de producto, envío EE. UU.)
    1943: ("588", "Home & Garden > Candles", "6.79"),
    478: ("2169", "Kitchen & Dining > Mugs", "5.79"),
    49: ("212", "Apparel > Sweatshirts", "7.39"),
    12: ("212", "Apparel > T-Shirts", "3.99"),
}
ROPA = {49, 12}
CAMPOS = ["id", "item_group_id", "title", "description", "link", "image_link", "additional_image_link",
          "availability", "price", "brand", "condition", "identifier_exists", "google_product_category",
          "product_type", "color", "size", "gender", "age_group", "shipping", "custom_label_0"]


def token():
    t = os.environ.get("PRINTIFY_TOKEN")
    if t:
        return t.strip()
    return (Path(__file__).resolve().parent.parent / ".printify_token").read_text().strip()


def get(ruta):
    req = urllib.request.Request(API + ruta, headers={"Authorization": "Bearer " + token(),
                                                      "User-Agent": "feed-smellslikelabelco/1.0"})
    for intento in range(10):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(60)
                continue
            raise
        except urllib.error.URLError:
            time.sleep(30)
    raise RuntimeError("Printify no responde: " + ruta)


def limpio(t, n):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n].replace("\t", " ")


def opciones(v_title, bp):
    partes = [p.strip() for p in v_title.split("/")]
    if bp in ROPA and len(partes) >= 2:
        return partes[0], partes[1]  # color, talla
    if bp == 1943 and len(partes) >= 3:
        return partes[1], ""          # tarro
    return "", ""


def main():
    productos, pag = [], 1
    while True:
        r = get(f"/shops/{SHOP}/products.json?limit=50&page={pag}")
        productos += r["data"]
        if pag >= r["last_page"]:
            break
        pag += 1
    filas = []
    for p in productos:
        bp = p["blueprint_id"]
        link = (p.get("external") or {}).get("handle")
        if bp not in TIPOS or not link or not p.get("visible", True):
            continue
        cat, tipo, envio = TIPOS[bp]
        imgs = p["images"]
        for v in p["variants"]:
            if not v.get("is_enabled") or not v.get("is_available", True):
                continue
            mias = [i["src"] for i in imgs if v["id"] in i["variant_ids"]]
            if not mias:
                continue
            color, talla = opciones(v["title"], bp)
            titulo = p["title"]
            if bp in ROPA:
                titulo = f"{titulo} - {color} {talla}"
            elif bp == 1943:
                titulo = f"{titulo} - {v['title'].split('/')[-1].strip()} Scent"
            filas.append({
                "id": v.get("sku") or f"{p['id']}-{v['id']}",
                "item_group_id": p["id"],
                "title": limpio(titulo, 150),
                "description": limpio(p["description"], 4900),
                "link": link,
                "image_link": mias[0],
                "additional_image_link": ",".join(mias[1:6]),
                "availability": "in_stock",
                "price": f"{v['price'] / 100:.2f} USD",
                "brand": BRAND,
                "condition": "new",
                "identifier_exists": "no",
                "google_product_category": cat,
                "product_type": tipo,
                "color": color,
                "size": talla,
                "gender": "unisex" if bp in ROPA else "",
                "age_group": "adult" if bp in ROPA else "",
                "shipping": f"US:::{envio} USD",
                "custom_label_0": tipo.split(" > ")[-1],
            })
    out = Path(__file__).resolve().parent / "public"
    out.mkdir(exist_ok=True)
    with open(out / "feed.txt", "w", encoding="utf-8") as f:
        f.write("\t".join(CAMPOS) + "\n")
        for fila in filas:
            f.write("\t".join(str(fila[c]) for c in CAMPOS) + "\n")
    (out / "index.html").write_text("<!doctype html><title>Feed</title><p>Product feed: feed.txt</p>")
    print(len(productos), "productos ->", len(filas), "filas")


if __name__ == "__main__":
    main()
