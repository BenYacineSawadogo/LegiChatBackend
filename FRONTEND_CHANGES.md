# 📢 Changements API Backend - Pour l'Équipe Frontend

**Date**: 2025-10-23
**Version**: 2.1
**Impact**: Structure de réponse enrichie + Métadonnées

---

## 🎯 Changement Principal

La réponse de l'API `/api/chat` inclut maintenant un champ **`metadata`** avec le type de réponse et les sources juridiques utilisées.

---

## 📊 Nouvelle Structure de Réponse

### Avant (v2.0)
```typescript
{
  "id": "msg-...",
  "conversationId": "conv-...",
  "content": "Réponse de l'IA...",
  "role": "assistant",
  "timestamp": "2025-10-23T..."
}
```

### Maintenant (v2.1)
```typescript
{
  "id": "msg-...",
  "conversationId": "conv-...",
  "content": "Réponse de l'IA...",
  "role": "assistant",
  "timestamp": "2025-10-23T...",
  "metadata": {                           // ← NOUVEAU
    "responseType": "legal_answer",       // ← Type de réponse
    "country": "Burkina Faso",            // ← Contexte juridique
    "sources": [                          // ← Documents utilisés
      {
        "document": "ARRETE_016_2023_ALT",
        "relevance": 0.95
      }
    ]
  }
}
```

---

## 🔤 Types de Réponses (`responseType`)

| Valeur | Signification | Rendu Suggéré |
|--------|---------------|---------------|
| `legal_answer` | Réponse juridique classique | Texte avec icône ⚖️, afficher sources |
| `document_link` | Lien vers un PDF | Bouton télécharger avec icône 📄 |
| `document_summary` | Résumé d'un document | Card avec sections structurées |
| `not_found` | Information non trouvée | Message d'alerte ⚠️ |
| `error` | Erreur lors du traitement | Message d'erreur ❌ |

---

## 💻 Modifications TypeScript Nécessaires

### 1. Mettre à Jour l'Interface

**Fichier**: `src/app/core/models/message.model.ts` ou `chat-api.interface.ts`

```typescript
// AJOUTER cette interface
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

// MODIFIER l'interface ChatResponse
export interface ChatResponse {
  id: string;
  conversationId: string;
  content: string;
  role: 'assistant';
  timestamp: string;
  metadata: ResponseMetadata;  // ← AJOUTER
}

// Si vous avez une interface Message, ajouter aussi
export interface Message {
  id: string;
  conversationId: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  isLoading?: boolean;
  metadata?: ResponseMetadata;  // ← AJOUTER (optionnel car user n'en a pas)
}
```

### 2. Adapter le Service API

**Fichier**: `src/app/core/services/chat-api.service.ts`

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
      isLoading: false,
      metadata: response.metadata  // ← AJOUTER
    }))
  );
}
```

---

## 🎨 Exemples d'Utilisation dans les Composants

### Affichage Conditionnel par Type

**Fichier**: `chat.component.html`

```html
<div class="message assistant" [ngClass]="message.metadata?.responseType">

  <!-- Réponse juridique classique -->
  <div *ngIf="message.metadata?.responseType === 'legal_answer'" class="legal-response">
    <div class="content" [innerHTML]="message.content | sanitizeHtml"></div>

    <!-- Afficher les sources -->
    <div *ngIf="message.metadata.sources?.length" class="sources">
      <h4>📚 Sources consultées :</h4>
      <ul>
        <li *ngFor="let source of message.metadata.sources">
          {{ source.document }}
          <span class="relevance">({{ source.relevance * 100 | number:'1.0-0' }}%)</span>
        </li>
      </ul>
    </div>
  </div>

  <!-- Lien vers document -->
  <div *ngIf="message.metadata?.responseType === 'document_link'" class="document-link">
    <div [innerHTML]="message.content | sanitizeHtml"></div>
    <button *ngIf="message.metadata.sources?.[0]?.lien"
            (click)="downloadDocument(message.metadata.sources[0].lien)"
            class="btn-download">
      📥 Télécharger le document
    </button>
  </div>

  <!-- Résumé de document -->
  <div *ngIf="message.metadata?.responseType === 'document_summary'" class="summary">
    <div class="summary-header">📋 Résumé du document</div>
    <div class="content" [innerHTML]="message.content | sanitizeHtml"></div>
  </div>

  <!-- Information non trouvée -->
  <div *ngIf="message.metadata?.responseType === 'not_found'" class="warning">
    <span class="icon">⚠️</span>
    <span>{{ message.content }}</span>
  </div>

  <!-- Erreur -->
  <div *ngIf="message.metadata?.responseType === 'error'" class="error">
    <span class="icon">❌</span>
    <span>{{ message.content }}</span>
  </div>

