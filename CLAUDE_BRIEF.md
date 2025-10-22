# 🤖 Claude Brief - LegiChat Integration

**Purpose**: This file helps Claude AI understand how to integrate the Angular frontend with the Flask backend in seconds.

---

## 🎯 Core Facts

- **Backend**: Flask on `http://localhost:5000`
- **Frontend**: Angular 20 on `http://localhost:4200`
- **Endpoint**: `POST /api/chat`
- **Data Flow**: Frontend generates `conversationId` → Backend maintains conversation context

---

## 📡 The One Endpoint You Need

```
POST http://localhost:5000/api/chat
Content-Type: application/json

{
  "conversationId": "conv-{timestamp}-{random}",  // Frontend generates
  "message": "User question here"
}

→ Returns:
{
  "id": "msg-{timestamp}-{random}",              // Backend generates
  "conversationId": "conv-...",                  // Same as request
  "content": "AI response text (may contain HTML links)",
  "role": "assistant",
  "timestamp": "2025-10-22T14:30:01.000Z"       // ISO 8601
}
```

**That's it. One endpoint. JSON in, JSON out.**

---

## ⚡ 3-Step Integration

### Step 1: Frontend Config
```typescript
// src/app/core/services/chat-api.service.ts
private apiUrl = 'http://localhost:5000/api';
```

### Step 2: Send Message
```typescript
this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
  conversationId: conversationId,
  message: userMessage
}).subscribe(response => {
  // response.content contains AI answer
  displayMessage(response);
});
```

### Step 3: Handle Context
**Key**: Use the SAME `conversationId` for all messages in a conversation.
Backend automatically maintains context.

---

## 🧠 Backend Intelligence

The backend does 3 things automatically based on message content:

1. **Document Search**: Message like "cherche loi 2023-15" → Returns PDF link
2. **Summarization**: User says "oui" after receiving PDF → Returns summary
3. **Legal Q&A** (default): Any question → RAG with FAISS + Mistral AI

**You don't choose the mode. Backend detects it automatically.**

---

## 🔧 How It Works Behind the Scenes

```
User message → Backend detects type →
                ├─ "cherche loi X" → Search metadata → Return PDF link
                ├─ "oui"/"résume" after PDF → Extract PDF → Mistral summarize
                └─ Normal question → FAISS search → Top 10 articles → Mistral with context

Backend stores conversation history by conversationId:
conversations_history["conv-123"] = [
  {"role": "user", "content": "Message 1"},
  {"role": "assistant", "content": "Response 1"},
  {"role": "user", "content": "Message 2"},
  ...
]
```

---

## 🚀 Start Both Servers

```bash
# Terminal 1 - Backend
cd LegiChatBackend
python app.py
# → http://localhost:5000

# Terminal 2 - Frontend
cd LegiChatUI
npm start
# → http://localhost:4200
```

---

## 🧪 Test Before Connecting Frontend

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-1","message":"Bonjour"}'

# Should return: {"id":"msg-...","conversationId":"test-1","content":"Bonjour ! ...","role":"assistant","timestamp":"..."}
```

---

## ⚠️ Common Mistakes

| Mistake | Fix |
|---------|-----|
| Different `conversationId` each time | Use SAME ID for entire conversation |
| CORS error | Backend must run on port 5000, frontend on 4200 |
| 500 error | Check Mistral API key is valid |
| No context | Verify same conversationId being sent |

---

## 🎨 Frontend Implementation Pattern

```typescript
export class ChatService {
  private apiUrl = 'http://localhost:5000/api';

  sendMessage(conversationId: string, message: string): Observable<Message> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
      conversationId,
      message
    }).pipe(
      map(res => ({
        id: res.id,
        conversationId: res.conversationId,
        content: res.content,
        role: 'assistant',
        timestamp: new Date(res.timestamp)
      }))
    );
  }
}

// Usage
this.chatService.sendMessage(this.currentConversationId, userInput)
  .subscribe({
    next: (msg) => this.displayMessage(msg),
    error: (err) => this.handleError(err)
  });
