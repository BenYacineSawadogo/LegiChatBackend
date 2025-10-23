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
# 💬 Patterns conversationnels
# ==========================================================
CONVERSATIONAL_PATTERNS = [
    r'^(bonjour|salut|bonsoir|hello|hi|hey)',
    r'^(merci|thanks|au revoir|bye|adieu)',
    r'^(comment ça va|ça va|comment vas-tu)',
    r'^(ok|d\'accord|compris|entendu)',
    r'^(qui es-tu|tu es qui|qui êtes-vous)',
    r'^(quel est ton nom|comment tu t\'appelles)',
]

CONVERSATIONAL_RESPONSES = {
    "greeting": [
        "Bonjour ! Je suis votre assistant juridique spécialisé en droit burkinabè. Comment puis-je vous aider aujourd'hui ?",
        "Salut ! Je suis là pour répondre à vos questions juridiques concernant le Burkina Faso. Que puis-je faire pour vous ?"
    ],
    "thanks": [
        "Je vous en prie ! N'hésitez pas si vous avez d'autres questions juridiques.",
        "Avec plaisir ! Je reste à votre disposition pour toute autre question."
    ],
    "goodbye": [
        "Au revoir ! À bientôt pour vos prochaines questions juridiques.",
        "À bientôt ! N'hésitez pas à revenir si vous avez besoin d'aide."
    ],
    "identity": [
        "Je suis un assistant juridique spécialisé dans le droit du Burkina Faso. Je peux vous aider à comprendre les lois, décrets et arrêtés burkinabè.",
        "Je suis votre assistant pour les questions juridiques relatives au Burkina Faso, basé sur les documents officiels du pays."
    ],
    "default": [
        "Je suis là pour vous aider. Posez-moi vos questions juridiques concernant le Burkina Faso.",
        "Comment puis-je vous assister dans vos recherches juridiques ?"
    ]
}


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


def is_conversational_message(message):
    """
    Détecte si un message est conversationnel (salutations, remerciements, etc.)
    plutôt qu'une vraie question juridique.

    Args:
        message: Le message utilisateur

    Returns:
        tuple: (bool is_conversational, str conversation_type)
    """
    message_lower = message.lower().strip()

    # Messages très courts (< 15 caractères) sont probablement conversationnels
    if len(message_lower) < 15:
        # Détecter le type spécifique
        if re.match(r'^(bonjour|salut|bonsoir|hello|hi|hey)', message_lower):
            return True, "greeting"
        elif re.match(r'^(merci|thanks)', message_lower):
            return True, "thanks"
        elif re.match(r'^(au revoir|bye|adieu)', message_lower):
            return True, "goodbye"
        elif re.match(r'^(ok|d\'accord|compris|entendu)', message_lower):
            return True, "default"

    # Vérifier les patterns spécifiques
    for pattern in CONVERSATIONAL_PATTERNS:
        if re.match(pattern, message_lower):
            # Déterminer le type
            if any(word in message_lower for word in ["bonjour", "salut", "bonsoir", "hello", "hi", "hey"]):
                return True, "greeting"
            elif any(word in message_lower for word in ["merci", "thanks"]):
                return True, "thanks"
            elif any(word in message_lower for word in ["au revoir", "bye", "adieu"]):
                return True, "goodbye"
            elif any(word in message_lower for word in ["qui es-tu", "tu es qui", "qui êtes-vous", "ton nom", "t'appelles"]):
                return True, "identity"
            elif any(word in message_lower for word in ["comment ça va", "ça va"]):
                return True, "greeting"
            else:
                return True, "default"

    return False, None


def generate_conversational_response(conversation_type):
    """
    Génère une réponse conversationnelle appropriée.

    Args:
        conversation_type: Type de conversation (greeting, thanks, goodbye, identity, default)

    Returns:
        str: Réponse conversationnelle
    """
    import random

    responses = CONVERSATIONAL_RESPONSES.get(conversation_type, CONVERSATIONAL_RESPONSES["default"])
    return random.choice(responses)


def validate_response(response, response_type, sources):
    """
    Valide et nettoie une réponse avant de l'envoyer.

    Args:
        response: Le texte de la réponse
        response_type: Type de réponse
        sources: Liste des sources

    Returns:
        tuple: (cleaned_response, cleaned_sources)
    """
    # Nettoyer la réponse
    cleaned_response = response.strip()

    # Remplacer les tableaux vides par None
    cleaned_sources = None if not sources or len(sources) == 0 else sources

    # Si on a des sources, les nettoyer
    if cleaned_sources:
        for source in cleaned_sources:
            # Convertir les scores de pertinence en pourcentages
            if "relevance" in source and source["relevance"] is not None:
                # Convertir 0.95 en 95
                source["relevance"] = round(source["relevance"] * 100, 1)

    return cleaned_response, cleaned_sources


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
    # 🚀 OPTIMISATION 1 : Vérifier d'abord si c'est un message conversationnel
    # (évite les recherches FAISS inutiles pour les "Bonjour", "Merci", etc.)
    is_conversational, conv_type = is_conversational_message(new_message)
    if is_conversational:
        response = generate_conversational_response(conv_type)
        return response, "conversational", None

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
            return "❌ Référence non trouvée dans les métadonnées.", "not_found", None

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
                        "role": "user",
                        "content": f"Voici le contenu d'un texte juridique du Burkina Faso :\n\n{texte_complet}\n\nFais un résumé clair et structuré de ce document."
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
                return f"❌ Impossible de générer le résumé : {str(e)}", "error", None

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
            "content": "Tu es un assistant juridique spécialisé en droit burkinabè (Burkina Faso). Réponds de manière précise en citant les articles et les lois utilisés."
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
        "content": f"Contexte juridique :\n{contexte}\n\nQuestion : {new_message}"
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

        # 4. Valider et nettoyer la réponse (convertir relevance en %, remplacer [] par None)
        ai_response, sources = validate_response(ai_response, response_type, sources)

        # 5. Générer un ID pour le message assistant
        assistant_message_id = generate_message_id()

        # 6. Sauvegarder la réponse dans l'historique
        conversations_history[conversation_id].append({
            "role": "assistant",
            "content": ai_response
        })

        # 7. Retourner la réponse structurée au format attendu par le frontend
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
