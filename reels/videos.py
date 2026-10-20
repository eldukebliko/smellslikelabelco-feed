"""Vídeos verticales (1080x1920, 8 s, 30 fps) de una vela a partir de su mockup.

0-2 s: pregunta-gancho; 0-6 s: mockup con zoom lento; 6-8 s: tarjeta final con la tienda.
Uso: python3 videos.py id1 id2 ...   -> videos/<id>.mp4
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw
from render import TEMAS, fuente_bagel, fuente_shoulders
from pines import ajustar

BASE = Path(__file__).parent
W, H, FPS, SEG = 1080, 1920, 30, 8


def nicho_de(fid):
    d = json.loads((BASE / "frases.json").read_text())
    for n, b in d.items():
        for it in b["items"]:
            if it["id"] == fid:
                return n, it


def gancho(it):
    o = it["ocasion"].lower().replace("gift for ", "").replace(" gift", "")
    return f"LOOKING FOR A {o.upper()} GIFT?"


def frames(fid):
    nicho, it = nicho_de(fid)
    tema = TEMAS[nicho]
    foto = Image.open(BASE / f"pines/mockups/{fid}.jpg").convert("RGB")
    d0 = ImageDraw.Draw(Image.new("RGB", (W, H)))
    fg, lg, pg = ajustar(d0, gancho(it), lambda s: fuente_shoulders(s, 800), W - 140, 330, 150)
    for i in range(FPS * SEG):
        t = i / FPS
        img = Image.new("RGB", (W, H), tema["papel"])
        d = ImageDraw.Draw(img)
        if t < 6:
            z = 1.0 + 0.18 * (t / 6)                      # zoom lento hacia la etiqueta
            lado = int(1000 * z)
            f = foto.resize((lado, lado))
            c = (lado - 1000) // 2
            img.paste(f.crop((c, c, c + 1000, c + 1000)).resize((1040, 1040)), (20, 560))
            y = 150
            for l in lg:
                d.text(((W - d.textlength(l, font=fg)) / 2, y), l, font=fg, fill=tema["tinta"])
                y += pg * 1.05
            fb = fuente_bagel(58)
            pie = "FUNNY SOY CANDLE · 9 OZ"
            d.text(((W - d.textlength(pie, font=fb)) / 2, 1680), pie, font=fb, fill=tema["tinta"])
        else:
            fb, fs = fuente_bagel(110), fuente_shoulders(64, 700)
            for txt, f, y in (("SMELLS LIKE", fs, 640), ("LABEL CO", fb, 720)):
                d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=tema["tinta"])
            for txt, y in (("400 FUNNY GIFTS · CANDLES, MUGS, TEES", 930), ("MADE IN THE USA · LINK IN BIO", 1020)):
                d.text(((W - d.textlength(txt, font=fs)) / 2, y), txt, font=fs, fill=tema["tinta"])
        yield img


def video(fid):
    out = BASE / f"videos/{fid}.mp4"
    out.parent.mkdir(exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                         stdin=subprocess.PIPE)
    for f in frames(fid):
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    print("vídeo", out.name)


if __name__ == "__main__":
    for fid in sys.argv[1:]:
        video(fid)
