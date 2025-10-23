# 📘 Documentation API LegiChat Backend

**Version** : 2.1
**Date** : 2025-10-23
**Contexte** : Système juridique du Burkina Faso
**Technologies** : Flask + Mistral AI + FAISS (RAG)

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Démarrage Rapide](#démarrage-rapide)
3. [API Endpoint](#api-endpoint)
4. [Types de Réponses](#types-de-réponses)
5. [Architecture](#architecture)
6. [Installation](#installation)
7. [Tests](#tests)
8. [Dépannage](#dépannage)

---

## 🎯 Vue d'Ensemble

LegiChat Backend est un système de question-réponse juridique pour le **Burkina Faso** utilisant :

- **RAG (Retrieval-Augmented Generation)** : Recherche sémantique avec FAISS
- **LLM** : Mistral AI pour générer des réponses contextuelles
- **Sources** : Documents juridiques burkinabè (arrêtés, décrets, lois)

### Fonctionnalités

✅ Recherche de documents juridiques par référence
✅ Résumés automatiques de documents PDF
✅ Réponses juridiques basées sur le contexte (RAG)
✅ Gestion de conversations avec historique
✅ Métadonnées enrichies (types, sources, pertinence)

---

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.8+
- Dépendances installées (`requirements.txt`)
- Données FAISS dans `faiss_index/`
- PDFs dans `static/pdfs/`

### Lancer le Serveur

```bash
cd /path/to/LegiChatBackend
python app.py
```

**Serveur disponible sur** : `http://localhost:5000`

### Test Rapide

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-001",
    "message": "Quels sont les aéroports internationaux au Burkina Faso ?"
  }'
```

---

## 📡 API Endpoint

### POST /api/chat

**URL** : `http://localhost:5000/api/chat`

#### Requête

**Headers** :
```
Content-Type: application/json
```

**Body** :
```typescript
{
  conversationId: string;  // ID de conversation (généré par le frontend)
  message: string;         // Message utilisateur (max 5000 chars)
}
```

**Exemple** :
```json
{
  "conversationId": "conv-1729459200-abc123",
  "message": "Quelle est la procédure pour créer une entreprise au Burkina Faso ?"
}
```

#### Réponse Succès (200 OK)

**Body** :
```typescript
{
  id: string;              // ID du message assistant (généré backend)
  conversationId: string;  // Même ID que la requête
  content: string;         // Réponse de l'assistant (peut contenir HTML)
  role: "assistant";       // Toujours "assistant"
  timestamp: string;       // ISO 8601 format
  metadata: {
    responseType: string;  // Type de réponse (voir ci-dessous)
    country: "Burkina Faso";
    sources: Array<{       // Documents juridiques utilisés
      document?: string;   // Nom du document
      relevance?: number;  // Score de pertinence (0-1)
      type?: string;       // Type (Loi, Décret, Arrêté)
      numero?: string;     // Numéro du document
      lien?: string;       // Lien PDF
    }>;
  };
}
```

**Exemple** :
```json
{
  "id": "msg-1729459201-xyz789",
  "conversationId": "conv-1729459200-abc123",
  "content": "Selon l'article 1 de l'arrêté n°016/2023, les aéroports de Ouagadougou et de Bobo-Dioulasso sont ouverts au trafic aérien international...",
  "role": "assistant",
  "timestamp": "2025-10-23T14:30:01.000Z",
  "metadata": {
    "responseType": "legal_answer",
    "country": "Burkina Faso",
    "sources": [
      {
        "document": "ARRETE_016_2023_ALT",
        "relevance": 0.9523
      },
      {
        "document": "DECRET_2022_0056",
        "relevance": 0.8234
      }
    ]
  }
}
```

#### Réponses d'Erreur

**400 Bad Request** :
```json
{
  "error": "conversationId is required"
}
```
```json
{
  "error": "message is required"
}
```
```json
{
  "error": "message is too long (max 5000 characters)"
}
```

**500 Internal Server Error** :
```json
{
  "error": "An error occurred processing your request",
  "details": "..." // En mode debug uniquement
}
```

---

## 📊 Types de Réponses

Le champ `metadata.responseType` indique le type de réponse retournée :

| Type | Description | Contenu | Utilisation Frontend |
|------|-------------|---------|---------------------|
| **legal_answer** | Réponse juridique standard (RAG) | Texte avec citations d'articles | Afficher avec icône ⚖️ + sources |
| **document_link** | Lien vers un document PDF trouvé | HTML avec lien cliquable | Bouton télécharger 📄 |
| **document_summary** | Résumé d'un document juridique | Résumé structuré | Card spéciale avec sections 📋 |
| **not_found** | Information non trouvée | Message d'absence | Afficher comme warning ⚠️ |
| **error** | Erreur lors du traitement | Message d'erreur | Afficher comme erreur ❌ |

### Exemples par Type

#### 1. legal_answer
```json
{
  "content": "Selon l'article 2 du décret n°2022-0056...",
  "metadata": {
    "responseType": "legal_answer",
    "sources": [
      {"document": "DECRET_2022_0056", "relevance": 0.95}
    ]
  }
}
```

#### 2. document_link
```json
{
  "content": "📄 Voici le document demandé : <a href='http://...' target='_blank'>cliquer ici</a><br>Souhaitez-vous un résumé ? (oui/non)",
  "metadata": {
    "responseType": "document_link",
    "sources": [
      {"type": "Loi", "numero": "2023-015", "lien": "http://..."}
    ]
  }
}
```

#### 3. document_summary
```json
{
  "content": "Ce décret porte sur... Les points clés sont...",
  "metadata": {
    "responseType": "document_summary",
    "sources": [
      {"type": "Décret", "numero": "2023-100", "lien": "http://..."}
    ]
  }
}
```

#### 4. not_found
```json
{
  "content": "❌ Référence non trouvée dans les métadonnées.",
  "metadata": {
    "responseType": "not_found",
    "sources": []
  }
}
```

---

## 🏗️ Architecture

### Composants Principaux

```
┌─────────────────┐
│  Frontend       │
│  (Angular 20)   │
└────────┬────────┘
         │ POST /api/chat
         ▼
┌─────────────────────────────────────┐
│  Backend Flask                      │
│  ┌─────────────────────────────┐   │
│  │ process_question_with_context│   │
│  └──────────┬──────────────────┘   │
│             │                        │
│   ┌─────────┴─────────┐             │
│   │                   │             │
│   ▼                   ▼             │
│ ┌──────┐          ┌──────┐         │
│ │FAISS │          │Mistral│         │
│ │Index │          │  AI   │         │
│ └──────┘          └───────┘         │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Données        │
│  - faiss_index/ │
│  - static/pdfs/ │
│  - metadatas    │
└─────────────────┘
```

### Flux de Traitement

1. **Réception** : Frontend envoie `{conversationId, message}`
2. **Détection** : Backend détecte le type de question
   - Recherche de document ? → Lookup dans metadata
   - Demande de résumé ? → Extraction PDF + Mistral
   - Question juridique ? → RAG (FAISS + Mistral)
3. **Traitement** :
   - Encodage de la question (sentence-transformers)
   - Recherche des 10 articles les plus pertinents (FAISS)
   - Génération de réponse avec contexte (Mistral AI)
4. **Réponse** : Retour JSON avec metadata structurée

### Gestion des Conversations

```python
# Stockage en mémoire (RAM)
conversations_history = {
    "conv-123": [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Réponse 1"},
        {"type": "reference", "lien": "...", ...},  # Méta-données
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Réponse 2"}
    ]
}
```

**Note** : En production, migrer vers une base de données (MongoDB/PostgreSQL).

---

## 💻 Installation

### 1. Cloner le Projet

```bash
git clone <repo-url>
cd LegiChatBackend
```

### 2. Créer un Environnement Virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

**Dépendances principales** :
- Flask 3.1.0
- flask-cors 5.0.1
- mistralai 1.7.0
- sentence-transformers 3.3.1
- faiss-cpu 1.10.0
- PyPDF2 3.0.1
- scikit-learn 1.6.1

### 4. Configuration (Optionnel)

Créer un fichier `.env` :

```bash
cp .env.example .env
nano .env
```

Configurer :
```env
MISTRAL_API_KEY=votre-cle-api-mistral
SECRET_KEY=votre-cle-secrete
FLASK_ENV=development
FRONTEND_URL=http://localhost:4200
```

**Important** : En production, ne jamais exposer la clé API dans le code.

### 5. Vérifier les Données

```bash
# Vérifier l'index FAISS
ls -lh faiss_index/
# Doit contenir : embeddings.npy, index.faiss, fichier.csv, metadatas.pkl

# Vérifier les PDFs
ls static/pdfs/ | head
```

### 6. Lancer le Serveur

```bash
python app.py
```

**Sortie attendue** :
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

## 🧪 Tests

### Test 1 : Endpoint Disponible

```bash
curl http://localhost:5000/
```

**Attendu** : HTML de la page d'accueil (ancien frontend)

### Test 2 : Question Simple

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-001",
    "message": "Bonjour"
  }'
```

**Attendu** : JSON avec réponse de l'assistant

### Test 3 : Question Juridique

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-002",
    "message": "Quels sont les aéroports internationaux au Burkina Faso ?"
  }'
```

**Attendu** : Réponse citant l'arrêté n°016/2023 avec sources dans metadata

### Test 4 : Recherche de Document

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-003",
    "message": "Cherche-moi la loi 2023-015"
  }'
```

**Attendu** : Lien PDF si le document existe, `responseType: "document_link"`

### Test 5 : Validation (Erreur)

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-004"
  }'
```

**Attendu** : `{"error": "message is required"}` avec status 400

### Test 6 : Contexte Conversationnel

```bash
# Message 1
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-005","message":"Parle-moi des aéroports"}'

# Message 2 (même conversationId)
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-005","message":"Quels sont leurs horaires ?"}'
```

**Attendu** : La 2ème réponse doit tenir compte du contexte (aéroports mentionnés avant)

---

## 🔧 Dépannage

### Problème 1 : CORS Error

**Symptôme** :
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution** :
```python
# Vérifier dans app.py ligne 29
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)
```

Si le frontend est sur un autre port, ajuster `origins`.

### Problème 2 : 500 Internal Server Error

**Causes possibles** :
1. Clé API Mistral invalide
2. Fichiers FAISS manquants
3. Erreur dans le code

**Debug** :
```bash
# Activer mode debug pour voir les erreurs détaillées
# app.py ligne 244
app.run(debug=True, threaded=True)
```

Consulter les logs dans le terminal où `python app.py` tourne.

### Problème 3 : Pas de Réponses

**Causes possibles** :
1. Clé API Mistral épuisée (quota)
2. Pas de connexion internet
3. Index FAISS corrompu

**Vérifications** :
```python
# Tester l'API Mistral directement
from mistralai import Mistral
client = Mistral(api_key="votre-cle")
response = client.chat.complete(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Test"}]
)
print(response.choices[0].message.content)
```

### Problème 4 : ModuleNotFoundError

**Symptôme** :
```
ModuleNotFoundError: No module named 'flask_cors'
```

**Solution** :
```bash
pip install flask-cors
# ou réinstaller tout
pip install -r requirements.txt
```

### Problème 5 : Contexte Non Conservé

**Symptôme** : Les messages suivants ne tiennent pas compte des précédents

**Cause** : `conversationId` différent entre les messages

**Solution** : Vérifier que le frontend utilise le **même** `conversationId` pour toute une conversation

---

## 📚 Ressources

### Documentation Officielle

- [Flask](https://flask.palletsprojects.com/)
- [Mistral AI](https://docs.mistral.ai/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)

### Fichiers Importants

- `app.py` - Application principale
- `requirements.txt` - Dépendances Python
- `.env.example` - Template de configuration
- `faiss_index/` - Index de recherche vectorielle
- `static/pdfs/` - Documents juridiques PDF

### Contact & Support

Pour des questions techniques, consulter :
- Issues GitHub du projet
- Documentation dans le code (docstrings)
- Logs du serveur Flask

---

## 🔐 Sécurité & Production

### Recommandations

**Ne PAS faire en production** :
- ❌ Exposer la clé API dans le code
- ❌ Utiliser `debug=True`
- ❌ Utiliser le serveur Flask dev
- ❌ Stocker les conversations en RAM

**Faire en production** :
- ✅ Variables d'environnement (`.env`)
- ✅ Gunicorn ou uWSGI comme serveur
- ✅ Base de données (MongoDB/PostgreSQL)
- ✅ HTTPS uniquement
- ✅ Rate limiting
- ✅ Authentification JWT
- ✅ Logging structuré
- ✅ Monitoring (Prometheus/Grafana)

---

**Version** : 2.1
**Dernière mise à jour** : 2025-10-23
**Contexte juridique** : Burkina Faso
