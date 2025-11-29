# Freya Web GUI

A modern, browser-based control panel for Freya AI Assistant.

## 🎯 Features

### Current Features (Working Now)
- ✅ **Ollama Control** - Start/stop Ollama server
- ✅ **Model Management** - List and load Ollama models
- ✅ **Chat Interface** - Text-based conversation (placeholder)
- ✅ **Real-time Updates** - WebSocket connection for live status
- ✅ **Debug Console** - Toggle-able debugging interface with:
  - Real-time logs
  - Agent status monitoring
  - Event tracking
  - Network statistics
- ✅ **Statistics Dashboard** - Session metrics
- ✅ **Toast Notifications** - User feedback
- ✅ **Responsive Design** - Works on desktop and mobile

### Placeholder Features (Ready to Wire Up)
- 🔲 Voice Interaction - Buttons ready, need to connect to SpeechAgent
- 🔲 Wake Word Detection - UI ready, needs WakeWordAgent integration
- 🔲 Memory Viewer - View/manage long-term memories
- 🔲 Camera Controls - Start/stop vision processing
- 🔲 Tool Manager - View and configure available tools
- 🔲 Settings Panel - Adjust temperature, tokens, etc.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn python-multipart jinja2
```

Or if you have the updated requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Launch the Web GUI

```bash
# Simple launch
python run_web_gui.py

# Custom host/port
python run_web_gui.py --host 0.0.0.0 --port 8080

# Development mode with auto-reload
python run_web_gui.py --reload
```

### 3. Open in Browser

Navigate to: **http://localhost:8000**

---

## 📖 User Guide

### Getting Started

1. **Start Ollama Server**
   - Click the "Start" button under "Ollama Server"
   - Status badge will turn green when ready

2. **Load a Model**
   - Select a model from the dropdown (auto-populated)
   - Click "Load Model"
   - Wait for confirmation toast

3. **Start Chatting**
   - Type your message in the chat input
   - Press Enter or click Send
   - Responses appear in the chat window

### Debug Console

Toggle the debug console with the "🐛 Debug Console" button in the header.

**Tabs**:
- **Logs** - Real-time application logs with filtering
- **Agents** - Status of all Freya agents
- **Events** - Event bus activity
- **Network** - WebSocket and API status

---

## 🛠️ Architecture

### Backend (FastAPI)

**File**: `freya/web/app.py`

**Key Components**:
- `FastAPI` app with WebSocket support
- REST API endpoints for Ollama control
- WebSocket manager for real-time updates
- Connection to Freya's agent system (TODO)

**API Endpoints**:
```
GET  /                      - Main UI
GET  /api/status            - Get Freya status
POST /api/ollama/start      - Start Ollama server
POST /api/ollama/stop       - Stop Ollama server
GET  /api/ollama/models     - List available models
POST /api/ollama/load-model - Load specific model
POST /api/chat              - Send chat message
GET  /api/debug/logs        - Get debug logs
GET  /api/debug/agents      - Get agent statuses
WS   /ws                    - WebSocket connection
```

### Frontend

**Files**:
- `templates/index.html` - Main UI structure
- `static/css/style.css` - Modern dark theme styling
- `static/js/app.js` - WebSocket, API calls, interactivity

**UI Sections**:
1. **Header** - Title, debug toggle, connection status
2. **Left Sidebar** - System controls, agents, feature buttons
3. **Main Area** - Chat interface
4. **Right Sidebar** - Statistics and settings
5. **Debug Console** - Toggleable bottom panel

---

## 🔌 Integration Guide

### Connecting to Freya Agents

The web GUI is designed to integrate with Freya's agent architecture.

**Current**: Placeholder responses
**Goal**: Full integration with DialogAgent, MemoryAgent, etc.

#### Example: Integrate DialogAgent

```python
# In app.py

from freya.infrastructure.agents.dialog_agent import DialogAgent
from freya.infrastructure.messaging.message_bus import MessageBus

# Initialize Freya components
message_bus = MessageBus()
dialog_agent = DialogAgent(message_bus, config)

# Update chat endpoint
@app.post("/api/chat")
async def chat(message: dict):
    user_message = message.get("message", "")

    # Publish to dialog agent
    await message_bus.publish("dialog.request", {
        "message": user_message,
        "user_id": "web_user"
    })

    # Subscribe to response
    response = await wait_for_response(message_bus, "dialog.complete")

    return {
        "status": "success",
        "response": response["text"]
    }
