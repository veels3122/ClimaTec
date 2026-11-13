# -*- coding: utf-8 -*-
"""
ClimaTec - Etapa 6 / Limpieza de comentarios de YouTube antes de Orange.

Entrada:  data/etapa6/comentarios_youtube_raw.csv  (texto, fecha, likes, respuestas)
Salida:   data/etapa6/comentarios_youtube_limpio.csv
          data/etapa6/traza_limpieza_comentarios.json

Reglas (cada una queda contada en la traza):
  1. Vacios: texto nulo o solo espacios.
  2. Duplicados exactos (mismo texto normalizado): se conserva el primero.
  3. Sin contenido analizable: solo emojis, signos, enlaces o menciones (@...).
  4. Muy cortos: menos de 3 palabras despues de quitar enlaces/emojis
     ("jajaja", "primero", "👍") - no aportan tema.
  5. Spam / promocion: enlaces + palabras tipo "suscribete", "canal", "promo".
  6. Idioma: deteccion heuristica por palabras vacias (es / en / otro). Se
     conservan solo los comentarios en espanol porque el flujo de Orange usa
     stopwords y sentimiento en espanol; los demas se cuentan en la traza.
Se eliminan URL y menciones del texto conservado, pero no se corrige ortografia
para no alterar la opinion del autor. No se guarda ningun dato del autor.
"""

import json
import os
import re
import unicodedata

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(BASE_DIR, "data", "etapa6")

URL = re.compile(r"https?://\S+|www\.\S+")
MENCION = re.compile(r"@\S+")
PALABRA = re.compile(r"[a-záéíóúñü]+", re.I)
SPAM = re.compile(r"suscr[ií]b|mi canal|visita|promo|gana dinero|whatsapp|telegram|crypto|bitcoin", re.I)

STOP_ES = set("""de la que el en y a los se del las un por con no una su para es al lo como mas más
pero sus le ya o este si porque esta entre cuando muy sin sobre tambien también me hasta hay donde
quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos e esto mi antes algunos
que qué unos yo otro otras otra el él tanto esa estos mucho quienes nada muchos cual poco ella estar
estas algunas algo nosotros es son está estan están fue era ser tiene tienen""".split())
STOP_EN = set("""the of and to in is that it for on with as was are be this by not you at from or have
an they which but his all we can there their what so if about more when who will would no just like
do how people my one our""".split())


def normalizar(t):
    t = unicodedata.normalize("NFKC", str(t)).strip().lower()
    return re.sub(r"\s+", " ", t)


def idioma(t):
    w = PALABRA.findall(t.lower())
    es = sum(x in STOP_ES for x in w)
    en = sum(x in STOP_EN for x in w)
    if es == 0 and en == 0:
        return "indeterminado"
    return "es" if es >= en else "en"


def limpiar():
    df = pd.read_csv(os.path.join(DIR, "comentarios_youtube_raw.csv"))
    if "respuestas" not in df.columns:   # el script original de Colab no la traia
        df["respuestas"] = 0
    traza = {"registros_iniciales": len(df)}

    df["texto"] = df["texto"].astype("string")
    vacio = df.texto.isna() | (df.texto.str.strip() == "")
    traza["vacios"] = int(vacio.sum()); df = df[~vacio].copy()

    df["_norm"] = df.texto.map(normalizar)
    dup = df.duplicated("_norm", keep="first")
    traza["duplicados"] = int(dup.sum()); df = df[~dup].copy()

    df["texto_limpio"] = df.texto.map(lambda t: re.sub(r"\s+", " ", MENCION.sub(" ", URL.sub(" ", t))).strip())
    df["n_palabras"] = df.texto_limpio.map(lambda t: len(PALABRA.findall(t)))
    sin = df.n_palabras == 0
    traza["sin_contenido_textual"] = int(sin.sum()); df = df[~sin]
    corto = df.n_palabras < 3
    traza["muy_cortos_menos_3_palabras"] = int(corto.sum()); df = df[~corto]
    spam = df.texto.str.contains(SPAM) & df.texto.str.contains(URL)
    traza["spam_promocion"] = int(spam.sum()); df = df[~spam]

    df["idioma"] = df.texto_limpio.map(idioma)
    traza["por_idioma"] = df.idioma.value_counts().to_dict()
    df = df[df.idioma == "es"]
    traza["registros_finales"] = len(df)
    traza["porcentaje_conservado"] = round(100 * len(df) / max(traza["registros_iniciales"], 1), 1)

    df["fecha"] = pd.to_datetime(df.fecha, utc=True).dt.strftime("%Y-%m-%d")
    out = df[["texto_limpio", "fecha", "likes", "respuestas", "n_palabras"]].rename(
        columns={"texto_limpio": "texto"})
    out.to_csv(os.path.join(DIR, "comentarios_youtube_limpio.csv"), index=False, encoding="utf-8")
    with open(os.path.join(DIR, "traza_limpieza_comentarios.json"), "w", encoding="utf-8") as f:
        json.dump(traza, f, ensure_ascii=False, indent=2)
    return traza


if __name__ == "__main__":
    print(json.dumps(limpiar(), ensure_ascii=False, indent=2))