</div>
```

### Styling par Type

**Fichier**: `chat.component.scss`

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
      color: #546E7A;

      h4 {
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
      }

      ul {
        list-style: none;
        padding-left: 0;

        li {
          padding: 0.25rem 0;

          .relevance {
            color: #1976D2;
            font-weight: 500;
          }
        }
      }
    }
  }

  &.document-link {
    border-left: 4px solid #4CAF50;
    background: #E8F5E9;

    .btn-download {
      margin-top: 1rem;
      padding: 0.5rem 1rem;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;

      &:hover {
        background: #45A049;
      }
    }
  }

  &.document-summary {
    border-left: 4px solid #9C27B0;
    background: #F3E5F5;

    .summary-header {
      font-weight: 600;
      color: #7B1FA2;
      margin-bottom: 0.75rem;
      font-size: 1.1rem;
    }
  }

  &.not-found {
    border-left: 4px solid #FF9800;
    background: #FFF3E0;

    .warning {
      color: #E65100;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
  }

  &.error {
    border-left: 4px solid #F44336;
    background: #FFEBEE;

    .error {
      color: #C62828;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
  }
}
```

### Logique dans le Composant

**Fichier**: `chat.component.ts`

```typescript
export class ChatComponent {

  downloadDocument(url: string): void {
    window.open(url, '_blank');
  }

  getResponseIcon(type: string): string {
    const icons = {
      'legal_answer': '⚖️',
      'document_link': '📄',
      'document_summary': '📋',
      'not_found': '⚠️',
      'error': '❌'
    };
    return icons[type] || '💬';
  }

  // Méthode utile pour filtrer les messages par type
  getLegalAnswers(): Message[] {
    return this.messages.filter(m => m.metadata?.responseType === 'legal_answer');
  }
}
```

---

## 🌍 Contexte Juridique

**Important** : Toutes les réponses concernent maintenant le **Burkina Faso** (et non le Sénégal).

Le champ `metadata.country` sera toujours `"Burkina Faso"`.

---

## 📋 Checklist d'Intégration

### Backend
- [x] ✅ Endpoint `/api/chat` mis à jour
- [x] ✅ Champ `metadata` ajouté
- [x] ✅ Contexte Burkina Faso configuré
- [x] ✅ Documentation à jour

### Frontend (À faire)
- [ ] Mettre à jour l'interface TypeScript (`ChatResponse`, `Message`)
- [ ] Adapter le service API pour mapper `metadata`
- [ ] Ajouter le rendu conditionnel par `responseType`
- [ ] Implémenter l'affichage des sources juridiques
- [ ] Ajouter le styling pour chaque type de réponse
- [ ] Tester avec différents types de questions

---

## 🧪 Tests Suggérés

### 1. Réponse Juridique Classique
```typescript
// Question
"Quels sont les aéroports internationaux au Burkina Faso ?"

// Réponse attendue
{
  ...,
  "metadata": {
    "responseType": "legal_answer",
    "sources": [{"document": "ARRETE_016_2023_ALT", ...}]
  }
}
```

### 2. Recherche de Document
```typescript
// Question
"Cherche-moi la loi 2023-015"

// Réponse attendue
{
  ...,
  "metadata": {
    "responseType": "document_link",
    "sources": [{"type": "Loi", "numero": "2023-015", "lien": "..."}]
  }
}
```

### 3. Demande de Résumé
```typescript
// Après avoir reçu un lien de document
// Question
"oui" (pour demander le résumé)

// Réponse attendue
{
  ...,
  "metadata": {
    "responseType": "document_summary",
    "sources": [{"type": "Loi", "numero": "2023-015", ...}]
  }
}
```

### 4. Information Non Trouvée
```typescript
// Question
"Quelle est la procédure pour importer des girafes ?"

// Réponse attendue
{
  ...,
  "content": "Je n'ai pas trouvé cette information dans les textes juridiques disponibles du Burkina Faso",
  "metadata": {
    "responseType": "not_found",
    "sources": []
  }
}
```

---

## 🔗 Exemple Complet de Réponse

```json
{
  "id": "msg-1730012345678-abc123def",
  "conversationId": "conv-1730012340000-xyz789",
  "content": "Selon l'article 1 de l'arrêté n°016/2023, les aéroports de Ouagadougou et de Bobo-Dioulasso sont ouverts au trafic aérien international. L'article 2 précise que les horaires d'ouverture sont publiés par voie d'information aéronautique.",
  "role": "assistant",
  "timestamp": "2025-10-23T14:30:01.123Z",
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

---

## 📞 Contact

Questions techniques : Voir `BACKEND_API_REFERENCE.md` pour la doc complète

**Changelog** :
- **v2.1** (2025-10-23) : Ajout `metadata` avec types et sources
- **v2.0** (2025-10-22) : Version initiale compatible Angular

---

**Résumé** : Ajoutez le champ `metadata` à vos interfaces et utilisez `responseType` pour un rendu conditionnel intelligent ! 🚀
