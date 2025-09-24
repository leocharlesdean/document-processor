import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

class TestAPI:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Document Intelligence Platform" in response.text
    
    def test_upload_invalid_file(self):
        # Test with non-PDF file
        response = client.post(
            "/api/v1/documents",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]
    
    def test_list_documents_empty(self):
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_dashboard_analytics(self):
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "document_types" in data
        assert "processing_status" in data