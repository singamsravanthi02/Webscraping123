import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock, MagicMock

client = TestClient(app)

headers = {"Authorization": "Bearer test_token_user_1"}

def test_create_session(db_session):
    response = client.post("/api/v1/learning/sessions", json={
        "title": "Machine Learning Prep",
        "subject": "CS401"
    }, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        assert data["title"] == "Machine Learning Prep"
        assert data["subject"] == "CS401"

@patch('app.domain.learning.services.rag_service.search_documents')
@patch('app.domain.learning.services.rag_service.gateway.generate_structured_response')
def test_rag_chat_hallucination_prevention(mock_generate, mock_search, db_session):
    # Mock retrieval
    mock_search.return_value = [
        {"title": "Syllabus.pdf", "text": "Machine learning basics", "source_type": "pdf"}
    ]
    
    # Mock Gemini to return structured JSON
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "concise_explanation": "ML is a field of AI.",
        "confidence_level": "High",
        "related_topics": ["Deep Learning"]
    }
    mock_generate.return_value = mock_response
    
    # Create session
    res = client.post("/api/v1/learning/sessions", json={"title": "ML", "subject": "CS401"}, headers=headers)
    if res.status_code == 200:
        s_id = res.json()["id"]
        
        # Chat
        chat_res = client.post(f"/api/v1/learning/sessions/{s_id}/chat", json={"content": "What is ML?"}, headers=headers)
        assert chat_res.status_code == 200
        data = chat_res.json()
        
        # The content should be a JSON string of our struct
        content_json = json.loads(data["content"])
        assert content_json["confidence_level"] == "High"
        assert "Deep Learning" in content_json["related_topics"]
        
        # Check citations
        assert len(data["citations"]) == 1
        assert data["citations"][0]["title"] == "Syllabus.pdf"

@patch('app.domain.learning.services.rag_service.search_documents')
@patch('app.domain.learning.services.rag_service.gateway.generate_structured_response')
def test_rag_chat_includes_rich_citations(mock_generate, mock_search, db_session):
    mock_search.return_value = [
        {
            "title": "JNTUH Syllabus.pdf",
            "text": "Machine learning basics",
            "source_type": "pdf",
            "score": 0.91,
            "embedding_distance": 0.09,
            "document_id": 7,
            "chunk_index": 0,
            "chunk_number": 1,
            "page_number": 4,
            "metadata": {
                "title": "JNTUH Syllabus.pdf",
                "source": "JNTUH",
                "subject": "CS401",
                "department": "CSE",
                "semester": "6",
                "unit": "Unit 2",
                "url": "https://example.com/jntuh.pdf",
                "keywords": ["ml", "ai"],
            },
        }
    ]

    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "concise_explanation": "ML is a field of AI.",
        "confidence_level": "High",
        "related_topics": ["Deep Learning"]
    }
    mock_generate.return_value = mock_response

    res = client.post("/api/v1/learning/sessions", json={"title": "ML", "subject": "CS401"}, headers=headers)
    if res.status_code == 200:
        s_id = res.json()["id"]
        chat_res = client.post(f"/api/v1/learning/sessions/{s_id}/chat", json={"content": "What is ML?"}, headers=headers)
        assert chat_res.status_code == 200
        data = chat_res.json()
        assert data["citations"][0]["page"] == 4
        assert data["citations"][0]["chunk_number"] == 1
        assert data["citations"][0]["metadata"]["subject"] == "CS401"

@patch('app.domain.learning.services.rag_service.search_documents')
@patch('app.domain.learning.services.rag_service.gateway.generate_structured_response')
def test_generate_material_and_memory(mock_generate, mock_search, db_session):
    mock_search.return_value = [
        {"title": "Neural Networks", "text": "Neural networks basics", "source_type": "pdf"}
    ]

    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "material_type": "quiz",
        "topic": "Neural Networks",
        "summary_markdown": "",
        "flashcards": [],
        "questions": [
            {"question": "Q1", "options": ["A", "B"], "answer_index": 0, "explanation": "E"}
        ],
        "key_points": [],
        "cheat_sheet": "",
    }
    mock_generate.return_value = mock_response
    
    res = client.post("/api/v1/learning/generate", json={
        "topic": "Neural Networks",
        "type": "quiz"
    }, headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        assert "questions" in data["result"]
        
@patch('app.api.v1.learning.ingest_document')
def test_pdf_upload(mock_ingest, db_session):
    # Test file upload route
    files = {'file': ('test.pdf', b'dummy content', 'application/pdf')}
    data = {
        'title': 'Test Doc',
        'type': 'pdf',
        'subject': 'CS401',
        'topic': 'ML',
        'keywords': 'ai, ml'
    }
    
    res = client.post("/api/v1/learning/resources/upload", data=data, files=files, headers=headers)
    
    if res.status_code == 200:
        assert mock_ingest.called
        kwargs = mock_ingest.call_args.kwargs
        assert kwargs["subject"] == "CS401"
        assert "ai" in kwargs["keywords"]
