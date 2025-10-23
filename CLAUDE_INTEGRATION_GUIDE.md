# 🤖 Guide d'Intégration pour Claude AI

**Objectif** : Intégrer le backend LegiChat Flask avec un frontend Angular 20
**Temps estimé** : 15-30 minutes

---

## 📌 Contexte Rapide

### Backend
- **Techno** : Flask + Mistral AI + FAISS
- **Port** : `http://localhost:5000`
- **Contexte** : Documents juridiques du **Burkina Faso** (arrêtés, décrets, lois)
- **Endpoint** : `POST /api/chat`

### Ce qui a changé
Le backend retourne maintenant un champ **`metadata`** avec :
- `responseType` : Type de réponse (5 types différents)
- `country` : Toujours "Burkina Faso"
- `sources` : Documents juridiques utilisés avec scores de pertinence

---

## 🎯 Contrat API

### Requête
```json
POST http://localhost:5000/api/chat

{
  "conversationId": "conv-1729459200-abc",
  "message": "Quelle est la procédure ?"
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

## 💻 Code TypeScript à Intégrer

### 1. Interfaces (models/message.model.ts ou interfaces/)

```typescript
export interface ResponseMetadata {
  responseType: 'legal_answer' | 'document_link' | 'document_summary' | 'not_found' | 'error';
  country: string;
  sources: Array<{
    document?: string;      // Nom du document (ex: "ARRETE_016_2023_ALT")
    relevance?: number;     // Score 0-1
    type?: string;          // "Loi", "Décret", "Arrêté"
    numero?: string;        // Numéro du document
    lien?: string;          // URL du PDF
  }>;
}

export interface ChatResponse {
  id: string;
  conversationId: string;
  content: string;
  role: 'assistant';
  timestamp: string;
  metadata: ResponseMetadata;  // ← NOUVEAU
}

export interface Message {
  id: string;
  conversationId: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isLoading?: boolean;
  metadata?: ResponseMetadata;  // ← NOUVEAU (optionnel car user n'en a pas)
}
```

### 2. Service API (services/chat-api.service.ts)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ChatResponse, Message } from '../models/message.model';

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  private apiUrl = 'http://localhost:5000/api';  // ← CONFIGURER

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
        isLoading: false,
        metadata: response.metadata  // ← AJOUTER
      }))
    );
  }
}
```

---

## 🎨 Rendu Frontend

### HTML Template (chat.component.html)

```html
<div class="messages-container">
  <div *ngFor="let message of messages"
       class="message"
       [ngClass]="[message.role, message.metadata?.responseType]">

    <!-- Message Utilisateur -->
    <div *ngIf="message.role === 'user'" class="user-message">
      <div class="content">{{ message.content }}</div>
      <div class="timestamp">{{ message.timestamp | date:'short' }}</div>
    </div>

    <!-- Message Assistant -->
    <div *ngIf="message.role === 'assistant'" class="assistant-message">

      <!-- Réponse Juridique Classique -->
      <ng-container *ngIf="message.metadata?.responseType === 'legal_answer'">
        <div class="legal-icon">⚖️</div>
        <div class="content" [innerHTML]="message.content | sanitizeHtml"></div>

        <!-- Afficher les Sources -->
        <div *ngIf="message.metadata.sources?.length" class="sources-section">
          <div class="sources-title">📚 Sources consultées</div>
          <ul class="sources-list">
            <li *ngFor="let source of message.metadata.sources">
              <span class="source-name">{{ source.document }}</span>
              <span class="source-relevance">
                ({{ source.relevance * 100 | number:'1.0-0' }}%)
              </span>
            </li>
          </ul>
        </div>
      </ng-container>

      <!-- Lien vers Document -->
      <ng-container *ngIf="message.metadata?.responseType === 'document_link'">
        <div class="doc-icon">📄</div>
        <div class="content" [innerHTML]="message.content | sanitizeHtml"></div>
        <button *ngIf="message.metadata.sources?.[0]?.lien"
                (click)="openDocument(message.metadata.sources[0].lien)"
                class="btn-download">
          📥 Télécharger le document
        </button>
      </ng-container>

      <!-- Résumé de Document -->
      <ng-container *ngIf="message.metadata?.responseType === 'document_summary'">
        <div class="summary-header">📋 Résumé du document</div>
        <div class="content" [innerHTML]="message.content | sanitizeHtml"></div>
      </ng-container>

      <!-- Information Non Trouvée -->
      <ng-container *ngIf="message.metadata?.responseType === 'not_found'">
        <div class="warning-message">
          <span class="icon">⚠️</span>
          <span class="text">{{ message.content }}</span>
        </div>
      </ng-container>

      <!-- Erreur -->
      <ng-container *ngIf="message.metadata?.responseType === 'error'">
        <div class="error-message">
          <span class="icon">❌</span>
          <span class="text">{{ message.content }}</span>
        </div>
      </ng-container>

      <div class="timestamp">{{ message.timestamp | date:'short' }}</div>
    </div>

  </div>
</div>
```

