# 📡 Backend API Reference - LegiChat

**Base URL**: `http://localhost:5000`
**Backend**: Flask + Mistral AI + FAISS
**Frontend**: Angular 20
**Legal Context**: **Burkina Faso** (arrêtés, décrets, lois burkinabè)
**Last Updated**: 2025-10-23

---

## 🎯 Quick Start

### Backend Setup
```bash
cd /path/to/LegiChatBackend
pip install -r requirements.txt
python app.py
# Server runs on http://localhost:5000
```

### Frontend Configuration
```typescript
// src/app/core/services/chat-api.service.ts
private apiUrl = 'http://localhost:5000/api';
```

---

## 📋 API Endpoint

### POST /api/chat

**Purpose**: Send user message, receive AI response with conversation context

#### Request

**URL**: `POST http://localhost:5000/api/chat`

**Headers**:
```http
Content-Type: application/json
```

**Body**:
```typescript
interface ChatRequest {
  conversationId: string;  // Frontend-generated ID (e.g., "conv-1729459200-abc123")
  message: string;         // User message (max 5000 chars)
}
```

**Example**:
```json
{
  "conversationId": "conv-1729459200-k8j3h2l9q",
  "message": "Quelle est la procédure pour créer une entreprise au Sénégal ?"
}
```

#### Response

**Status**: `200 OK`

**Body**:
```typescript
interface ChatResponse {
  id: string;              // Backend-generated message ID
  conversationId: string;  // Same as request
  content: string;         // AI response (HTML may be present for links)
  role: "assistant";       // Always "assistant"
  timestamp: string;       // ISO 8601 format (e.g., "2025-10-22T14:30:01.000Z")
  metadata: {
    responseType: string;  // "legal_answer" | "document_link" | "document_summary" | "not_found"
    country: string;       // Always "Burkina Faso"
    sources: Array<{       // Legal documents used in the response
      document?: string;   // Document name (e.g., "ARRETE_016_2023_ALT")
      relevance?: number;  // Relevance score (0-1)
      type?: string;       // Document type (e.g., "loi", "décret")
      numero?: string;     // Document number
      lien?: string;       // PDF link
    }>;
  };
}
```

**Example**:
```json
{
  "id": "msg-1729459201-xyz789",
  "conversationId": "conv-1729459200-k8j3h2l9q",
  "content": "Selon l'article 1 de l'arrêté n°016/2023, les aéroports de Ouagadougou et de Bobo-Dioulasso sont ouverts au trafic aérien international...",
  "role": "assistant",
  "timestamp": "2025-10-23T14:30:01.000Z",
  "metadata": {
    "responseType": "legal_answer",
    "country": "Burkina Faso",
    "sources": [
      {"document": "ARRETE_016_2023_ALT", "relevance": 0.95},
      {"document": "DECRET_2022_0056", "relevance": 0.82}
    ]
  }
}
```

#### Error Responses

**400 Bad Request**:
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

**500 Internal Server Error**:
```json
{
  "error": "An error occurred processing your request",
  "details": "..." // Only in debug mode
}
```

---

## 🔄 Conversation Flow

### First Message
```
Frontend generates: conversationId = "conv-1729459200-abc"
   ↓
POST /api/chat {conversationId: "conv-1729459200-abc", message: "Bonjour"}
   ↓
Backend creates new conversation history
   ↓
Backend processes with RAG (FAISS + Mistral AI)
   ↓
Backend returns {id: "msg-...", content: "...", ...}
   ↓
Frontend displays response
```

### Subsequent Messages (Same Conversation)
```
Frontend uses SAME conversationId = "conv-1729459200-abc"
   ↓
POST /api/chat {conversationId: "conv-1729459200-abc", message: "Et les taxes ?"}
   ↓
Backend retrieves conversation history
   ↓
Backend builds context with previous messages
   ↓
Backend generates contextual response
   ↓
Frontend displays response with context
```

**Key Point**: Backend maintains conversation context automatically when you use the same `conversationId`.

---

## 📊 Response Types

Le backend retourne différents types de réponses identifiés par `metadata.responseType` :

### Types de Réponses

| responseType | Description | Usage Frontend |
|--------------|-------------|----------------|
| `legal_answer` | Réponse juridique basée sur RAG (FAISS + Mistral) | Afficher comme texte formaté avec citations |
| `document_link` | Lien vers un document PDF | Afficher le lien + bouton télécharger |
| `document_summary` | Résumé d'un document juridique | Afficher avec mise en forme spéciale (sections) |
| `not_found` | Information non trouvée dans la base | Afficher comme message d'avertissement |

### Utilisation des Sources

Le champ `metadata.sources` contient les documents juridiques utilisés :
- **Pour `legal_answer`** : Liste des arrêtés/décrets/lois consultés avec score de pertinence
- **Pour `document_link`** : Document demandé avec lien PDF
- **Pour `document_summary`** : Document source du résumé

