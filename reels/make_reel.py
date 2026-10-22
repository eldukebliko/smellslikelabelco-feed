"""Elige el producto del día, baja su mockup de Printify, fabrica el reel y deja public/reels/next.json.

Prioridad por lo que deja cada venta (Printify, 22-oct-2026): sudadera ~17 $, taza ~13 $, vela y camiseta ~12 $.
La línea ilustrada (gx*) entra un día sí y otro no hasta que todas tengan reel. Hasta el 24-dic van primero las sudaderas de Navidad; después, rotación sudadera, taza, sudadera, camiseta, vela.
No repite lo ya publicado (posted.json; las velas antiguas figuran solo con su id). Token en PRINTIFY_TOKEN.
"""
import datetime, json, os, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import videos  # noqa: E402

PUB = AQUI.parent / "public" / "reels"
TIPOS = {  # tipo -> (fichero de productos, texto bajo el mockup, nombre en el caption, hashtags del producto)
    "sudadera": ("productos_sudadera.json", "FUNNY CREWNECK SWEATSHIRT", "crewneck sweatshirt",
                 "#funnysweatshirt #crewneck #graphicsweatshirt"),
    "taza": ("productos_taza.json", "FUNNY COFFEE MUG · 11 OZ", "coffee mug", "#funnymugs #coffeemug #mugsofinstagram"),
    "camiseta": ("productos_camiseta.json", "FUNNY GRAPHIC TEE", "graphic tee", "#funnyshirts #graphictee #funnytshirt"),
    "vela": ("productos.json", "FUNNY SOY CANDLE · 9 OZ", "hand-poured soy candle", "#funnycandles #soycandle"),
}
ROTACION = ["sudadera", "taza", "sudadera", "camiseta", "vela"]
HASHTAGS = {
    "navidad": "#secretsanta #whiteelephantgift #funnychristmasgifts #christmasgiftideas",
    "oficina": "#coworkergift #officehumor #funnycoworkergifts #retirementgift",
    "profesiones": "#nursegifts #teachergifts #funnygifts #giftsforher",
    "cumple": "#birthdaygiftideas #funnybirthdaygifts #40thbirthday #30thbirthday",
    "boda": "#bridesmaidproposal #bridesmaidgifts #weddinggifts #bridetobe",
    "familia": "#giftsformom #giftsfordad #mothersdaygift #funnyfamily",
    "casa": "#housewarminggift #newhome #firsthome #homedecor",
    "amigos": "#bestfriendgift #selfcaregift #friendshipgift #funnygifts",
    "ilustrados": "#flyingcar #gamergift #carlover #ufo #retrogaming",
}


def clave(tipo, fid):
    return fid if tipo == "vela" else f"{tipo}:{fid}"


def posted():
    p = AQUI / "posted.json"
    return json.loads(p.read_text()) if p.exists() else []


def productos(tipo):
    return json.loads((AQUI / TIPOS[tipo][0]).read_text())


def elegir():
    frases = json.loads((AQUI / "frases.json").read_text())
    hechos = {x["id"] for x in posted()}
    # Línea ilustrada (22-oct-2026): mientras quede alguna sin reel, va un día sí y otro no
    nuevos = [(t, it) for it in frases["ilustrados"]["items"] for t in ("sudadera", "camiseta")
              if it["id"] in productos(t) and clave(t, it["id"]) not in hechos]
    if nuevos and len(hechos) % 2 == 0:
        return nuevos[0]
    hoy = datetime.date.today()
    if (hoy.month, hoy.day) <= (12, 24):  # temporada: solo Navidad
        items = frases["navidad"]["items"]
    else:
        items = [it for n, b in frases.items() if n != "ilustrados" for it in b["items"]]
    orden = [(t, it) for t in dict.fromkeys(ROTACION) for it in items if it["id"] in productos(t)]
    candidatos = [(t, it) for t, it in orden if clave(t, it["id"]) not in hechos] or orden
    toca = ROTACION[len(hechos) % len(ROTACION)]  # el tipo de hoy, según los reels ya publicados
    return next(((t, it) for t, it in candidatos if t == toca), candidatos[0])


def mockup(tipo, fid):
    prod = productos(tipo)[fid]["producto"]
    out = AQUI / "pines" / "mockups" / f"{tipo}_{fid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    datos = subprocess.run(["curl", "-sf", "-H", "Authorization: Bearer " + os.environ["PRINTIFY_TOKEN"],
                            f"https://api.printify.com/v1/shops/29354750/products/{prod}.json"],
                           capture_output=True, check=True).stdout
    p = json.loads(datos)
    if tipo == "vela":
        imgs = [i for i in p["images"] if 120602 in i["variant_ids"] and i.get("position") == "front"]
    else:
        imgs = [i for i in p["images"] if i.get("is_default") and i.get("position") in ("front", None)]
    imgs = imgs or [i for i in p["images"] if i.get("is_default")] or p["images"]
    subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(out), imgs[0]["src"]], check=True)
    return out, (p.get("external") or {}).get("handle")


def caption(tipo, nicho, it):
    o, nombre, tags = it["ocasion"], TIPOS[tipo][2], TIPOS[tipo][3]
    return (f"{videos.gancho(it).capitalize()}\n\n"
            f"\"{it['frase']}\" A funny {nombre}, the perfect {o.lower()}. Made to order in the USA.\n"
            f"Shop 400 funny gifts: link in bio 👆\n\n"
            f"{HASHTAGS.get(nicho, '#funnygifts')} {tags} #giftideas #smellslikelabelco")


def main():
    tipo, it = elegir()
    fid = it["id"]
    foto, enlace = mockup(tipo, fid)
    videos.BASE = AQUI
    nombre = f"{tipo}_{fid}"
    videos.video(fid, foto=foto, pie=TIPOS[tipo][1], nombre=nombre)
    PUB.mkdir(parents=True, exist_ok=True)
    shutil.copy(AQUI / "videos" / f"{nombre}.mp4", PUB / f"{nombre}.mp4")
    nicho, _ = videos.nicho_de(fid)
    (PUB / "next.json").write_text(json.dumps({"id": clave(tipo, fid), "video": f"reels/{nombre}.mp4",
                                               "caption": caption(tipo, nicho, it), "link": enlace}, indent=1))
    print("reel listo:", tipo, fid)


if __name__ == "__main__":
    main()
