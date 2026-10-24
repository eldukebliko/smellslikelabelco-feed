"""Publica en Instagram el reel que dejó make_reel.py (API de Instagram con inicio de sesión de Instagram).

Variables: IG_TOKEN (token largo), IG_USER_ID, PAGES_URL (base pública del vídeo).
Además renueva el token (dura 60 días) y lo guarda cifrado en reels/ig_token.enc con la clave IG_KEY
(AES-256 de openssl; la clave solo está en los secretos del repo). IG_TOKEN solo hace falta la primera vez.
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GRAPH = "https://graph.instagram.com/v21.0"


def llamar(metodo, url, datos=None):
    body = urllib.parse.urlencode(datos).encode() if datos else None
    req = urllib.request.Request(url, data=body, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{metodo} {url.split('?')[0]} -> {e.code}: {e.read().decode()[:500]}")


CIFRADO = AQUI / "ig_token.enc"
OPENSSL = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-a", "-A", "-pass", "env:IG_KEY"]


def leer_token():
    if CIFRADO.exists() and os.environ.get("IG_KEY"):
        r = subprocess.run(OPENSSL + ["-d", "-in", str(CIFRADO)], capture_output=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode().strip()
        print("no se pudo descifrar ig_token.enc; uso IG_TOKEN")
    partes = (os.environ.get("IG_TOKEN") or "").split()
    return next((x for x in partes if x.startswith("IG")), partes[0] if partes else "")


def guardar_token(token):
    if os.environ.get("IG_KEY"):
        subprocess.run(OPENSSL + ["-out", str(CIFRADO)], input=token.encode(), check=True)


def renovar(token):
    nuevo = llamar("GET", "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token"
                          "&access_token=" + token).get("access_token")
    if nuevo:
        guardar_token(nuevo)
        print("token renovado y guardado cifrado")
    return nuevo or token


def main():
    token = leer_token()
    user = (os.environ.get("IG_USER_ID") or "").strip()
    if not token or not user:
        print("Sin IG_TOKEN/IG_USER_ID: no se publica (solo vista previa).")
        return
    if not CIFRADO.exists():
        guardar_token(token)  # primera vez: arranca la cadena cifrada
    try:
        token = renovar(token)
    except RuntimeError as e:  # Meta solo renueva tokens de más de 24 h; no impide publicar
        print("sin renovar:", str(e).split("->")[-1][:200])
    sig = json.loads((AQUI.parent / "public" / "reels" / "next.json").read_text())
    video_url = os.environ["PAGES_URL"].rstrip("/") + "/" + sig["video"]
    cont = llamar("POST", f"{GRAPH}/{user}/media", {"media_type": "REELS", "video_url": video_url,
                                                     "caption": sig["caption"], "share_to_feed": "true",
                                                     "access_token": token})["id"]
    for _ in range(40):  # hasta ~10 min
        st = llamar("GET", f"{GRAPH}/{cont}?fields=status_code,status&access_token={token}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError("Instagram rechazó el vídeo: " + json.dumps(st))
        time.sleep(15)
    else:
        raise RuntimeError("El vídeo no terminó de procesarse a tiempo")
    pub = llamar("POST", f"{GRAPH}/{user}/media_publish", {"creation_id": cont, "access_token": token})
    hechos_p = AQUI / "posted.json"
    hechos = json.loads(hechos_p.read_text()) if hechos_p.exists() else []
    hechos.append({"id": sig["id"], "media_id": pub.get("id"), "fecha": time.strftime("%Y-%m-%d")})
    hechos_p.write_text(json.dumps(hechos, indent=1))
    print("publicado:", sig["id"], pub.get("id"))


if __name__ == "__main__":
    sys.exit(main())