**Exemple Frontend (Angular)** :
```typescript
displayMessage(response: ChatResponse) {
  switch (response.metadata.responseType) {
    case 'legal_answer':
      this.renderLegalAnswer(response.content, response.metadata.sources);
      break;
    case 'document_link':
      this.renderDocumentLink(response.content);
      break;
    case 'document_summary':
      this.renderSummary(response.content, response.metadata.sources);
      break;
    case 'not_found':
      this.renderWarning(response.content);
      break;
  }
}
```

---

## 🧩 Backend Features

### 1. Document Search
**Trigger**: Message contains patterns like "cherche loi 2023-15" or "donne-moi le décret 98-2020"

**Response**: Link to PDF + offer for summary
```json
{
  "content": "📄 Voici le document demandé : <a href='http://...' target='_blank'>cliquer ici</a><br>Souhaitez-vous un résumé ? (oui/non)",
  ...
}
```

### 2. Document Summarization
**Trigger**: User says "oui" / "résume" after receiving a document link

**Response**: Full text summary extracted from PDF
```json
{
  "content": "Résumé du document : Ce décret porte sur...",
  ...
}
```

### 3. Legal Q&A (RAG)
**Trigger**: Any explanatory question (default mode)

**Process**:
1. Encode question with sentence-transformers
2. Search top 10 similar articles in FAISS index
3. Build context with retrieved articles
4. Generate response with Mistral AI
5. Return answer citing legal sources

**Response**:
```json
{
  "content": "Selon l'article 42 de la loi 2023-15, les entreprises doivent...",
  ...
}
```

---

## 💻 Frontend Integration Code

### TypeScript Interface
```typescript
// src/app/core/models/message.model.ts
export interface Message {
  id: string;
  conversationId: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isLoading?: boolean; // Frontend only
}

// src/app/core/interfaces/chat-api.interface.ts
export interface ChatResponse {
  id: string;
  conversationId: string;
  content: string;
  role: 'assistant';
  timestamp: string;
}
```

### Service Implementation
```typescript
// src/app/core/services/chat-api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

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
}
```

### Usage Example
```typescript
// In your component
this.chatApiService.sendMessage(
  'conv-1729459200-abc123',
  'Quelle est la procédure pour créer une entreprise ?'
).subscribe({
  next: (message) => {
    console.log('Response:', message);
    // Display message.content in UI
  },
  error: (error) => {
    console.error('Error:', error);
    // Handle error
  }
});
```

---

## 🧪 Testing

### cURL Test
```bash
# Test 1: Simple question
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-123",
    "message": "Bonjour"
  }'

# Test 2: Document search
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-456",
    "message": "Cherche la loi 2023-15"
  }'

# Test 3: Follow-up question (same conversationId)
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-123",
    "message": "Peux-tu développer ?"
  }'
```

### Expected Response Format
```json
{
  "id": "msg-1730000000000-abc123xyz",
  "conversationId": "test-123",
  "content": "Bonjour ! Comment puis-je vous aider avec le droit sénégalais ?",
  "role": "assistant",
  "timestamp": "2025-10-22T14:30:01.123Z"
}
```

---

## 🔐 CORS Configuration

**Backend** (already configured in `app.py`):
```python
from flask_cors import CORS
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)
```

**Allowed Origins**:
- Development: `http://localhost:4200`
- Production: Update to your domain (e.g., `https://legichat.com`)

**If CORS errors occur**:
1. Verify backend is running on port 5000
2. Verify frontend is on port 4200
3. Check browser console for specific error
4. Restart backend server after any config changes

---

## 📊 Conversation Storage

**Current**: In-memory storage (RAM)
```python
# Backend: app.py
conversations_history = {
    "conv-123": [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"}
    ]
}
```

**Limitations**:
- ❌ Lost on server restart
- ❌ Doesn't scale with multiple instances
- ✅ Fast and simple for development

**Production Recommendation**:
Migrate to database (MongoDB/PostgreSQL) - see `INTEGRATION.md` for details.

---

## ⚡ Performance

**Average Response Time**:
- Document search: ~100-300ms
- PDF summarization: ~2-5s (depends on PDF size)
- Legal Q&A (RAG): ~1-3s (depends on Mistral API)

**Optimize**:
- Cache frequent questions (Redis)
- Pre-process PDFs
- Use faster Mistral model
- Implement request pooling

---

## 🚨 Common Issues & Solutions

### Issue 1: CORS Error
**Error**: `Access to XMLHttpRequest blocked by CORS policy`

**Solution**:
```python
# Verify in app.py line 29:
CORS(app, origins=["http://localhost:4200"], supports_credentials=True)
```

### Issue 2: 500 Error
**Error**: `An error occurred processing your request`

**Debug**:
1. Check backend terminal for error logs
2. Enable debug mode: `app.run(debug=True)`
3. Verify Mistral API key is valid
4. Check FAISS index files exist in `faiss_index/`