```

---

## 📋 Checklist for Claude

When helping integrate frontend ↔ backend:

- [ ] Verify `apiUrl` points to `http://localhost:5000/api`
- [ ] Ensure `conversationId` is generated ONCE per conversation
- [ ] Check same `conversationId` used for follow-up messages
- [ ] Confirm request body has both `conversationId` and `message`
- [ ] Parse `response.content` for display (may contain HTML)
- [ ] Convert `response.timestamp` string to Date object
- [ ] Handle errors (400 for validation, 500 for server errors)
- [ ] Test with curl first before blaming frontend

---

## 🔍 Debug Workflow

```
Issue: Frontend not receiving response
  ├─ Is backend running? → curl http://localhost:5000/
  ├─ Is endpoint working? → curl -X POST http://localhost:5000/api/chat ...
  ├─ CORS configured? → Check browser console for CORS error
  └─ Network tab shows request? → Check Status Code (200/400/500)

Issue: No conversation context
  └─ Are you sending different conversationId?
     → Print conversationId in both messages, verify they match

Issue: 500 Internal Server Error
  └─ Check backend terminal logs
     → Usually Mistral API key issue or FAISS files missing
```

---

## 📦 File Structure Reference

```
LegiChatBackend/
├── app.py                    ← Main backend (line 297: /api/chat endpoint)
├── faiss_index/              ← Embeddings & search index
│   ├── embeddings.npy
│   ├── index.faiss
│   ├── fichier.csv
│   └── metadatas.pkl
├── static/pdfs/              ← Legal documents PDFs
├── requirements.txt          ← Dependencies (includes flask-cors)
├── .env.example              ← Config template
├── BACKEND_API_REFERENCE.md  ← Detailed API docs
└── INTEGRATION.md            ← Full setup guide

LegiChatUI/
└── src/app/core/
    ├── services/
    │   └── chat-api.service.ts    ← Configure apiUrl here
    ├── models/
    │   └── message.model.ts       ← Message interface
    └── interfaces/
        └── chat-api.interface.ts  ← ChatResponse interface
```

---

## 💡 Key Insight for Claude

The frontend Angular app already has:
✅ Conversation management (LocalStorage)
✅ Message display logic
✅ conversationId generation
✅ HTTP service skeleton

**All it needs is:**
1. Change `apiUrl` to backend URL
2. Uncomment the real HTTP code
3. Comment out the mock code

**The backend already handles:**
✅ Conversation context (by conversationId)
✅ RAG with FAISS
✅ Mistral AI integration
✅ Document search & summarization
✅ CORS configuration

**They're ready to connect. Just wire them up.**

---

## 🎯 Success Criteria

Integration is successful when:
1. User sends message in Angular UI
2. Network tab shows POST to `http://localhost:5000/api/chat` with 200 status
3. Response appears in chat UI
4. Follow-up question gets contextual answer (proves conversation memory works)
5. No CORS errors in browser console

---

## 📞 Quick Reference

```typescript
// Request format
interface Request {
  conversationId: string;  // e.g., "conv-1729459200-abc123"
  message: string;         // e.g., "Quelle est la procédure..."
}

// Response format
interface Response {
  id: string;              // e.g., "msg-1729459201-xyz789"
  conversationId: string;  // same as request
  content: string;         // AI answer
  role: "assistant";       // always "assistant"
  timestamp: string;       // e.g., "2025-10-22T14:30:01.000Z"
}

// Error format
interface Error {
  error: string;           // e.g., "message is required"
  details?: string;        // only in debug mode
}
```

---

## 🚦 Status

- Backend: ✅ Ready (port 5000)
- CORS: ✅ Configured for localhost:4200
- Endpoint: ✅ `/api/chat` functional
- Context: ✅ Conversation history works
- Frontend: ⏳ Needs `apiUrl` configuration

**Next Action**: Configure frontend `apiUrl` and test.

---

**This brief is optimized for Claude AI to quickly understand the entire integration in under 60 seconds.**

For humans: See `BACKEND_API_REFERENCE.md` (detailed) or `INTEGRATION.md` (comprehensive).
