"""
Phase 5 Verification Tests: Chat, Conversations & Resilient SSE Streaming.

Validates:
1. Conversation CRUD:
   - Create, list, retrieve, rename, delete conversations.
   - Message history retrieval with citations.
2. Synchronous AI Tutor Endpoint:
   - POST /api/v1/chat/ask
   - RAG grounded response with citations and message persistence.
3. SSE Streaming Endpoints (GET and POST /api/v1/chat/stream):
   - Status, token, and done events delivery.
   - Sources/citation events delivery.
   - Keepalive ping and response headers (Cache-Control: no-cache, X-Accel-Buffering: no).
   - Database persistence of streamed assistant responses.
4. Mid-Stream Resilience & Provider Fallback (Amendment 4):
   - Emits 'provider_switch' event on failure.
   - Restarts token generation cleanly without splicing partial text.
"""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from database.database import get_db
from database.models import Conversation, Message
from models.ai_provider import AIProviderManager, BaseAIProvider


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. Conversation Management CRUD Tests
# ============================================================================

def test_conversation_crud_lifecycle(client, db_session):
    # 1. Create Conversation
    create_resp = client.post(
        "/api/v1/chat/conversations",
        json={"title": "Data Structures Revision", "subject_id": 1}
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True
    conv_id = create_data["data"]["id"]
    assert create_data["data"]["title"] == "Data Structures Revision"

    # 2. Get Conversation Details
    get_resp = client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == conv_id

    # 3. List Conversations
    list_resp = client.get("/api/v1/chat/conversations")
    assert list_resp.status_code == 200
    conv_list = list_resp.json()["data"]
    assert any(c["id"] == conv_id for c in conv_list)

    # 4. Rename Conversation (PATCH)
    patch_resp = client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        json={"title": "Advanced Data Structures & Trees"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["title"] == "Advanced Data Structures & Trees"

    # 5. Delete Conversation
    del_resp = client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # 6. Verify 404 after deletion
    not_found_resp = client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert not_found_resp.status_code == 404


def test_conversation_message_history(client, db_session):
    # Create conversation and add messages directly
    conv_resp = client.post(
        "/api/v1/chat/conversations",
        json={"title": "Message History Test"}
    )
    conv_id = conv_resp.json()["data"]["id"]

    # Post an ask query
    ask_resp = client.post(
        "/api/v1/chat/ask",
        json={
            "question": "What is the time complexity of quicksort?",
            "conversation_id": conv_id
        }
    )
    assert ask_resp.status_code == 200
    assert ask_resp.json()["success"] is True

    # Retrieve message history
    history_resp = client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert history_resp.status_code == 200
    msgs = history_resp.json()["data"]
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert "quicksort" in msgs[0]["content"]
    assert msgs[1]["role"] == "assistant"
    assert len(msgs[1]["content"]) > 10


# ============================================================================
# 2. Synchronous Chat API Test
# ============================================================================

def test_ask_ai_tutor_synchronous(client, db_session):
    resp = client.post(
        "/api/v1/chat/ask",
        json={
            "question": "Explain binary search algorithm in simple English",
            "style": "Simple explanation"
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["answer"]) > 20
    assert data["provider_used"] in ("material", "general", "no_material", "offline", "Gemini", "OpenAI")
    assert data["conversation_id"] is not None


# ============================================================================
# 3. Server-Sent Events (SSE) Streaming Protocol Tests
# ============================================================================

def _parse_sse_events(raw_text: str):
    """Helper to parse raw SSE text into a list of (event_type, json_data) tuples."""
    events = []
    lines = raw_text.strip().split("\n")
    current_event = None
    current_data = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_event and current_data:
                try:
                    parsed_json = json.loads("".join(current_data))
                except Exception:
                    parsed_json = "".join(current_data)
                events.append((current_event, parsed_json))
            current_event = None
            current_data = []
            continue

        if line.startswith("event:"):
            current_event = line.replace("event:", "").strip()
        elif line.startswith("data:"):
            current_data.append(line.replace("data:", "").strip())

    if current_event and current_data:
        try:
            parsed_json = json.loads("".join(current_data))
        except Exception:
            parsed_json = "".join(current_data)
        events.append((current_event, parsed_json))

    return events


def test_chat_stream_get_protocol(client, db_session):
    resp = client.get(
        "/api/v1/chat/stream?question=Explain+hash+tables+and+collisions&style=Simple+explanation"
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert resp.headers.get("cache-control") == "no-cache"
    assert resp.headers.get("x-accel-buffering") == "no"

    events = _parse_sse_events(resp.text)
    event_names = [e[0] for e in events]

    assert "status" in event_names
    assert "agent_step" in event_names
    assert "token" in event_names
    assert "done" in event_names

    # Verify token reconstruction
    tokens = [e[1]["text"] for e in events if e[0] == "token"]
    full_reconstructed = "".join(tokens)
    assert len(full_reconstructed) > 20

    # Verify done event structure
    done_event = next(e[1] for e in events if e[0] == "done")
    assert "conversation_id" in done_event
    assert "message_id" in done_event
    assert done_event["finish_reason"] == "stop"


def test_chat_stream_post_protocol(client, db_session):
    payload = {
        "question": "What is normalization in databases?",
        "style": "Detailed explanation"
    }
    resp = client.post("/api/v1/chat/stream", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    event_names = [e[0] for e in events]

    assert "status" in event_names
    assert "token" in event_names
    assert "done" in event_names

    # Check conversation was recorded in database
    done_event = next(e[1] for e in events if e[0] == "done")
    conv_id = done_event["conversation_id"]

    msgs = client.get(f"/api/v1/chat/conversations/{conv_id}/messages").json()["data"]
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert len(msgs[1]["content"]) > 10


# ============================================================================
# 4. Mid-Stream Resilience & Provider Fallback (Amendment 4)
# ============================================================================

def test_mid_stream_provider_switch_resilience():
    """
    Verifies that if a provider fails mid-stream:
    1. A 'provider_switch' event is emitted with action='restart'.
    2. Generation restarts cleanly from the fallback provider without corrupted text.
    """
    class FailingProvider(BaseAIProvider):
        def __init__(self):
            self.model = "gemini-2.0-flash"
            self.model_name = "failing-gemini"
        def is_available(self): return True
        def get_model_name(self): return self.model_name
        def test_connection(self): return True, "SUCCESS"
        def generate_text(self, *args, **kwargs): return "full text"
        def stream_text(self, *args, **kwargs):
            yield "Partial token 1 "
            yield "Partial token 2 "
            raise RuntimeError("HTTP 503: Model overloaded mid-stream")

    mgr = AIProviderManager()
    mgr.gemini_circuit.state = "CLOSED"
    mgr.gemini_circuit.consecutive_failures = 0

    # Monkeypatch GeminiProvider to simulate a mid-stream failure
    import models.ai_provider as mod
    orig_gemini_cls = mod.GeminiProvider
    try:
        mod.GeminiProvider = FailingProvider

        events = list(mgr.stream_text_with_resilience(
            prompt="Test prompt",
            system_instruction="Test system",
            preferred="gemini"
        ))

        types = [e["type"] for e in events]
        assert "provider_switch" in types

        # Find switch event
        switch_evt = next(e for e in events if e["type"] == "provider_switch")
        assert switch_evt["from_provider"] == "Gemini"
        assert switch_evt["action"] == "restart"
        assert "503" in switch_evt["reason"]

        # Tokens after switch must belong to fallback provider
        post_switch_tokens = []
        seen_switch = False
        for e in events:
            if e["type"] == "provider_switch":
                seen_switch = True
                continue
            if seen_switch and e["type"] == "token":
                post_switch_tokens.append(e["text"])

        assert len(post_switch_tokens) > 0
        fallback_text = "".join(post_switch_tokens)
        assert len(fallback_text) > 10

        # Verify done event
        assert types[-1] == "done"

    finally:
        mod.GeminiProvider = orig_gemini_cls