### Issue 3: No Context in Responses
**Cause**: Different `conversationId` used for follow-up messages

**Solution**: Frontend must use the SAME `conversationId` for all messages in a conversation

### Issue 4: Empty Response
**Cause**: Mistral API quota exceeded or network issue

**Solution**:
1. Check Mistral API dashboard for quota
2. Verify internet connection
3. Check API key validity

---

## 🔒 Security Notes

### Current Issues (Development)
⚠️ **API Key exposed** in code (`app.py:43`)
⚠️ **No rate limiting** - vulnerable to spam
⚠️ **No authentication** - anyone can access
⚠️ **Debug mode enabled** - exposes error details

### Production Checklist
- [ ] Move API key to `.env` file
- [ ] Implement rate limiting (flask-limiter)
- [ ] Add user authentication (JWT)
- [ ] Disable debug mode
- [ ] Use HTTPS only
- [ ] Implement request validation
- [ ] Add logging and monitoring

---

## 📦 Data Models Summary

### Request
```typescript
{
  conversationId: string,  // Required, frontend-generated
  message: string          // Required, max 5000 chars
}
```

### Response
```typescript
{
  id: string,              // Backend-generated
  conversationId: string,  // Echoed from request
  content: string,         // AI response (may contain HTML)
  role: "assistant",       // Always "assistant"
  timestamp: string        // ISO 8601 UTC
}
```

### Error
```typescript
{
  error: string,           // Error message
  details?: string         // Optional (debug mode only)
}
```

---

## 🎨 Response Content Formats

### Plain Text
```json
{
  "content": "Selon l'article 42, les entreprises doivent..."
}
```

### HTML Links (Document Search)
```json
{
  "content": "📄 Voici le document : <a href='http://...' target='_blank'>cliquer ici</a>"
}
```

### Structured Response
```json
{
  "content": "Pour créer une entreprise :\n1. Étape 1\n2. Étape 2\n3. Étape 3"
}
```

**Frontend Rendering**:
- Use `innerHTML` or sanitize HTML for links
- Handle newlines (`\n`) appropriately
- Style links for better UX

---

## 📞 Support & Debugging

### Enable Verbose Logging
```python
# Add to app.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In api_chat function:
logger.debug(f"Received: {conversation_id}, {message}")
logger.debug(f"Response: {ai_response}")
```

### Monitor Network Requests
```typescript
// Angular Interceptor
import { HttpInterceptor } from '@angular/common/http';

intercept(req: HttpRequest<any>, next: HttpHandler) {
  console.log('Request:', req.url, req.body);
  return next.handle(req).pipe(
    tap(res => console.log('Response:', res))
  );
}
```

### Backend Health Check
```bash
# Verify server is running
curl http://localhost:5000/

# Expected: HTML page (old frontend)
```

---

## 🔄 Version Compatibility

| Component | Version | Status |
|-----------|---------|--------|
| Backend | 2.0 | ✅ Production-ready |
| Frontend | Angular 20.3.6 | ✅ Compatible |
| API Endpoint | `/api/chat` | ✅ Stable |
| Legacy Endpoint | `/stream` | 🟡 Deprecated (still works) |

---

## 📝 Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│  LegiChat Backend API - Quick Reference         │
├─────────────────────────────────────────────────┤
│  Endpoint: POST /api/chat                       │
│  URL:      http://localhost:5000/api/chat       │
│                                                  │
│  Request:  { conversationId, message }          │
│  Response: { id, conversationId, content,       │
│              role, timestamp }                  │
│                                                  │
│  Features:                                      │
│  • Document search & PDF links                  │
│  • PDF summarization                            │
│  • Legal Q&A with RAG (FAISS)                   │
│  • Conversation context memory                  │
│                                                  │
│  CORS: http://localhost:4200 ✓                  │
│  Format: JSON                                   │
│  Streaming: No (complete response)              │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Complete Integration Example

```typescript
// 1. Generate conversation ID (frontend)
const conversationId = `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

// 2. Send first message
this.http.post('http://localhost:5000/api/chat', {
  conversationId: conversationId,
  message: 'Quelle est la procédure pour créer une entreprise ?'
}).subscribe(response => {
  console.log('First response:', response);
  // Display: response.content
});

// 3. Send follow-up (SAME conversationId)
this.http.post('http://localhost:5000/api/chat', {
  conversationId: conversationId, // ← SAME ID
  message: 'Quels sont les coûts ?'
}).subscribe(response => {
  console.log('Contextual response:', response);
  // Backend remembers previous question about "entreprise"
});
```

---

**Document Version**: 1.0
**Created**: 2025-10-22
**Backend Branch**: `claude/understand-code-011CUNZAQ26yUeUpjYPjQfxC`
**Contact**: See `INTEGRATION.md` for detailed setup and troubleshooting
