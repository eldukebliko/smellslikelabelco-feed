"""Genera un pin de Pinterest (1000x1500, 2:3) por vela + pines/pines.json con título, texto, enlace y tablero."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from render import TEMAS, fuente_shoulders, fuente_bagel

BASE = Path(__file__).parent
W, H = 1000, 1500
TABLEROS = {"oficina": "Funny Coworker Gifts", "navidad": "Funny Christmas Gifts",
            "profesiones": "Funny Gifts by Profession", "cumple": "Funny Birthday Gifts",
            "boda": "Bridesmaid & Wedding Gifts", "familia": "Funny Gifts for Mom & Dad",
            "casa": "Housewarming Gifts", "amigos": "Gifts for Your Best Friend"}


def ajustar(d, texto, fuente_fn, ancho, alto_max, maximo):
    """Mayor cuerpo con el que el texto cabe en una o dos líneas."""
    palabras = texto.split()
    for px in range(maximo, 20, -2):
        f = fuente_fn(px)
        for n in (1, 2):
            if n == 2 and len(palabras) < 2:
                continue
            if n == 1:
                lineas = [texto]
            else:
                corte = min(range(1, len(palabras)), key=lambda i: abs(
                    d.textlength(" ".join(palabras[:i]), font=f) - d.textlength(" ".join(palabras[i:]), font=f)))
                lineas = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
            if max(d.textlength(l, font=f) for l in lineas) <= ancho and n * px * 1.05 <= alto_max:
                return f, lineas, px
    return fuente_fn(20), [texto], 20


def pin(nicho, it):
    tema = TEMAS[nicho]
    img = Image.new("RGB", (W, H), tema["papel"])
    d = ImageDraw.Draw(img)
    # gancho arriba: para quién es
    gancho = it["ocasion"].upper().replace("GIFT FOR ", "GIFT FOR A ").replace("FUNNY ", "")
    f, lineas, px = ajustar(d, gancho, lambda s: fuente_shoulders(s, 800), W - 120, 230, 120)
    y = 40 + (230 - len(lineas) * px * 1.05) / 2
    for l in lineas:
        d.text(((W - d.textlength(l, font=f)) / 2, y), l, font=f, fill=tema["tinta"])
        y += px * 1.05
    # foto del producto
    foto = Image.open(BASE / f"pines/mockups/{it['id']}.jpg").convert("RGB").resize((1000, 1000))
    img.paste(foto, (0, 300))
    # pie
    fb = fuente_bagel(54)
    t1 = "FUNNY SOY CANDLE · 9 OZ"
    d.text(((W - d.textlength(t1, font=fb)) / 2, 1338), t1, font=fb, fill=tema["tinta"])
    fs = fuente_shoulders(40, 700)
    t2 = "HAND-POURED IN THE USA · SMELLS LIKE LABEL CO"
    d.text(((W - d.textlength(t2, font=fs)) / 2, 1420), t2, font=fs, fill=tema["tinta"])
    return img


def main():
    datos = json.loads((BASE / "frases.json").read_text())
    estado = json.loads((BASE / "estado.json").read_text())
    salida = []
    for nicho, bloque in datos.items():
        for it in bloque["items"]:
            pin(nicho, it).save(BASE / f"pines/{it['id']}.png", optimize=True)
            frase, ocasion = it["frase"], it["ocasion"]
            salida.append({
                "id": it["id"],
                "imagen": f"pines/{it['id']}.png",
                "tablero": TABLEROS[nicho],
                "titulo": f"{ocasion}: Smells Like {frase} Candle"[:100],
                "descripcion": (f"Looking for a {ocasion[0].lower() + ocasion[1:]} that actually gets a laugh? This hand-poured soy "
                                f"candle says it for you: \"Smells like {frase}\". 9 oz jar, 50-60 hour burn, "
                                f"9 scents to choose from. Made to order and shipped within the US.")[:500],
                "enlace": estado[it["id"]]["url"],
            })
    (BASE / "pines/pines.json").write_text(json.dumps(salida, indent=1, ensure_ascii=False))
    print(len(salida), "pines")


if __name__ == "__main__":
    main()
