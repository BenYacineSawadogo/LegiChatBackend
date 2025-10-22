# 🔗 Guide d'Intégration Backend ↔️ Frontend Angular

**Date**: 2025-10-22
**Version Backend**: 2.0 (Compatible Angular 20)
**Auteur**: Adaptation pour LegiChatUI

---

## 📋 Résumé des Modifications

Le backend LegiChatBackend a été adapté pour être **100% compatible** avec le frontend Angular LegiChatUI. L'ancienne route `/stream` (streaming text/plain) est toujours disponible, mais un **nouvel endpoint `/api/chat`** (JSON REST) a été ajouté.

### ✨ Nouveautés

| Fonctionnalité | Détails |
|---------------|---------|
| **Endpoint REST** | `POST /api/chat` avec format JSON |
| **CORS configuré** | Frontend Angular (`localhost:4200`) autorisé |
| **Historique conversationnel** | Gestion des conversations par `conversationId` |
| **Réponses complètes** | Plus de streaming, réponse JSON complète |
| **IDs générés** | Backend génère les IDs des messages assistant |
| **Validation** | Validation des entrées + gestion d'erreurs |
| **Rétrocompatibilité** | L'ancien endpoint `/stream` fonctionne toujours |

---

## 🏗️ Architecture Modifiée

### Avant (app.py v1)

```
Frontend (HTML/JS)
     ↓ POST /stream
Backend Flask
     ↓ Response (text/plain streaming)
Frontend affiche le texte progressivement
```

### Après (app.py v2)

```
Frontend Angular
     ↓ POST /api/chat {conversationId, message}
Backend Flask
     ├─ Récupère l'historique de conversation
     ├─ Traite avec contexte (RAG + Mistral AI)
     └─ Retourne JSON {id, conversationId, content, role, timestamp}
Frontend Angular affiche le message
```

---

## 📦 Nouveaux Fichiers et Modifications

### Fichiers Modifiés

1. **`app.py`** (principales modifications)
   - Imports ajoutés : `jsonify`, `CORS`, `datetime`, `defaultdict`
   - Configuration CORS pour `localhost:4200`
   - Stockage en mémoire : `conversations_history`
   - Nouvelles fonctions :
     - `generate_mistral_complete()` - Réponse complète (non-streaming)
     - `generate_message_id()` - Génération d'ID unique
     - `process_question_with_context()` - Traitement avec contexte conversationnel
   - Nouvel endpoint : `@app.route("/api/chat", methods=["POST", "OPTIONS"])`

### Fichiers Créés

2. **`.env.example`**
   - Template pour configuration environnement
   - Variables pour Mistral API, Tesseract, CORS, etc.

3. **`INTEGRATION.md`** (ce fichier)
   - Documentation complète de l'intégration

---

## 🔌 Spécifications de l'Endpoint `/api/chat`

### Requête HTTP

**URL**: `http://localhost:5000/api/chat`
**Méthode**: `POST`
**Headers**:
```http
Content-Type: application/json
```

**Body**:
```json
{
  "conversationId": "conv-1729459200-k8j3h2l9q",
  "message": "Quelle est la procédure pour créer une entreprise au Sénégal ?"
}
```

**Validation**:
- `conversationId` : Requis, non-vide, string
- `message` : Requis, non-vide, max 5000 caractères, string

### Réponse HTTP

**Status Code**: `200 OK` (succès) ou `400`/`500` (erreur)
**Headers**:
```http
Content-Type: application/json
```

**Body (Succès)**:
```json
{
  "id": "msg-1729459201-xyz789",
  "conversationId": "conv-1729459200-k8j3h2l9q",
  "content": "Pour créer une entreprise au Sénégal, vous devez suivre les étapes suivantes...",
  "role": "assistant",
  "timestamp": "2025-10-22T14:30:01.000Z"
}
```

**Body (Erreur 400 - Bad Request)**:
```json
{
  "error": "conversationId is required"
}
```

