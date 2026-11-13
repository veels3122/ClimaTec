"""Etapa 6 - Analisis de los comentarios de YouTube con Orange Data Mining.

Reproduce con la libreria de Orange (orange3 + orange3-text) los mismos pasos
del flujo data/etapa6/etapa6_comentarios_youtube.ows y guarda los resultados
que lee la seccion "Conocimiento Oculto" de la app:

  Entrada:  data/etapa6/comentarios_youtube_limpio.csv
            data/etapa6/video_metadatos.json
  Salida:   data/etapa6/resultados_texto.json
            static/img/etapa6/yt_*.png

Pasos (iguales al flujo):
  Corpus -> Preprocess Text (minusculas, sin URL, tokens por regex, stopwords
  es, sin numeros ni tokens de 1-2 letras, frecuencia documental >= 3)
  -> Bag of Words (TF-IDF, L2) -> Topic Modelling (LDA, 5 temas)
  -> Sentiment Analysis (Multilingual, es) -> Distances (coseno)
  -> Hierarchical Clustering (enlace promedio, 4 grupos) -> Word Enrichment.

Uso:  python scripts/youtube_analisis_texto.py
Requiere: pip install orange3 orange3-text matplotlib
"""
import json
import os
import re
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from Orange.data import Domain, StringVariable, ContinuousVariable, Table
from Orange.distance import Cosine
from Orange.clustering.hierarchical import dist_matrix_linkage, tree_from_linkage, top_clusters, leaves, AVERAGE
from orangecontrib.text import Corpus, preprocess
from orangecontrib.text.vectorization import BowVectorizer
from orangecontrib.text.topics import LdaWrapper
from orangecontrib.text.sentiment import MultiSentiment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(BASE, "data", "etapa6")
IMG = os.path.join(BASE, "static", "img", "etapa6")
SEMILLA = 42
N_TEMAS = 5
N_GRUPOS = 4

# Temas para contrastar con los modelos (busqueda por raiz de palabra)
CATEGORIAS = {
    "Eventos extremos (inundaciones, sequías, calor)": r"inundac|sequ[ií]a|lluvi|calor|temperatur|hurac|incendi|torment|desbord|dana\b|tornado|granizo",
    "Responsables (países ricos, empresas, gobiernos)": r"china|estados unidos|eeuu|pa[ií]ses ricos|\bricos\b|potencias|empresa|industria|gobiern|pol[ií]tic|millonari|capitalis|poder",
    "Religión o fatalismo": r"\bdios\b|biblia|apocalip|profec|fin del mundo|\bse[nñ]or\b|nos espera|castigo",
    "Manipulación del clima o negación": r"haarp|geoinge|manipul|chemtrail|qu[ií]mico|mentira|farsa|enga[nñ]|estafa|agenda|no existe|no es real|alarmis",
    "Acción individual y consumo": r"recicl|pl[aá]stic|consum|cada uno|h[aá]bito|bicicleta|todos somos|debemos|tenemos que",
    "Valoración del documental": r"gracias|excelente|documental|\bdw\b|interesante|buen video|buen v[ií]deo",
    "Colombia o Latinoamérica": r"colombia|latinoam|am[eé]rica latina|sudam|m[eé]xico|argentin|per[uú]\b|chile|venezuel|ecuador|bogot|medell",
    "Ganadería, agricultura y bosques": r"vaca|ganad|carne|metano|agricult|cultivo|deforest|amazon|selva|bosque|[aá]rbol",
    "Energía y combustibles": r"energ|petr[oó]le|carb[oó]n|\bgas\b|combustib|solar|e[oó]lic|renovab|el[eé]ctric|nuclear|hidroel",
    "El Niño o La Niña": r"fen[oó]meno del ni[nñ]o|\bel ni[nñ]o\b|\bla ni[nñ]a\b",
}


def corpus_desde_csv(df):
    texto = StringVariable("texto")
    dom = Domain([], metas=[texto, StringVariable("fecha"), ContinuousVariable("likes")])
    metas = np.array([[t, f, float(l)] for t, f, l in zip(df.texto, df.fecha, df.likes)], dtype=object)
    tabla = Table.from_numpy(dom, np.empty((len(df), 0)), metas=metas)
    c = Corpus.from_table(dom, tabla)
    c.set_text_features([texto])
    c.attributes["language"] = "es"
    return c