```

#### Adding Voice Controls

Wire up the placeholder buttons:

```javascript
// In static/js/app.js

document.getElementById('startListening').addEventListener('click', async () => {
    const result = await apiCall('/api/speech/start', 'POST');
    if (result.status === 'success') {
        showToast('Listening...', 'info');
    }
});
```

```python
# In app.py

@app.post("/api/speech/start")
async def start_speech():
    # Activate SpeechAgent
    await message_bus.publish("speech.listen_request", {})
    return {"status": "success"}
```

---

## 🎨 Customization

### Changing the Theme

Edit `static/css/style.css` and modify the CSS variables:

```css
:root {
    --primary: #6366f1;      /* Change primary color */
    --bg-dark: #0f172a;      /* Change background */
    --text-primary: #f1f5f9; /* Change text color */
}
```

### Adding New Features

1. **Add UI Component** in `templates/index.html`:
```html
<button id="myFeature" class="btn btn-primary">
    <span class="icon">⭐</span> My Feature
</button>
```

2. **Add Event Listener** in `static/js/app.js`:
```javascript
document.getElementById('myFeature').addEventListener('click', async () => {
    const result = await apiCall('/api/my-feature', 'POST');
    showToast('Feature activated!', 'success');
});
```

3. **Add API Endpoint** in `app.py`:
```python
@app.post("/api/my-feature")
async def my_feature():
    # Your logic here
    return {"status": "success", "message": "Done!"}
```

---

## 🐛 Debugging

### Enable Development Mode

```bash
python run_web_gui.py --reload
```

This enables:
- Auto-reload on code changes
- Detailed error messages
- Request logging

### Check WebSocket Connection

Open browser console (F12) and look for:
```
WebSocket connected
```

### View Backend Logs

Server logs appear in the terminal where you ran `run_web_gui.py`.

### Common Issues

**Issue**: Can't connect to Ollama
**Solution**: Make sure Ollama is installed and running:
```bash
ollama serve
```

**Issue**: WebSocket keeps disconnecting
**Solution**: Check firewall settings, ensure port 8000 is open

**Issue**: Models not loading
**Solution**: Pull models first:
```bash
ollama pull llama3.2:3b
ollama pull dolphin3:8b
```

---

## 📝 TODO / Roadmap

### Phase 1: Core Integration (Next)
- [ ] Connect to Freya's MessageBus
- [ ] Integrate DialogAgent for real chat
- [ ] Wire up MemoryAgent for memory display
- [ ] Add proper logging integration

### Phase 2: Voice & Vision
- [ ] Enable voice interaction buttons
- [ ] Add wake word detection control
- [ ] Integrate camera feed display
- [ ] Add face recognition UI

### Phase 3: Advanced Features
- [ ] Tool execution from UI
- [ ] Memory browser/editor
- [ ] Configuration panel
- [ ] Personality trait sliders
- [ ] Multi-user support

### Phase 4: Polish
- [ ] Add keyboard shortcuts
- [ ] Export conversation history
- [ ] Dark/light theme toggle
- [ ] Mobile app (PWA)

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Client)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   HTML/CSS   │  │  JavaScript  │  │  WebSocket   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (Backend)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  REST API    │  │  WebSocket   │  │  Static      │      │
│  │  Endpoints   │  │  Manager     │  │  Files       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ MessageBus Integration
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Freya Agent System                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Dialog   │  │  Memory  │  │  Speech  │  │  Tools   │   │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📄 File Structure

```
freya/web/
├── app.py                 # FastAPI backend
├── README.md              # This file
├── static/
│   ├── css/
│   │   └── style.css      # Styles
│   └── js/
│       └── app.js         # Frontend logic
└── templates/
    └── index.html         # Main UI template

run_web_gui.py             # Launch script (project root)
```

---

## 💡 Tips

1. **Use the Debug Console** - It's your best friend for development
2. **Check Browser Console** - F12 shows JavaScript errors
3. **Watch Server Logs** - Backend errors appear in terminal
4. **Test WebSocket** - Make sure it's connected (green dot in header)
5. **Start Simple** - Get Ollama working first, then add features

---

## 🤝 Contributing

To add a new feature:

1. Add UI component in HTML
2. Style it in CSS
3. Add JavaScript handler
4. Create API endpoint in FastAPI
5. Test and document

---

## 📞 Support

- Check the main Freya README
- Review browser console for errors
- Check FastAPI logs in terminal
- Use the debug console in the UI

---

**Built with ❤️ for the Freya AI Assistant project**