**Body (Erreur 500 - Internal Server Error)**:
```json
{
  "error": "An error occurred processing your request",
  "details": "..." // Seulement en mode debug
}
```

---

## 🗄️ Gestion de l'Historique Conversationnel

### Stockage en Mémoire

Le backend stocke l'historique dans une structure Python :

```python
conversations_history = {
    "conv-123": [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
        {"type": "reference", "lien": "http://...", ...},  # Méta-info pour les références
        {"role": "user", "content": "Question suivante"},
        {"role": "assistant", "content": "Réponse..."}
    ],
    "conv-456": [...]
}
```

### Flux de Données

1. **Premier message d'une conversation**
   ```
   Frontend → Backend: {conversationId: "conv-123", message: "Bonjour"}
   Backend:
     - Crée une nouvelle entrée dans conversations_history["conv-123"]
     - Ajoute {"role": "user", "content": "Bonjour"}
     - Traite la question (RAG + Mistral)
     - Ajoute {"role": "assistant", "content": "..."}
     - Retourne la réponse
   ```

2. **Messages suivants**
   ```
   Frontend → Backend: {conversationId: "conv-123", message: "Question suivante"}
   Backend:
     - Récupère l'historique de "conv-123"
     - Construit le contexte pour Mistral avec tout l'historique
     - Génère la réponse avec contexte
     - Ajoute les messages user + assistant à l'historique
     - Retourne la réponse
   ```

### ⚠️ Important : Stockage en Mémoire

Le stockage actuel est **en mémoire** (RAM). Cela signifie :
- ✅ Rapide et simple
- ❌ Perdu au redémarrage du serveur
- ❌ Ne fonctionne pas avec plusieurs instances (load balancing)

**Pour la production**, remplacer par :
- Base de données (MongoDB, PostgreSQL)
- Redis pour le cache
- Voir section "Migration vers DB" ci-dessous

---

## 🔐 Sécurité et Configuration

### Variables d'Environnement (Recommandé)

**Créer un fichier `.env`** (à partir de `.env.example`) :

```bash
cp .env.example .env
nano .env  # ou vim, code, etc.
```

**Modifier les valeurs** :
```env
MISTRAL_API_KEY=votre-cle-api-mistral
SECRET_KEY=une-cle-secrete-aleatoire-longue
FLASK_ENV=development
```

**Modifier `app.py`** pour charger les variables d'environnement :

```python
# En haut de app.py, après les imports
from dotenv import load_dotenv
load_dotenv()

# Remplacer ligne 43
# client = Mistral(api_key="uhSmZH1rHb7TPZdmoSnjVRGMrDPtJDe6")
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

# Remplacer ligne 26
# app.secret_key = "resume_secret_key"
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")
```

**Installer python-dotenv** :
```bash
pip install python-dotenv
echo "python-dotenv==1.0.0" >> requirements.txt
```

### CORS

La configuration CORS actuelle autorise **uniquement** `http://localhost:4200`.

Pour production, modifier dans `app.py` :
```python
# Développement
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)

# Production
CORS(app, origins=["https://votre-domaine.com"], supports_credentials=True)

# Ou depuis variable d'environnement
CORS(app, origins=[os.getenv("FRONTEND_URL", "http://localhost:4200")], supports_credentials=True)
```

---

## 🚀 Installation et Démarrage

### 1. Installation des Dépendances

```bash
cd /home/user/LegiChatBackend

# Vérifier que flask-cors est dans requirements.txt
grep flask-cors requirements.txt

# Installer (si nécessaire)
pip install flask-cors

# Ou réinstaller toutes les dépendances
pip install -r requirements.txt
```

### 2. Configuration (Optionnel mais Recommandé)

```bash
# Copier le template
cp .env.example .env

# Éditer avec vos valeurs
nano .env
```

### 3. Démarrer le Serveur

```bash
python app.py
```

