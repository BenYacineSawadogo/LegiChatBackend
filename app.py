from flask import Flask, render_template, request, Response, session
import time
import re
import pickle
import unicodedata
import numpy as np
import pandas as pd
import os
import cv2
import pytesseract
from PIL import Image
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from mistralai import Mistral


# ==========================================================
# 🚀 Configuration Flask
# ==========================================================
app = Flask(__name__)
app.secret_key = "resume_secret_key"


# ==========================================================
# ⚙️ Configuration Tesseract OCR (Windows)
# ==========================================================
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Users\\DELL 7540\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe"
)
os.environ["TESSDATA_PREFIX"] = (
    r"C:\\Users\\DELL 7540\\AppData\\Local\\Programs\\Tesseract-OCR\\tessdata"
)


# ==========================================================
# 📦 Chargement des modèles et données
# ==========================================================
encoder_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
client = Mistral(api_key="uhSmZH1rHb7TPZdmoSnjVRGMrDPtJDe6")
mistral_model = "mistral-small-latest"

with open("faiss_index/metadatas.pkl", "rb") as f:
    metadatas = pickle.load(f)

embeddings = np.load("faiss_index/embeddings.npy")
df = pd.read_csv("faiss_index/fichier.csv")
textes = df["texte"].tolist()


# ==========================================================
# 🛠️ Fonctions utilitaires
# ==========================================================
def preprocess_image(pil_img):
    img = np.array(pil_img.convert("L"))
    img = cv2.GaussianBlur(img, (5, 5), 0)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(img)


def extract_text_ocr(pdf_path):
    images = convert_from_path(pdf_path, dpi=300)
    full_text = ""
    for img in images:
        preproc = preprocess_image(img)
        text = pytesseract.image_to_string(preproc, lang="fra", config="--psm 6")
        full_text += "\n" + text
    return full_text


def extract_text_from_pdf(path):
    try:
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if len(text.strip()) < 100:  # si texte trop court → fallback OCR
            return extract_text_ocr(path)
        return text
    except Exception:
        return extract_text_ocr(path)


def detecte_type_question(question):
    motifs = (
        r"\b(cherche|cherches|chercher|recherche|recherches|donne|donner|donne[-\s]?moi|"
        r"fournis|fournir|trouve|trouver|obtiens|obtenir|je veux|j'aimerais voir|"
        r"montre[-\s]?moi|accède|accéder à|affiche|afficher)\b"
    )
    return "recherche" if re.search(motifs, question.lower()) else "demande"


def extraire_reference_loi_decret(question):
    question = question.lower()
    pattern = r"(loi|décret)[\s\-n°]*([n]?\s?\d{1,4}(?:[\-/]\d{1,4})?[\-\_/]?\d{1,4}?)"
    match = re.search(pattern, question)
    if match:
        type_texte = match.group(1)
        numero = match.group(2).replace(" ", "")
        return type_texte.capitalize(), numero
    return None, None


def enlever_accents(texte):
    return "".join(
        c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn"
    )


def normaliser_numero(numero):
    parties = re.split(r"[-/]", numero)
    if len(parties) == 2:
        a, b = str(int(parties[0])), str(int(parties[1]))
        return [f"{a}-{b}", f"{b}-{a}"]
    return [numero]


def rechercher_dans_metadatas(type_texte, numero, metadatas):
    if type_texte and numero:
        variantes = normaliser_numero(numero)
        prefix = enlever_accents(type_texte.upper())
        for metadata in metadatas:
            loi_metadata = enlever_accents(str(metadata["loi"]).upper())
            for variante in variantes:
                terme = f"{prefix}_{variante}"
                if terme in loi_metadata:
                    return metadata["lien_pdf"]
    return None


def encodeur(question):
    return encoder_model.encode(question)


def generate_mistral_stream(prompt):
    response = client.chat.complete(
        model=mistral_model, messages=[{"role": "user", "content": prompt}]
    )
    full_text = response.choices[0].message.content

    # Nettoyage du texte
    cleaned_text = re.sub(r"#+\s*", "", full_text)

    # Streaming par paquets de 50 caractères
    for i in range(0, len(cleaned_text), 50):
        yield cleaned_text[i : i + 50]
        time.sleep(0.1)


# ==========================================================
# 🌐 Routes Flask
# ==========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream", methods=["POST"])
def stream():
    data = request.get_json()
    question = data.get("question", "").strip().lower()

    # === Cas résumé ===
    if question in ["oui", "oui merci", "résume", "résume-moi", "je veux un résumé"]:
        ref = session.get("derniere_reference")
        if ref:
            nom_fichier = ref["lien"].split("/")[-1]
            chemin_pdf = f"./static/pdfs/{nom_fichier}"

            try:
                texte_complet = extract_text_from_pdf(chemin_pdf)
                prompt = (
                    f"Voici le contenu d'un texte juridique :\n\n{texte_complet}\n\n"
                    "Fais un résumé clair et structuré de ce document."
                )

                def event_stream():
                    for chunk in generate_mistral_stream(prompt):
                        yield chunk
                    yield "[DONE]"

                return Response(event_stream(), mimetype="text/plain")

            except Exception as e:
                def event_stream():
                    yield f"❌ Impossible de générer le résumé : {str(e)}"

                return Response(event_stream(), mimetype="text/plain")

    # === Cas recherche de document ===
    type_question = detecte_type_question(question)
    if type_question == "recherche":
        type_texte, numero = extraire_reference_loi_decret(question)
        lien_pdf = rechercher_dans_metadatas(type_texte, numero, metadatas)

        if lien_pdf:
            session["derniere_reference"] = {
                "type": type_texte,
                "numero": numero,
                "lien": lien_pdf,
            }
            message = (
                f"📄 Voici le document demandé : "
                f"<a href='{lien_pdf}' target='_blank'>cliquer ici</a><br>"
                f"Souhaitez-vous un résumé ? (oui/non)"
            )

            def event_stream():
                yield message

            return Response(event_stream(), mimetype="text/plain")
        else:
            def event_stream():
                yield "❌ Référence non trouvée dans les métadonnées."

            return Response(event_stream(), mimetype="text/plain")

    # === Cas demande explicative (RAG avec FAISS) ===
    question_embedding = encodeur(question)
    sims = cosine_similarity([question_embedding], embeddings)[0]
    top_k = np.argsort(sims)[-10:][::-1]
    articles_selectionnes = [textes[i] for i in top_k]

    contexte = "\n\n".join(articles_selectionnes)
    prompt = (
        f"Contexte :\n{contexte}\n\n"
        f"Question : {question}\n\n"
        "Réponds de manière précise en citant les articles et les lois utilisés."
    )

    def event_stream():
        for chunk in generate_mistral_stream(prompt):
            yield chunk
        yield "[DONE]"

    return Response(event_stream(), mimetype="text/plain")


# ==========================================================
# ▶️ Lancement de l’application
# ==========================================================
if __name__ == "__main__":
    app.run(debug=True, threaded=True)
