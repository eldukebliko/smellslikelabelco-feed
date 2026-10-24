"""Publica en Instagram el reel que dejó make_reel.py (API de Instagram con inicio de sesión de Instagram).

Variables: IG_TOKEN (token largo), IG_USER_ID, PAGES_URL (base pública del vídeo).
Además renueva el token (dura 60 días) y lo guarda en el secreto IG_TOKEN si hay GH_PAT.
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


def renovar(token):
    nuevo = llamar("GET", "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token"
                          "&access_token=" + token).get("access_token")
    if nuevo and os.environ.get("GH_PAT", "").strip() and nuevo != token:
        subprocess.run(["gh", "secret", "set", "IG_TOKEN", "-R", os.environ["GITHUB_REPOSITORY"]],
                       input=nuevo.encode(), env={**os.environ, "GH_TOKEN": os.environ["GH_PAT"]}, check=True)
        print("token renovado y guardado")
    return nuevo or token


def main():
    token, user = (os.environ.get("IG_TOKEN") or "").strip(), (os.environ.get("IG_USER_ID") or "").strip()
    if not token or not user:
        print("Sin IG_TOKEN/IG_USER_ID: no se publica (solo vista previa).")
        return
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