def preprocesar(c):
    pp = preprocess.PreprocessorList([
        preprocess.LowercaseTransformer(),
        preprocess.UrlRemover(),
        preprocess.RegexpTokenizer(r"\w+"),
        preprocess.StopwordsFilter(language="es"),
        preprocess.NumbersFilter(),
        preprocess.RegexpFilter(r"^.{1,2}$"),          # tokens de 1-2 letras
        preprocess.FrequencyFilter(min_df=3),          # aparece en >= 3 comentarios
    ])
    return pp(c)


def guardar_fig(nombre):
    plt.tight_layout()
    plt.savefig(os.path.join(IMG, nombre), dpi=150)
    plt.close()


def main():
    os.makedirs(IMG, exist_ok=True)
    df = pd.read_csv(os.path.join(DIR, "comentarios_youtube_limpio.csv"))
    df["likes"] = pd.to_numeric(df.get("likes", 0), errors="coerce").fillna(0)
    meta = json.load(open(os.path.join(DIR, "video_metadatos.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(DIR, "video_metadatos.json")) else {}
    n = len(df)

    # 1. Corpus y preprocesamiento
    c = preprocesar(corpus_desde_csv(df))
    tokens = c.tokens
    vacios = sum(1 for t in tokens if len(t) == 0)

    # 2. Bolsa de palabras TF-IDF
    bow = BowVectorizer(wlocal=BowVectorizer.COUNT, wglobal=BowVectorizer.IDF,
                        norm=BowVectorizer.L2).transform(c)
    X = bow.X.toarray() if hasattr(bow.X, "toarray") else np.asarray(bow.X)
    palabras = [a.name for a in bow.domain.attributes]
    tfidf_medio = X.mean(axis=0)
    orden = np.argsort(-tfidf_medio)
    top_tfidf = [(palabras[i], float(tfidf_medio[i])) for i in orden[:20]]
    frec = Counter(w for t in tokens for w in t)
    top_frec = frec.most_common(20)

    # 3. LDA (5 temas)
    lda = LdaWrapper(num_topics=N_TEMAS)   # Orange fija random_state=0
    c_lda = lda.fit_transform(c.copy())
    temas = []
    pesos_tema = np.array([[float(v) for v in c_lda.get_column(f"Topic {k+1}")] for k in range(N_TEMAS)]).T
    dominante = pesos_tema.argmax(axis=1)
    for k in range(N_TEMAS):
        terminos = list(lda.get_top_words_by_id(k, num_of_words=8)[0])
        temas.append({"tema": k + 1, "terminos": terminos,
                      "comentarios": int((dominante == k).sum()),
                      "porcentaje": round(100 * float((dominante == k).mean()), 1)})

    # 4. Sentimiento (Multilingual, espanol: lexico de Chen y Skiena, 2014)
    c_sent = MultiSentiment(language="es").transform(c)
    sent = np.array([float(v) for v in c_sent.get_column("sentiment")])
    pos, neg, neu = int((sent > 0).sum()), int((sent < 0).sum()), int((sent == 0).sum())

    # 5. Distancia coseno + clustering jerarquico (enlace promedio, 4 grupos)
    filas = np.where(X.sum(axis=1) > 0)[0]
    D = Cosine(Table.from_numpy(None, X[filas]))
    link = dist_matrix_linkage(D, linkage=AVERAGE)
    raiz = tree_from_linkage(link)
    grupos_arbol = top_clusters(raiz, N_GRUPOS)
    etiqueta = np.full(len(X), -1)
    for g, nodo in enumerate(grupos_arbol):
        etiqueta[filas[[hoja.value.index for hoja in leaves(nodo)]]] = g
    grupos = []
    for g in range(N_GRUPOS):
        m = etiqueta == g
        if m.sum() == 0:
            continue
        dentro, fuera = X[m].mean(axis=0), X[~m].mean(axis=0) if (~m).sum() else 0
        enriq = np.argsort(-(dentro - fuera))[:8]
        ej = [df.texto.iloc[i][:160] for i in np.where(m)[0][np.argsort(-df.likes.values[m])][:2]]
        grupos.append({"grupo": f"G{g+1}", "comentarios": int(m.sum()),
                       "palabras": [palabras[i] for i in enriq],
                       "sentimiento_medio": round(float(sent[m].mean()), 2), "ejemplos": ej})
    grupos.sort(key=lambda d: -d["comentarios"])

    # 6. Temas para el contraste con los modelos
    low = df.texto.str.lower()
    categorias = []
    for nombre, rx in CATEGORIAS.items():
        m = low.str.contains(rx, regex=True)
        categorias.append({"categoria": nombre, "comentarios": int(m.sum()),
                           "porcentaje": round(100 * float(m.mean()), 1),
                           "sentimiento_medio": round(float(sent[m.values].mean()), 2) if m.sum() else 0.0,
                           "likes_medianos": float(df.likes[m].median()) if m.sum() else 0.0})
    categorias.sort(key=lambda d: -d["comentarios"])

    # ---------- Figuras ----------
    plt.figure(figsize=(8, 5))
    w, v = zip(*top_tfidf[:15][::-1])
    plt.barh(w, v, color="#2a7fa3"); plt.xlabel("TF-IDF promedio"); plt.title("Términos más relevantes (TF-IDF)")
    guardar_fig("yt_terminos_tfidf.png")

    plt.figure(figsize=(8, 4.5))
    lab = [f"Tema {t['tema']}: " + ", ".join(t["terminos"][:4]) for t in temas]
    plt.barh(lab[::-1], [t["comentarios"] for t in temas][::-1], color="#c9732a")
    plt.xlabel("Comentarios con el tema dominante"); plt.title("Temas LDA (5)")
    guardar_fig("yt_temas_lda.png")

    plt.figure(figsize=(7, 4.2))
    plt.hist(sent, bins=30, color="#555")
    plt.axvline(0, color="k", lw=1); plt.xlabel("Puntaje de sentimiento (Multilingual, es)"); plt.ylabel("Comentarios")
    plt.title(f"Sentimiento: {pos} positivos · {neu} neutros · {neg} negativos")
    guardar_fig("yt_sentimiento.png")

    plt.figure(figsize=(8, 4.5))
    cn = [d["categoria"] for d in categorias][::-1]
    plt.barh(cn, [d["porcentaje"] for d in categorias][::-1], color="#3a8f5c")
    plt.xlabel("% de comentarios que mencionan el tema"); plt.title("Temas del proyecto en los comentarios")
    guardar_fig("yt_temas_proyecto.png")

    # ---------- Salida ----------
    cat = {d["categoria"]: d for d in categorias}
    coma = lambda x: str(x).replace(".", ",")
    pct = lambda k: coma(cat[k]["porcentaje"])
    res = {
        "n_comentarios": n, "sin_tokens_tras_preproceso": vacios, "vocabulario": len(palabras),
        "top_tfidf": top_tfidf, "top_frecuencia": top_frec, "temas_lda": temas,
        "sentimiento": {"positivos": pos, "neutros": neu, "negativos": neg,
                        "media": round(float(sent.mean()), 2), "mediana": round(float(np.median(sent)), 2)},
        "grupos": grupos, "categorias": categorias, "video": meta,
        "coincidencias": {
            "factor": f"{pct('Energía y combustibles')} % de los comentarios mencionan energía o combustibles",
            "colombia": f"{pct('Colombia o Latinoamérica')} % mencionan Colombia o Latinoamérica",
            "responsables": f"{pct('Responsables (países ricos, empresas, gobiernos)')} % señalan a países, empresas o gobiernos",
        },
        "hallazgos": [
            {"titulo": "Términos más relevantes", "img": "yt_terminos_tfidf.png",
             "pie": "Bag of Words con TF-IDF y normalización L2; promedio por término.",
             "texto": "Términos con mayor peso: " + ", ".join(w for w, _ in top_tfidf[:10]) + "."},
            {"titulo": "Temas (LDA, 5 temas)", "img": "yt_temas_lda.png",
             "pie": "Topic Modelling con LDA; cada comentario se asigna a su tema dominante.",
             "texto": " · ".join(f"Tema {t['tema']} ({coma(t['porcentaje'])} %): " + ", ".join(t['terminos'][:5]) for t in temas)},
            {"titulo": "Sentimiento", "img": "yt_sentimiento.png",
             "pie": "Sentiment Analysis, método Multilingual en español.",
             "texto": f"{pos} comentarios positivos, {neu} neutros y {neg} negativos (media {coma(round(float(sent.mean()), 2))})."},
            {"titulo": "Temas del proyecto en los comentarios", "img": "yt_temas_proyecto.png",
             "pie": "Porcentaje de comentarios que mencionan cada tema (búsqueda por raíz de palabra).",
             "texto": " · ".join(f"{d['categoria']}: {coma(d['porcentaje'])} %" for d in categorias)},
            {"titulo": "Grupos de comentarios", "img": None, "pie": None,
             "texto": " · ".join(f"{g['grupo']} ({g['comentarios']}): " + ", ".join(g['palabras'][:5]) for g in grupos)},
        ],
    }
    with open(os.path.join(DIR, "resultados_texto.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ["n_comentarios", "vocabulario", "sentimiento", "temas_lda", "categorias"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
