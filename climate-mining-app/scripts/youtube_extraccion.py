# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 6 / Extraccion de comentarios de YouTube (YouTube Data API v3).

La clave NUNCA se escribe en el codigo ni se sube al repositorio. Se lee de:
  - la variable de entorno YOUTUBE_API_KEY (local:  set YOUTUBE_API_KEY=...  en Windows), o
  - los "Secrets" de Google Colab (icono de llave, nombre YOUTUBE_API_KEY).

Solo se guardan los campos necesarios para el analisis: texto, fecha, likes y
numero de respuestas. NO se guarda el nombre, el canal ni la foto del autor.

Salida:
  data/etapa6/comentarios_youtube_raw.csv
  data/etapa6/video_metadatos.json   (titulo, canal, fecha, conteos; datos publicos del video)

Uso:  python scripts/youtube_extraccion.py 0rzAluuejUw 500
"""

import datetime as dt
import json
import os
import sys

import pandas as pd
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE_DIR, "data", "etapa6")
API = "https://www.googleapis.com/youtube/v3"


def obtener_clave():
    clave = os.environ.get("YOUTUBE_API_KEY")
    if not clave:
        try:  # Google Colab
            from google.colab import userdata  # type: ignore
            clave = userdata.get("YOUTUBE_API_KEY")
        except Exception:
            pass
    if not clave:
        sys.exit("Falta YOUTUBE_API_KEY (variable de entorno o Secret de Colab).")
    return clave


def metadatos_video(clave, video_id):
    r = requests.get(f"{API}/videos", params={"key": clave, "id": video_id,
                                              "part": "snippet,statistics"}, timeout=30)
    r.raise_for_status()
    item = r.json()["items"][0]
    sn, st = item["snippet"], item["statistics"]
    return {"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}",
            "titulo": sn["title"], "canal": sn["channelTitle"], "publicado": sn["publishedAt"],
            "idioma_declarado": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
            "vistas": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
            "comentarios_reportados": int(st.get("commentCount", 0))}


def extraer(clave, video_id, maximo=500):
    comentarios, pagina, paginas = [], None, 0
    while len(comentarios) < maximo:
        params = {"key": clave, "part": "snippet", "videoId": video_id,
                  "maxResults": min(100, maximo - len(comentarios)),
                  "textFormat": "plainText", "order": "time"}
        if pagina:
            params["pageToken"] = pagina
        r = requests.get(f"{API}/commentThreads", params=params, timeout=30)
        datos = r.json()
        if r.status_code != 200:
            print("Error de la API:", datos.get("error", {}).get("message"))
            break
        paginas += 1
        for el in datos.get("items", []):
            c = el["snippet"]["topLevelComment"]["snippet"]
            comentarios.append({"texto": c["textDisplay"], "fecha": c["publishedAt"],
                                "likes": c["likeCount"],
                                "respuestas": el["snippet"].get("totalReplyCount", 0)})
        pagina = datos.get("nextPageToken")
        if not pagina:
            break
    return comentarios, paginas


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "0rzAluuejUw"
    maximo = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    clave = obtener_clave()
    os.makedirs(OUT, exist_ok=True)
    meta = metadatos_video(clave, video)
    filas, paginas = extraer(clave, video, maximo)
    meta.update({"fecha_extraccion": dt.datetime.now().isoformat(timespec="seconds"),
                 "comentarios_extraidos": len(filas), "paginas_api": paginas,
                 "parametros": {"order": "time", "textFormat": "plainText",
                                "maxResults": 100, "limite": maximo}})
    pd.DataFrame(filas).to_csv(os.path.join(OUT, "comentarios_youtube_raw.csv"),
                               index=False, encoding="utf-8-sig")
    with open(os.path.join(OUT, "video_metadatos.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