**Sortie attendue** :
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

Le backend est maintenant accessible sur `http://localhost:5000`.

---

## 🧪 Tests

### Test 1 : Vérifier que le Serveur Répond

```bash
curl http://localhost:5000/
```

**Résultat attendu** : HTML de la page d'accueil (ancien frontend)

### Test 2 : Test Basique du Nouvel Endpoint

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-conv-123",
    "message": "Bonjour"
  }'
```

**Résultat attendu** (JSON) :
```json
{
  "id": "msg-1729459201-xyz789",
  "conversationId": "test-conv-123",
  "content": "Bonjour ! Comment puis-je vous aider avec le droit sénégalais ?",
  "role": "assistant",
  "timestamp": "2025-10-22T14:30:01.000Z"
}
```

### Test 3 : Test Avec Contexte (Conversation à 2 Messages)

**Message 1** :
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-conv-456",
    "message": "Parle-moi du code du travail sénégalais"
  }'
```

**Message 2** (même conversationId) :
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-conv-456",
    "message": "Quelles sont les sanctions prévues ?"
  }'
```

Le backend doit se souvenir du contexte du premier message.

### Test 4 : Test de Validation (Erreur 400)

**Message vide** :
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-conv-789",
    "message": ""
  }'
```

**Résultat attendu** :
```json
{
  "error": "message is required"
}
```

### Test 5 : Test CORS (Depuis le Frontend Angular)

1. Démarrer le backend : `python app.py`
2. Démarrer le frontend Angular : `cd ../LegiChatUI && npm start`
3. Ouvrir `http://localhost:4200`
4. Créer une conversation et envoyer un message
5. Ouvrir les DevTools (F12) → Onglet Network
6. Vérifier :
   - Requête POST vers `http://localhost:5000/api/chat`
   - Status 200
   - Pas d'erreurs CORS dans la console

---

## 🔗 Intégration avec le Frontend Angular

### Configuration Frontend

**Fichier** : `src/app/core/services/chat-api.service.ts`

**Ligne 16** - Modifier l'URL de l'API :
```typescript
private apiUrl = 'http://localhost:5000/api';
```

**Lignes 34-46** - Décommenter le code HTTP réel :
```typescript
sendMessage(conversationId: string, message: string): Observable<Message> {
  return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
    conversationId,
    message
  }).pipe(
    map(response => ({
      id: response.id,
      conversationId: response.conversationId,
      content: response.content,
      role: 'assistant' as const,
      timestamp: new Date(response.timestamp),
      isLoading: false
    }))
  );
}
```

**Lignes 40-46** - Commenter le mock :
```typescript
// MOCK - À supprimer en production
// return of({...}).pipe(delay(1000));
```

### Workflow Complet

```
1. Utilisateur ouvre http://localhost:4200
2. Utilisateur tape un message
3. Frontend génère conversationId (ex: "conv-1729459200-abc")
4. Frontend envoie POST /api/chat {conversationId, message}
5. Backend traite (RAG + Mistral)
6. Backend retourne JSON
7. Frontend affiche la réponse
8. Utilisateur envoie un 2e message (même conversationId)
9. Backend récupère l'historique et génère réponse avec contexte
10. Frontend affiche la réponse contextuelle
```

---

## 📊 Différences entre `/stream` et `/api/chat`

| Aspect | `/stream` (Ancien) | `/api/chat` (Nouveau) |
|--------|-------------------|----------------------|
| **Frontend** | HTML/JS custom | Angular 20 |
| **Format Requête** | `{question: "..."}` | `{conversationId: "...", message: "..."}` |
| **Format Réponse** | `text/plain` streaming | JSON complet |
| **Streaming** | ✅ Oui (50 chars/chunk) | ❌ Non (réponse complète) |
| **Contexte** | Via Flask sessions | Via conversationId |
| **IDs Messages** | ❌ Non | ✅ Oui (générés backend) |
| **CORS** | ❌ Non configuré | ✅ Oui (localhost:4200) |
| **Validation** | ❌ Minimale | ✅ Stricte |
| **Gestion Erreurs** | ❌ Basique | ✅ Structurée (JSON) |
| **État** | 🟢 Fonctionnel (legacy) | 🟢 Production-ready |