### Component Logic (chat.component.ts)

```typescript
export class ChatComponent implements OnInit {
  messages: Message[] = [];
  currentConversationId: string = '';

  constructor(private chatService: ChatApiService) {}

  ngOnInit() {
    // Générer un ID de conversation unique
    this.currentConversationId = this.generateConversationId();
  }

  sendMessage(userInput: string) {
    // Ajouter le message utilisateur
    const userMessage: Message = {
      id: this.generateMessageId(),
      conversationId: this.currentConversationId,
      content: userInput,
      role: 'user',
      timestamp: new Date()
    };
    this.messages.push(userMessage);

    // Créer un message assistant en chargement
    const loadingMessage: Message = {
      id: this.generateMessageId(),
      conversationId: this.currentConversationId,
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      isLoading: true
    };
    this.messages.push(loadingMessage);

    // Appeler l'API
    this.chatService.sendMessage(this.currentConversationId, userInput)
      .subscribe({
        next: (response) => {
          // Remplacer le message de chargement par la vraie réponse
          const index = this.messages.findIndex(m => m.id === loadingMessage.id);
          if (index !== -1) {
            this.messages[index] = response;
          }
        },
        error: (error) => {
          console.error('Erreur API:', error);
          const index = this.messages.findIndex(m => m.id === loadingMessage.id);
          if (index !== -1) {
            this.messages[index] = {
              ...loadingMessage,
              content: 'Désolé, une erreur s\'est produite.',
              isLoading: false,
              metadata: {
                responseType: 'error',
                country: 'Burkina Faso',
                sources: []
              }
            };
          }
        }
      });
  }

  openDocument(url: string) {
    window.open(url, '_blank');
  }

  private generateConversationId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `conv-${timestamp}-${random}`;
  }

  private generateMessageId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substr(2, 9);
    return `${timestamp}-${random}`;
  }
}
```

### Styles SCSS (chat.component.scss)

```scss
.messages-container {
  padding: 1rem;
  max-width: 800px;
  margin: 0 auto;

  .message {
    margin-bottom: 1.5rem;
    animation: fadeIn 0.3s ease-in;

    &.user {
      .user-message {
        background: #E3F2FD;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        border-radius: 8px;

        .content {
          font-size: 1rem;
          color: #1565C0;
        }

        .timestamp {
          font-size: 0.75rem;
          color: #64B5F6;
          margin-top: 0.5rem;
        }
      }
    }

    &.assistant {
      .assistant-message {
        padding: 1rem;
        border-radius: 8px;
        position: relative;

        .content {
          font-size: 1rem;
          line-height: 1.6;
        }

        .timestamp {
          font-size: 0.75rem;
          color: #999;
          margin-top: 0.5rem;
        }
      }

      // Style par type de réponse
      &.legal-answer .assistant-message {
        background: #E8F5E9;
        border-left: 4px solid #4CAF50;

        .legal-icon {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .sources-section {
          margin-top: 1rem;
          padding-top: 1rem;
          border-top: 1px solid #C8E6C9;

          .sources-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #388E3C;
            margin-bottom: 0.5rem;
          }

          .sources-list {
            list-style: none;
            padding: 0;
            font-size: 0.85rem;

            li {
              padding: 0.25rem 0;
              color: #4CAF50;

              .source-name {
                font-weight: 500;
              }

              .source-relevance {
                color: #66BB6A;
                margin-left: 0.5rem;
              }
            }
          }
        }
      }

      &.document-link .assistant-message {
        background: #FFF3E0;
        border-left: 4px solid #FF9800;

        .doc-icon {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .btn-download {
          margin-top: 1rem;
          padding: 0.75rem 1.5rem;
          background: #FF9800;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 0.95rem;
          cursor: pointer;
          transition: background 0.2s;

          &:hover {
            background: #F57C00;
          }
        }
      }

      &.document-summary .assistant-message {
        background: #F3E5F5;
        border-left: 4px solid #9C27B0;

        .summary-header {
          font-weight: 600;
          font-size: 1.1rem;
          color: #7B1FA2;
          margin-bottom: 0.75rem;
        }
      }

      &.not-found .assistant-message {
        background: #FFF8E1;
        border-left: 4px solid #FFC107;

        .warning-message {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: #F57F17;

          .icon {
            font-size: 1.5rem;
          }
        }
      }

      &.error .assistant-message {
        background: #FFEBEE;
        border-left: 4px solid #F44336;

        .error-message {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: #C62828;

          .icon {
            font-size: 1.5rem;
          }
        }
      }
    }
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## ✅ Checklist d'Intégration

### Backend
- [x] Endpoint `/api/chat` opérationnel
- [x] CORS configuré pour `localhost:4200`
- [x] Champ `metadata` dans les réponses
- [x] Contexte Burkina Faso configuré

### Frontend (À faire)
- [ ] Ajouter interface `ResponseMetadata`
- [ ] Modifier interfaces `ChatResponse` et `Message`
- [ ] Mettre à jour `sendMessage()` dans le service
- [ ] Configurer `apiUrl = 'http://localhost:5000/api'`
- [ ] Ajouter mapping `metadata: response.metadata`
- [ ] Implémenter rendu conditionnel par `responseType`
- [ ] Ajouter styles SCSS pour chaque type
- [ ] Tester avec le backend démarré

---

## 🧪 Tests

### 1. Vérifier Backend Disponible
```bash
# Dans le répertoire LegiChatBackend
python app.py

