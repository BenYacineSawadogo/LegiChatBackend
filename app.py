from flask import Flask, render_template, request, Response, session, jsonify
from flask_cors import CORS
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
from datetime import datetime
from collections import defaultdict


# ==========================================================
# 🚀 Configuration Flask
# ==========================================================
app = Flask(__name__)
app.secret_key = "resume_secret_key"

# Configuration CORS pour le frontend Angular
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)

# Stockage en mémoire des conversations (remplacer par DB en production)
conversations_history = defaultdict(list)


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


def generate_mistral_complete(messages):
    """
    Génère une réponse complète (non-streaming) à partir d'un historique de messages.

    Args:
        messages: Liste de messages au format [{"role": "user|assistant", "content": "..."}]

    Returns:
        str: Réponse complète de Mistral
    """
    response = client.chat.complete(
        model=mistral_model,
        messages=messages
    )
    full_text = response.choices[0].message.content

    # Nettoyage du texte
    cleaned_text = re.sub(r"#+\s*", "", full_text)
    return cleaned_text


def generate_message_id():
    """Génère un ID unique pour un message."""
    import random
    timestamp = int(datetime.now().timestamp() * 1000)
    random_part = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=9))
    return f"msg-{timestamp}-{random_part}"


def process_question_with_context(conversation_id, new_message):
    """
    Traite une question en utilisant le contexte de la conversation.

    Args:
        conversation_id: ID de la conversation
        new_message: Nouveau message utilisateur

    Returns:
        tuple: (réponse de l'assistant, type de réponse, sources utilisées)
    """
    # Récupérer l'historique de la conversation
    history = conversations_history[conversation_id]

    # Détecter le type de question
    type_question = detecte_type_question(new_message)

    # === Cas recherche de document ===
    if type_question == "recherche":
        type_texte, numero = extraire_reference_loi_decret(new_message)
        lien_pdf = rechercher_dans_metadatas(type_texte, numero, metadatas)

        if lien_pdf:
            response = (
                f"📄 Voici le document demandé : "
                f'<a href="{lien_pdf}" target="_blank">cliquer ici</a><br>'
                f"Souhaitez-vous un résumé ? (oui/non)"
            )
            # Stocker la référence dans l'historique pour usage ultérieur
            conversations_history[conversation_id].append({
                "type": "reference",
                "lien": lien_pdf,
                "type_texte": type_texte,
                "numero": numero
            })
            sources = [{"type": type_texte, "numero": numero, "lien": lien_pdf}]
            return response, "document_link", sources
        else:
            return "❌ Référence non trouvée dans les métadonnées.", "not_found", []

    # === Cas résumé (si l'utilisateur répond oui après une recherche de doc) ===
    if new_message.lower() in ["oui", "oui merci", "résume", "résume-moi", "je veux un résumé"]:
        # Chercher la dernière référence dans l'historique
        last_reference = None
        for item in reversed(history):
            if isinstance(item, dict) and item.get("type") == "reference":
                last_reference = item
                break

        if last_reference:
            nom_fichier = last_reference["lien"].split("/")[-1]
            chemin_pdf = f"./static/pdfs/{nom_fichier}"

            try:
                texte_complet = extract_text_from_pdf(chemin_pdf)
                prompt_messages = [
                    {
                        "role": "system",
                        "content": "Tu es un assistant juridique spécialisé dans les textes juridiques du Burkina Faso. Tu dois faire des résumés clairs, structurés et factuels."
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Voici le contenu d'un texte juridique burkinabè :\n\n{texte_complet}\n\n"
                            "Fais un résumé structuré de ce document en présentant :\n"
                            "1. L'objet du texte\n"
                            "2. Les points clés\n"
                            "3. Les dispositions importantes"
                        )
                    }
                ]
                summary = generate_mistral_complete(prompt_messages)
                sources = [{
                    "type": last_reference.get("type_texte"),
                    "numero": last_reference.get("numero"),
                    "lien": last_reference["lien"]
                }]
                return summary, "document_summary", sources
            except Exception as e:
                return f"❌ Impossible de générer le résumé : {str(e)}", "error", []

    # === Cas demande explicative (RAG avec FAISS) ===
    question_embedding = encodeur(new_message)
    sims = cosine_similarity([question_embedding], embeddings)[0]
    top_k = np.argsort(sims)[-10:][::-1]
    articles_selectionnes = [textes[i] for i in top_k]

    # Extraire les noms de documents sources pour les métadonnées
    sources = []
    for i in top_k:
        texte = textes[i]
        # Extraire le nom du document (première partie avant "article")
        doc_name = texte.split(" article ")[0] if " article " in texte else "Document juridique"
        if doc_name not in [s.get("document") for s in sources]:
            sources.append({"document": doc_name, "relevance": float(sims[i])})

    # Limiter à 5 sources principales
    sources = sources[:5]

    contexte = "\n\n".join(articles_selectionnes)

    # Construire l'historique de messages pour Mistral
    mistral_messages = [
        {
            "role": "system",
            "content": """Tu es un assistant juridique spécialisé en droit burkinabè (Burkina Faso).

RÈGLES STRICTES :
1. Utilise UNIQUEMENT les informations du contexte juridique fourni ci-dessous
2. Ne JAMAIS inventer ou supposer des informations qui ne sont pas dans le contexte
3. Si l'information demandée n'est pas dans le contexte, réponds : "Je n'ai pas trouvé cette information dans les textes juridiques disponibles du Burkina Faso"
4. Cite PRÉCISÉMENT les articles, lois, décrets et arrêtés du Burkina Faso en utilisant leur numéro exact
5. Structure tes réponses clairement avec des paragraphes et des sections

FORMAT DE RÉPONSE :
- Commence par une réponse directe à la question
- Cite les références légales exactes (ex: "Selon l'article 5 de l'arrêté n°016/2023")
- Utilise des paragraphes distincts pour chaque point
- Sois précis, factuel et professionnel"""
        }
    ]

    # Ajouter l'historique de la conversation (seulement les messages user/assistant, pas les références)
    for item in history:
        if isinstance(item, dict) and "role" in item:
            mistral_messages.append({
                "role": item["role"],
                "content": item["content"]
            })

    # Ajouter le nouveau message avec le contexte
    mistral_messages.append({
        "role": "user",
        "content": f"CONTEXTE JURIDIQUE (Burkina Faso) :\n{contexte}\n\nQUESTION : {new_message}\n\nRappel : Utilise UNIQUEMENT les informations du contexte ci-dessus."
    })

    response = generate_mistral_complete(mistral_messages)
    return response, "legal_answer", sources