**Recommandation** : Utiliser `/api/chat` pour le frontend Angular. Garder `/stream` pour rétrocompatibilité ou tests.

---

## 🛠️ Améliorations Futures

### Court Terme

1. **Variables d'environnement**
   - Externaliser la clé API Mistral
   - Configurer CORS dynamiquement
   - Port et host configurables

2. **Logging structuré**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   logger.info(f"New message from conversation {conversation_id}")
   logger.error(f"Error processing message: {e}")
   ```

3. **Rate Limiting**
   ```python
   from flask_limiter import Limiter

   limiter = Limiter(app, key_func=lambda: request.remote_addr)

   @app.route("/api/chat", methods=["POST"])
   @limiter.limit("10 per minute")
   def api_chat():
       ...
   ```

### Moyen Terme

4. **Migration vers Base de Données**

   **MongoDB** :
   ```python
   from pymongo import MongoClient

   client = MongoClient('mongodb://localhost:27017/')
   db = client['legichat']
   messages_collection = db['messages']

   # Sauvegarder un message
   messages_collection.insert_one({
       "conversationId": conversation_id,
       "role": "user",
       "content": message,
       "timestamp": datetime.utcnow()
   })

   # Récupérer l'historique
   history = list(messages_collection.find(
       {"conversationId": conversation_id}
   ).sort("timestamp", 1))
   ```

   **PostgreSQL** :
   ```python
   from sqlalchemy import create_engine, Column, String, DateTime, Text
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import sessionmaker

   engine = create_engine('postgresql://user:pass@localhost/legichat')
   Base = declarative_base()

   class Message(Base):
       __tablename__ = 'messages'
       id = Column(String, primary_key=True)
       conversation_id = Column(String, index=True)
       role = Column(String)
       content = Column(Text)
       timestamp = Column(DateTime, default=datetime.utcnow)

   Base.metadata.create_all(engine)
   Session = sessionmaker(bind=engine)
   ```

5. **Authentification Utilisateur**
   - JWT tokens
   - OAuth2 (Google, Facebook)
   - Associer conversations à des utilisateurs

6. **Cache Redis**
   ```python
   import redis

   redis_client = redis.Redis(host='localhost', port=6379, db=0)

   # Cache les embeddings de questions fréquentes
   cache_key = f"question:{hash(message)}"
   cached = redis_client.get(cache_key)
   if cached:
       return cached.decode('utf-8')

   # Générer et cacher
   response = process_question_with_context(...)
   redis_client.setex(cache_key, 3600, response)  # 1h TTL
   ```

7. **Tests Automatisés**
   ```python
   # tests/test_api_chat.py
   import pytest
   from app import app

   @pytest.fixture
   def client():
       with app.test_client() as client:
           yield client

   def test_api_chat_success(client):
       response = client.post('/api/chat', json={
           'conversationId': 'test-123',
           'message': 'Bonjour'
       })
       assert response.status_code == 200
       data = response.get_json()
       assert data['role'] == 'assistant'
       assert 'content' in data

   def test_api_chat_missing_message(client):
       response = client.post('/api/chat', json={
           'conversationId': 'test-123'
       })
       assert response.status_code == 400
   ```

### Long Terme

8. **Streaming avec Server-Sent Events (SSE)**
   - Pour retour aux réponses progressives
   - Compatible Angular avec EventSource API

9. **WebSocket pour Real-Time**
   - Flask-SocketIO
   - Conversations en temps réel

10. **Déploiement Production**
    - Gunicorn ou uWSGI au lieu de Flask dev server
    - Nginx en reverse proxy
    - Docker + Docker Compose
    - CI/CD (GitHub Actions, GitLab CI)
    - Monitoring (Prometheus, Grafana)

---

## 📚 Ressources

### Documentation Officielle
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask-CORS](https://flask-cors.readthedocs.io/)
- [Mistral AI API](https://docs.mistral.ai/)
- [Angular HTTP Client](https://angular.io/guide/http)

### Tutoriels Connexes
- [REST API Best Practices](https://restfulapi.net/)
- [JWT Authentication with Flask](https://flask-jwt-extended.readthedocs.io/)
- [PostgreSQL with SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
- [MongoDB with Python](https://pymongo.readthedocs.io/)

---

## 🐛 Dépannage

### Erreur : "ModuleNotFoundError: No module named 'flask_cors'"

**Solution** :
```bash
pip install flask-cors
```

### Erreur CORS dans le navigateur

**Symptôme** :
```
Access to XMLHttpRequest at 'http://localhost:5000/api/chat' from origin
'http://localhost:4200' has been blocked by CORS policy
```

**Solutions** :
1. Vérifier que le backend tourne sur le port 5000
2. Vérifier la configuration CORS dans app.py (ligne 29)
3. Vérifier que `supports_credentials=True` est présent
4. Redémarrer le serveur Flask

### Backend ne répond pas / Timeout

**Solutions** :
1. Vérifier que la clé API Mistral est valide
2. Vérifier la connexion internet
3. Augmenter le timeout côté frontend :
   ```typescript
   this.http.post(..., { timeout: 30000 }) // 30 secondes
   ```
4. Vérifier les logs backend (terminal où `python app.py` tourne)

### Réponses incohérentes / Pas de contexte

**Cause** : L'historique est perdu (serveur redémarré ou conversationId différent)

**Solutions** :
1. Vérifier que le même `conversationId` est utilisé
2. Implémenter la persistance en base de données
3. Vérifier les logs backend : `print(conversations_history[conversation_id])`

### Erreur 500 lors de l'appel Mistral

**Symptôme** :
```json
{
  "error": "An error occurred processing your request"
}
```

**Solutions** :
1. Vérifier la clé API Mistral
2. Vérifier le quota de l'API (crédits épuisés ?)
3. Activer le mode debug pour voir l'erreur détaillée :
   ```python
   # app.py ligne 244
   app.run(debug=True, threaded=True)
   ```
4. Consulter les logs du terminal backend

---

## 📝 Changelog

### Version 2.0 (2025-10-22)

**Ajouté** :
- Endpoint `/api/chat` pour frontend Angular
- Configuration CORS pour `localhost:4200`
- Gestion d'historique conversationnel par `conversationId`
- Génération d'IDs de messages côté backend
- Validation des entrées stricte
- Gestion d'erreurs structurée (JSON)
- Format de réponse ISO 8601 pour timestamps
- Fonction `generate_mistral_complete()` pour réponses complètes
- Fonction `process_question_with_context()` pour RAG avec contexte
- Fichier `.env.example` pour configuration
- Documentation `INTEGRATION.md`

**Modifié** :
- Imports : ajout de `jsonify`, `CORS`, `datetime`, `defaultdict`
- Structure de stockage : `conversations_history` remplace partiellement les sessions Flask

**Conservé** :
- Endpoint `/stream` (rétrocompatibilité)
- Toute la logique RAG (FAISS, embeddings, Mistral)
- Extraction PDF et OCR
- Recherche de documents juridiques

---

## 👥 Support

Pour toute question ou problème :

1. **Vérifier la documentation** : Ce fichier + `README.md`
2. **Consulter les logs** : Terminal où `python app.py` tourne
3. **Tester avec curl** : Isoler si le problème vient du backend ou frontend
4. **Mode debug** : Activer `debug=True` dans `app.run()`

---

**Document maintenu par l'équipe LegiChat - Dernière mise à jour : 2025-10-22**
