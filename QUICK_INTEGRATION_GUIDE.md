# 🚀 Guide d'Intégration Backend → Frontend LegiChat

**Contexte** : Backend Flask (Burkina Faso) → Frontend Angular 20
**Endpoint** : `POST http://localhost:5000/api/chat`

---

## 📡 L'Essentiel

### Requête
```json
POST /api/chat
{
  "conversationId": "conv-1729459200-abc",
  "message": "Quels sont les aéroports internationaux ?"
}
```

### Réponse
```json
{
  "id": "msg-1729459201-xyz",
  "conversationId": "conv-1729459200-abc",
  "content": "Selon l'article 1 de l'arrêté n°016/2023...",
  "role": "assistant",
  "timestamp": "2025-10-23T14:30:01.000Z",
  "metadata": {
    "responseType": "legal_answer",
    "country": "Burkina Faso",
    "sources": [
      {"document": "ARRETE_016_2023_ALT", "relevance": 0.95}
    ]
  }
}
```

---

## 💻 Code TypeScript à Ajouter

### 1. Interface (models/message.model.ts)

```typescript
export interface ResponseMetadata {
  responseType: 'legal_answer' | 'document_link' | 'document_summary' | 'not_found' | 'error';
  country: string;
  sources: Array<{
    document?: string;
    relevance?: number;
    type?: string;
    numero?: string;
    lien?: string;
  }>;
}

export interface ChatResponse {
  id: string;
  conversationId: string;
  content: string;
  role: 'assistant';
  timestamp: string;
  metadata: ResponseMetadata;  // ← AJOUTER
}

export interface Message {
  id: string;
  conversationId: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isLoading?: boolean;
  metadata?: ResponseMetadata;  // ← AJOUTER
}
```

### 2. Service (chat-api.service.ts)

```typescript
private apiUrl = 'http://localhost:5000/api';

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
      isLoading: false,
      metadata: response.metadata  // ← AJOUTER
    }))
  );
}
```

---

## 🎨 Rendu Frontend (chat.component.html)

```html
<div class="message assistant" [ngClass]="message.metadata?.responseType">

  <!-- Réponse juridique -->
  <div *ngIf="message.metadata?.responseType === 'legal_answer'">
    <div [innerHTML]="message.content | sanitizeHtml"></div>

    <!-- Sources -->
    <div *ngIf="message.metadata.sources?.length" class="sources">
      <strong>📚 Sources :</strong>
      <ul>
        <li *ngFor="let source of message.metadata.sources">
          {{ source.document }} ({{ source.relevance * 100 | number:'1.0-0' }}%)
        </li>
      </ul>
    </div>
  </div>

  <!-- Lien document -->
  <div *ngIf="message.metadata?.responseType === 'document_link'">
    <div [innerHTML]="message.content | sanitizeHtml"></div>
  </div>

  <!-- Résumé -->
  <div *ngIf="message.metadata?.responseType === 'document_summary'">
    <strong>📋 Résumé :</strong>
    <div [innerHTML]="message.content | sanitizeHtml"></div>
  </div>

  <!-- Non trouvé -->
  <div *ngIf="message.metadata?.responseType === 'not_found'" class="warning">
    ⚠️ {{ message.content }}
  </div>

</div>
```

---

## 🎨 Styles (chat.component.scss)

```scss
.message.assistant {

  &.legal-answer {
    border-left: 4px solid #2196F3;
    background: #E3F2FD;

    .sources {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid #BBDEFB;
      font-size: 0.85rem;

      ul {
        list-style: none;
        padding: 0;
      }
    }
  }

  &.document-link {
    border-left: 4px solid #4CAF50;
    background: #E8F5E9;
  }

  &.document-summary {
    border-left: 4px solid #9C27B0;
    background: #F3E5F5;
  }

  &.not-found {
    border-left: 4px solid #FF9800;
    background: #FFF3E0;
    color: #E65100;
  }
}
```

---

## 📋 Types de Réponses

| responseType | Quand | Affichage |
|--------------|-------|-----------|
| `legal_answer` | Question juridique classique | Texte + sources |
| `document_link` | Document trouvé | Lien cliquable |
| `document_summary` | Résumé demandé | Card spéciale |
| `not_found` | Info non trouvée | Avertissement |
| `error` | Erreur serveur | Message d'erreur |

---

## 🧪 Test Backend

```bash
# Vérifier que le backend répond
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-123","message":"Bonjour"}'

# Réponse attendue (JSON avec metadata)
```

---

## ⚡ Démarrage Rapide

### 1. Backend
```bash
cd LegiChatBackend
python app.py
# → http://localhost:5000
```

### 2. Frontend
```bash
cd LegiChatUI
npm start
# → http://localhost:4200
```

### 3. Configuration
```typescript
// Dans chat-api.service.ts
private apiUrl = 'http://localhost:5000/api';
```

---

## ✅ Checklist Intégration

- [ ] Ajouter `ResponseMetadata` interface
- [ ] Modifier `ChatResponse` et `Message` interfaces
- [ ] Mettre à jour `sendMessage()` dans le service
- [ ] Ajouter `metadata: response.metadata` dans le mapping
- [ ] Implémenter rendu conditionnel avec `*ngIf`
- [ ] Ajouter styles SCSS par type
- [ ] Tester avec le backend démarré

---

## 🌍 Important : Contexte Burkina Faso

- Toutes les réponses concernent le **Burkina Faso** (pas le Sénégal)
- `metadata.country` = "Burkina Faso"
- Sources = documents juridiques burkinabè (arrêtés, décrets, lois)

---

## 📞 Référence Complète

**Docs détaillées** : Voir `BACKEND_API_REFERENCE.md` dans LegiChatBackend

**Branche** : `claude/understand-code-011CUNZAQ26yUeUpjYPjQfxC`

---

## 🔄 Exemple Complet

```typescript
// 1. Envoyer message
this.chatService.sendMessage(conversationId, userMessage)
  .subscribe({
    next: (response: Message) => {
      // 2. Accéder au type
      const type = response.metadata?.responseType;

      // 3. Accéder aux sources
      const sources = response.metadata?.sources || [];

      // 4. Afficher selon le type
      this.displayMessage(response);
    },
    error: (err) => console.error('Erreur:', err)
  });
```

---

**Résumé** : Ajoutez le champ `metadata` à vos interfaces TypeScript et utilisez `responseType` pour un rendu conditionnel adapté. Le backend retourne maintenant des métadonnées enrichies pour chaque réponse ! 🚀