# ==========================================================
# 🌐 Routes Flask
# ==========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    """
    Endpoint principal pour le frontend Angular.

    Requête:
        {
            "conversationId": "conv-1729459200-k8j3h2l9q",
            "message": "Quelle est la procédure..."
        }

    Réponse:
        {
            "id": "msg-1729459201-xyz789",
            "conversationId": "conv-1729459200-k8j3h2l9q",
            "content": "Pour créer une entreprise...",
            "role": "assistant",
            "timestamp": "2025-10-22T14:30:01.000Z"
        }
    """
    # Gérer les requêtes OPTIONS pour CORS
    if request.method == "OPTIONS":
        return "", 200

    try:
        # 1. Extraire et valider les données
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        conversation_id = data.get("conversationId", "").strip()
        message = data.get("message", "").strip()

        # Validation
        if not conversation_id:
            return jsonify({"error": "conversationId is required"}), 400

        if not message:
            return jsonify({"error": "message is required"}), 400

        if len(message) > 5000:
            return jsonify({"error": "message is too long (max 5000 characters)"}), 400

        # 2. Sauvegarder le message utilisateur dans l'historique
        conversations_history[conversation_id].append({
            "role": "user",
            "content": message
        })

        # 3. Traiter la question avec contexte et récupérer les métadonnées
        ai_response, response_type, sources = process_question_with_context(conversation_id, message)

        # 4. Générer un ID pour le message assistant
        assistant_message_id = generate_message_id()

        # 5. Sauvegarder la réponse dans l'historique
        conversations_history[conversation_id].append({
            "role": "assistant",
            "content": ai_response
        })

        # 6. Retourner la réponse structurée au format attendu par le frontend
        response_data = {
            "id": assistant_message_id,
            "conversationId": conversation_id,
            "content": ai_response,
            "role": "assistant",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": {
                "responseType": response_type,
                "country": "Burkina Faso",
                "sources": sources
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        # Log l'erreur pour le debugging
        print(f"❌ Error in /api/chat: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e) if app.debug else None
        }), 500


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