# Dans un autre terminal
curl http://localhost:5000/
```

### 2. Tester l'API
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-001",
    "message": "Bonjour"
  }'
```

### 3. Tester avec Frontend
1. Démarrer le backend : `python app.py`
2. Démarrer le frontend : `npm start`
3. Ouvrir `http://localhost:4200`
4. Envoyer un message
5. Vérifier dans Network (F12) :
   - Requête POST vers `/api/chat`
   - Status 200
   - Réponse avec champ `metadata`

---

## 📊 Types de Réponses - Référence Rapide

| responseType | Trigger | Exemple |
|--------------|---------|---------|
| `legal_answer` | Question juridique standard | "Quelle est la procédure..." |
| `document_link` | Recherche de document | "Cherche la loi 2023-015" |
| `document_summary` | Demande de résumé | "oui" après un lien |
| `not_found` | Info non trouvée | Question hors contexte |
| `error` | Erreur serveur | Problème technique |

---

## 🌍 Contexte Important

**Burkina Faso** : Tous les documents et réponses concernent le droit burkinabè.
- Le champ `metadata.country` est toujours `"Burkina Faso"`
- Sources : Arrêtés, décrets, lois du Burkina Faso
- Pas de données sur d'autres pays

---

## 🔗 Ressources

**Documentation complète** : Voir `API_DOCUMENTATION.md` pour :
- Architecture détaillée
- Guide d'installation backend
- Dépannage complet
- Tests avancés

**Branche Git** : `claude/understand-code-011CUNZAQ26yUeUpjYPjQfxC`

---

## 💡 Conseils pour Claude AI

### Quand tu intègres ce code :

1. **Priorité** : Commence par les interfaces TypeScript
2. **Service** : Assure-toi que `apiUrl` pointe vers `localhost:5000`
3. **Mapping** : N'oublie pas `metadata: response.metadata` dans le pipe
4. **Sanitize HTML** : Le `content` peut contenir du HTML (liens), utilise un pipe
5. **Styles** : Les classes CSS utilisent `ngClass` avec `message.metadata?.responseType`
6. **Tests** : Vérifie que le backend tourne avant de tester le frontend

### Structure du projet Angular attendue :
```
src/app/
├── core/
│   ├── models/
│   │   └── message.model.ts       // Ajouter ResponseMetadata
│   └── services/
│       └── chat-api.service.ts    // Modifier sendMessage
└── features/
    └── chat/
        ├── chat.component.ts      // Logique
        ├── chat.component.html    // Template
        └── chat.component.scss    // Styles
```

---

**Ce guide contient tout le code nécessaire. Bon courage ! 🚀**
