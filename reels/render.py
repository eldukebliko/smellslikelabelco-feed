"""Genera las etiquetas de vela a partir de frases.json.

Uso: python3 render.py [ancho_px alto_px]   (por defecto 1800x1440 = 6x4.8 in a 300 ppp)
"""
import json, math, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
F = BASE / "fuentes"
W, H = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[1].isdigit() else (1800, 1440)

INK = "#1E2A44"
TEMAS = {
    "ilustrados": {"papel": "#1A1424", "tinta": "#FFF6E0", "sello": "#B04BE0", "sello_tinta": "#FFF6E0"},
    "oficina": {"papel": "#F2D16B", "tinta": INK, "sello": "#E2553B", "sello_tinta": "#FFF6E0"},
    "navidad": {"papel": "#B8322A", "tinta": "#FFF6E0", "sello": "#1E2A44", "sello_tinta": "#FFF6E0"},
    "profesiones": {"papel": "#BFD3B0", "tinta": INK, "sello": "#E2553B", "sello_tinta": "#FFF6E0"},
    "cumple": {"papel": "#F3A6B5", "tinta": INK, "sello": "#1E2A44", "sello_tinta": "#FFF6E0"},
    "boda": {"papel": "#DCD3EE", "tinta": INK, "sello": "#E2553B", "sello_tinta": "#FFF6E0"},
    "familia": {"papel": "#F6B98A", "tinta": INK, "sello": "#1E2A44", "sello_tinta": "#FFF6E0"},
    "casa": {"papel": "#9CC5DD", "tinta": INK, "sello": "#E2553B", "sello_tinta": "#FFF6E0"},
    "amigos": {"papel": "#2F6F5E", "tinta": "#FFF6E0", "sello": "#F2D16B", "sello_tinta": "#1E2A44"},
}


def fuente_bagel(px):
    return ImageFont.truetype(str(F / "BagelFatOne-Regular.ttf"), px)


def fuente_shoulders(px, peso=800):
    f = ImageFont.truetype(str(F / "BigShouldersDisplay.ttf"), px)
    f.set_variation_by_axes([peso])
    return f


def partir(frase, n):
    """Parte la frase en n líneas lo más equilibradas posible."""
    pal = frase.split()
    if n >= len(pal):
        return pal
    mejor, coste_min = None, 1e9
    def rec(i, lineas):
        nonlocal mejor, coste_min
        if len(lineas) == n - 1:
            ls = lineas + [" ".join(pal[i:])]
            c = max(len(x) for x in ls)
            if c < coste_min:
                coste_min, mejor = c, ls
            return
        for j in range(i + 1, len(pal) - (n - 2 - len(lineas))):
            rec(j, lineas + [" ".join(pal[i:j])])
    rec(0, [])
    return mejor


def bloque_frase(d, frase, caja, color):
    """Coloca la frase en la caja (x0,y0,x1,y1) con el mayor cuerpo posible."""
    x0, y0, x1, y1 = caja
    bw, bh = x1 - x0, y1 - y0
    mejor = None
    for n in range(1, 5):
        lineas = partir(frase.upper(), n)
        if not lineas:
            continue
        lo, hi = 20, 600
        while lo < hi:
            mid = (lo + hi + 1) // 2
            f = fuente_bagel(mid)
            anchos = [d.textlength(l, font=f) for l in lineas]
            alto = len(lineas) * mid * 0.98
            if max(anchos) <= bw and alto <= bh:
                lo = mid
            else:
                hi = mid - 1
        if mejor is None or lo > mejor[0]:
            mejor = (lo, lineas)
    px, lineas = mejor
    f = fuente_bagel(px)
    alto_linea = px * 0.98
    total = alto_linea * len(lineas)
    y = y0 + (bh - total) / 2
    for l in lineas:
        w = d.textlength(l, font=f)
        d.text((x0 + (bw - w) / 2, y - px * 0.12), l, font=f, fill=color)
        y += alto_linea


