"""Elige la vela del día, baja su mockup de Printify, fabrica el reel y deja public/reels/next.json.

Orden: primero Navidad (hasta el 24-dic), después el resto en rotación. No repite lo ya publicado
(posted.json). Token de Printify en PRINTIFY_TOKEN.
"""
import datetime, json, os, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import videos  # noqa: E402

PUB = AQUI.parent / "public" / "reels"
HASHTAGS = {
    "navidad": "#secretsanta #whiteelephantgift #funnychristmasgifts #christmasgiftideas",
    "oficina": "#coworkergift #officehumor #funnycoworkergifts #retirementgift",
    "profesiones": "#nursegifts #teachergifts #funnygifts #giftsforher",
    "cumple": "#birthdaygiftideas #funnybirthdaygifts #40thbirthday #30thbirthday",
    "boda": "#bridesmaidproposal #bridesmaidgifts #weddinggifts #bridetobe",
    "familia": "#giftsformom #giftsfordad #mothersdaygift #funnyfamily",
    "casa": "#housewarminggift #newhome #firsthome #homedecor",
    "amigos": "#bestfriendgift #selfcaregift #friendshipgift #funnygifts",
}


def posted():
    p = AQUI / "posted.json"
    return json.loads(p.read_text()) if p.exists() else []


def elegir():
    frases = json.loads((AQUI / "frases.json").read_text())
    hechos = {x["id"] for x in posted()}
    hoy = datetime.date.today()
    orden = []
    if (hoy.month, hoy.day) <= (12, 24):
        orden += [it for it in frases["navidad"]["items"]]
    for n, b in frases.items():
        if n != "navidad" or (hoy.month, hoy.day) > (12, 24):
            orden += b["items"]
    candidatos = [it for it in orden if it["id"] not in hechos]
    if not candidatos:  # todo publicado: vuelve a empezar
        candidatos = orden
    return candidatos[0]


def mockup(fid):
    prod = json.loads((AQUI / "productos.json").read_text())[fid]["producto"]
    out = AQUI / "pines" / "mockups" / f"{fid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    datos = subprocess.run(["curl", "-sf", "-H", "Authorization: Bearer " + os.environ["PRINTIFY_TOKEN"],
                            f"https://api.printify.com/v1/shops/29354750/products/{prod}.json"],
                           capture_output=True, check=True).stdout
    p = json.loads(datos)
    imgs = [i for i in p["images"] if 120602 in i["variant_ids"] and i.get("position") == "front"] \
        or [i for i in p["images"] if i.get("is_default")] or p["images"]
    subprocess.run(["curl", "-sfL", "-A", "Mozilla/5.0", "-o", str(out), imgs[0]["src"]], check=True)
    return (p.get("external") or {}).get("handle")


def caption(nicho, it):
    o = it["ocasion"]
    return (f"{videos.gancho(it).capitalize()}\n\n"
            f"\"Smells like {it['frase']}\" 🕯️ A funny hand-poured soy candle, the perfect {o.lower()}.\n"
            f"Shop 400 funny gifts: link in bio 👆\n\n"
            f"{HASHTAGS.get(nicho, '#funnygifts')} #funnycandles #giftideas #smellslikelabelco")


def main():
    it = elegir()
    fid = it["id"]
    enlace = mockup(fid)
    videos.BASE = AQUI
    videos.video(fid)
    PUB.mkdir(parents=True, exist_ok=True)
    shutil.copy(AQUI / "videos" / f"{fid}.mp4", PUB / f"{fid}.mp4")
    nicho, _ = videos.nicho_de(fid)
    (PUB / "next.json").write_text(json.dumps({"id": fid, "video": f"reels/{fid}.mp4",
                                               "caption": caption(nicho, it), "link": enlace}, indent=1))
    print("reel listo:", fid)


if __name__ == "__main__":
    main()
