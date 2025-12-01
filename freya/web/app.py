"""
FastAPI Web GUI for Freya AI Assistant

A browser-based interface for controlling and debugging Freya.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import logging
from pathlib import Path
from typing import Optional
import subprocess
import json

# Import Freya integration
from freya.web.freya_integration import FreyaIntegration

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Freya Web GUI", version="1.0.0")

# Mount static files and templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Global state
freya_state = {
    "ollama_running": False,
    "model_loaded": None,
    "agents_running": [],
    "conversation_active": False,
    "freya_initialized": False,
}

# WebSocket connections for real-time updates
active_connections: list[WebSocket] = []

# Freya integration instance
freya_integration: Optional[FreyaIntegration] = None


# ============================================================================
# WebSocket Manager
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


# ============================================================================
# Routes
# ============================================================================

@app.get("/")
async def index(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/status")
async def get_status():
    """Get current Freya status."""
    return JSONResponse(freya_state)


@app.post("/api/ollama/start")
async def start_ollama():
    """Start Ollama server."""
    try:
        # Check if already running
        result = subprocess.run(
            ["pgrep", "-f", "ollama"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            freya_state["ollama_running"] = True
            await manager.broadcast({
                "type": "status",
                "message": "Ollama is already running",
                "status": "success"
            })
            return {"status": "success", "message": "Ollama already running"}

        # Start Ollama in background
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait a bit for startup
        await asyncio.sleep(2)

        freya_state["ollama_running"] = True
        await manager.broadcast({
            "type": "status",
            "message": "Ollama server started",
            "status": "success"
        })

        return {"status": "success", "message": "Ollama started"}

    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        await manager.broadcast({
            "type": "error",
            "message": f"Failed to start Ollama: {str(e)}"
        })
        return {"status": "error", "message": str(e)}


@app.post("/api/ollama/stop")
async def stop_ollama():
    """Stop Ollama server."""
    try:
        subprocess.run(["pkill", "-f", "ollama"])
        freya_state["ollama_running"] = False
        freya_state["model_loaded"] = None

        await manager.broadcast({
            "type": "status",
            "message": "Ollama server stopped",
            "status": "success"
        })

        return {"status": "success", "message": "Ollama stopped"}

    except Exception as e:
        logger.error(f"Failed to stop Ollama: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/ollama/models")
async def list_models():
    """List available Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {"status": "error", "models": []}

        # Parse ollama list output
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        models = []

        for line in lines:
            parts = line.split()
            if parts:
                models.append({
                    "name": parts[0],
                    "size": parts[1] if len(parts) > 1 else "unknown"
                })

        return {"status": "success", "models": models}

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return {"status": "error", "models": [], "message": str(e)}


@app.post("/api/ollama/load-model")
async def load_model(model: dict):
    """Load a specific Ollama model."""
    try:
        model_name = model.get("name")
        if not model_name:
            return {"status": "error", "message": "Model name required"}

        # Test model by running a simple query
        result = subprocess.run(
            ["ollama", "run", model_name, "hi"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            freya_state["model_loaded"] = model_name
            await manager.broadcast({
                "type": "status",
                "message": f"Model {model_name} loaded successfully",
                "status": "success"
            })
            return {"status": "success", "message": f"Model {model_name} loaded"}
        else:
            return {"status": "error", "message": "Failed to load model"}

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/chat")
async def chat(message: dict):
    """Send a chat message to Freya."""
    global freya_integration

    user_message = message.get("message", "")

    # Check if Freya is initialized
    if not freya_integration or not freya_integration.is_running:
        return {
            "status": "error",
            "message": "Freya is not initialized. Please start Ollama and load a model first."
        }

    try:
        # Send message to Freya's dialog system
        await freya_integration.send_message(user_message, user_id="web_user")

        return {
            "status": "success",
            "message": "Message sent to Freya"
        }

    except Exception as e:
        logger.error(f"Failed to send message to Freya: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle incoming messages
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# Debug Endpoints
# ============================================================================

@app.get("/api/debug/logs")
async def get_debug_logs():
    """Get recent debug logs (placeholder)."""
    # TODO: Integrate with Freya's logging system
    return {
        "logs": [
            {"level": "INFO", "message": "Freya initialized", "timestamp": "2024-01-01 12:00:00"},
            {"level": "DEBUG", "message": "MessageBus created", "timestamp": "2024-01-01 12:00:01"},
            {"level": "INFO", "message": "Agents started", "timestamp": "2024-01-01 12:00:02"},
        ]
    }


@app.get("/api/debug/agents")
async def get_agent_status():
    """Get status of all agents."""
    global freya_integration

    if not freya_integration or not freya_integration.is_running:
        return {
            "agents": [
                {"name": "DialogAgent", "status": "stopped", "messages_processed": 0},
                {"name": "MemoryAgent", "status": "stopped", "memories_stored": 0},
                {"name": "ToolAgent", "status": "stopped", "tools_executed": 0},
                {"name": "SpeechAgent", "status": "stopped", "recordings": 0},
                {"name": "WakeWordAgent", "status": "stopped", "wake_words_detected": 0},
            ]
        }

    # Return actual status
    status = freya_integration.status
    return {
        "agents": [
            {"name": "DialogAgent", "status": "ready" if status["dialog_agent"] else "stopped", "messages_processed": 0},
            {"name": "MessageBus", "status": "ready" if status["message_bus"] else "stopped"},
            {"name": "LLMClient", "status": "ready" if status["llm_client"] else "stopped", "model": status.get("model")},
        ]
    }


@app.post("/api/freya/initialize")
async def initialize_freya():
    """Initialize Freya's core components."""
    global freya_integration

    if freya_integration and freya_integration.is_running:
        return {
            "status": "success",
            "message": "Freya is already initialized"
        }

    try:
        logger.info("Initializing Freya integration...")
        freya_integration = FreyaIntegration()

        # Register callback for responses
        async def response_callback(response_type: str, data: dict):
            """Handle Freya responses and broadcast to WebSocket."""
            if response_type == "chunk":
                await manager.broadcast({
                    "type": "chat_chunk",
                    "chunk": data["chunk"]
                })
            elif response_type == "complete":
                await manager.broadcast({
                    "type": "chat_response",
                    "message": data["response"]
                })
            elif response_type == "error":
                await manager.broadcast({
                    "type": "error",
                    "message": f"Freya error: {data['error']}"
                })

        freya_integration.register_response_callback(response_callback)

        # Initialize
        success = await freya_integration.initialize()

        if success:
            freya_state["freya_initialized"] = True
            freya_state["conversation_active"] = True

            await manager.broadcast({
                "type": "status",
                "message": "Freya initialized successfully",
                "status": "success"
            })

            return {
                "status": "success",
                "message": "Freya initialized",
                "details": freya_integration.status
            }
        else:
            return {
                "status": "error",
                "message": "Failed to initialize Freya"
            }

    except Exception as e:
        logger.error(f"Failed to initialize Freya: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# Startup / Shutdown Handlers
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info("Freya Web GUI starting up...")
    logger.info("WebSocket manager ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    global freya_integration

    logger.info("Freya Web GUI shutting down...")

    if freya_integration:
        await freya_integration.shutdown()

    logger.info("Shutdown complete")


# ============================================================================
# Server Entry Point
# ============================================================================

def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the FastAPI server."""
    logger.info(f"Starting Freya Web GUI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