def texto_en_arco(img, texto, centro, radio, fuente, color, arriba=True, abertura=None):
    """Dibuja texto siguiendo un arco (arriba = convexo hacia arriba)."""
    d = ImageDraw.Draw(img)
    anchos = [d.textlength(c, font=fuente) for c in texto]
    total = sum(anchos)
    ang_total = total / radio
    ang = -math.pi / 2 - ang_total / 2 if arriba else math.pi / 2 + ang_total / 2
    for c, w in zip(texto, anchos):
        da = w / radio
        a = ang + da / 2 if arriba else ang - da / 2
        cx = centro[0] + radio * math.cos(a)
        cy = centro[1] + radio * math.sin(a)
        size = int(fuente.size * 1.6)
        tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((size / 2, size / 2), c, font=fuente, fill=color, anchor="ms")
        rot = -math.degrees(a + math.pi / 2) if arriba else -math.degrees(a - math.pi / 2)
        tile = tile.rotate(rot, resample=Image.BICUBIC)
        img.alpha_composite(tile, (int(cx - size / 2), int(cy - size / 2)))
        ang += da if arriba else -da


def sello(tema, diam):
    s = Image.new("RGBA", (diam, diam), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    r = diam / 2
    d.ellipse((0, 0, diam - 1, diam - 1), fill=tema["sello"])
    borde = diam * 0.035
    d.ellipse((borde, borde, diam - borde, diam - borde), outline=tema["sello_tinta"], width=max(2, int(diam * 0.012)))
    f = fuente_shoulders(int(diam * 0.115))
    texto_en_arco(s, "SOY WAX · 9 OZ ·", (r, r), r * 0.72, f, tema["sello_tinta"], arriba=True)
    texto_en_arco(s, "· 50 H BURN ·", (r, r), r * 0.72, f, tema["sello_tinta"], arriba=False)
    # llama
    k = diam * 0.13
    cx, cy = r, r - k * 0.05
    d.polygon([(cx, cy - k * 1.35), (cx + k * 0.62, cy + k * 0.15), (cx, cy + k * 0.75), (cx - k * 0.62, cy + k * 0.15)],
              fill=tema["sello_tinta"])
    d.ellipse((cx - k * 0.62, cy - k * 0.45, cx + k * 0.62, cy + k * 0.78), fill=tema["sello_tinta"])
    d.ellipse((cx - k * 0.25, cy + k * 0.05, cx + k * 0.25, cy + k * 0.6), fill=tema["sello"])
    d.rectangle((cx - k * 0.07, cy + k * 0.95, cx + k * 0.07, cy + k * 1.35), fill=tema["sello_tinta"])
    return s.rotate(12, resample=Image.BICUBIC, expand=False)


def etiqueta(nicho, item, arco=True, vela=True):
    tema = TEMAS[nicho]
    img = Image.new("RGBA", (W, H), tema["papel"])
    d = ImageDraw.Draw(img)
    m = int(min(W, H) * 0.06)
    # marco doble fino
    lw = max(3, int(min(W, H) * 0.008))
    d.rounded_rectangle((m * 0.5, m * 0.5, W - m * 0.5, H - m * 0.5), radius=m * 0.6, outline=tema["tinta"], width=lw)
    # arco SMELLS LIKE
    if arco:
        f_arco = fuente_shoulders(int(H * 0.085))
        radio = W * 0.62
        texto_en_arco(img, "SMELLS LIKE", (W / 2, m * 1.25 + radio + H * 0.06), radio, f_arco, tema["tinta"], arriba=True)
    # frase
    caja = (m * 1.6, H * (0.25 if arco else 0.14), W - m * 1.6, H * (0.80 if vela else 0.86))
    bloque_frase(d, item["frase"], caja, tema["tinta"])
    # pie: ocasión
    f_pie = fuente_shoulders(int(H * 0.045), 700)
    pie = ("HAND-POURED · " if vela else "") + item["ocasion"].upper()
    w = d.textlength(pie, font=f_pie)
    if w > W - m * 5:
        pie = "HAND-POURED SOY CANDLE"
        w = d.textlength(pie, font=f_pie)
    if vela:
        d.text(((W - w) / 2, H * 0.855), pie, font=f_pie, fill=tema["tinta"])
    # sello firma, esquina superior derecha
    if vela:
        diam = int(H * 0.25)
        s = sello(tema, diam)
        img.alpha_composite(s, (int(W - m * 0.6 - diam * 0.92), int(m * 0.45)))
    return img.convert("RGB")


def main():
    datos = json.loads((BASE / "frases.json").read_text())
    out = BASE / "disenos"
    out.mkdir(exist_ok=True)
    for nicho, bloque in datos.items():
        for it in bloque["items"]:
            img = etiqueta(nicho, it)
            img.save(out / f"{it['id']}.png", dpi=(300, 300))
    print("ok", W, H)


if __name__ == "__main__":
    main()
