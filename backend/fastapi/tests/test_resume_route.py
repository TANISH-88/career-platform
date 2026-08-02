import os
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from app.config.constants import MAX_RESUME_BYTES
from app.main import app
from app.schemas.resume import ParsedResumeResponse
from app.services.resume_parser import GeminiUnavailableError, ResumeParser

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")


class StubParser:
    def __init__(
        self,
        *,
        text_result="resume text",
        skills_result=None,
        text_error=None,
        skills_error=None,
    ):
        self.text_result = text_result
        self.skills_result = skills_result or ParsedResumeResponse(
            computer_architecture=6.0,
            programming_skills=7.0,
            project_management=5.5,
            communication_skills=8.0,
            openness=6.5,
            conscientiousness=7.5,
            extraversion=4.5,
            agreeableness=6.0,
            emotional_range=5.0,
            conversation=6.5,
            openness_change=5.5,
            hedonism=4.0,
            self_enhancement=7.0,
            self_transcendence=6.0,
        )
        self.text_error = text_error
        self.skills_error = skills_error

    def extract_text(self, file_bytes, filename):
        if self.text_error is not None:
            raise self.text_error
        return self.text_result

    def extract_skills(self, text):
        if self.skills_error is not None:
            raise self.skills_error
        return self.skills_result


class FakeExtraction:
    model_fields = {
        "computer_architecture": None,
        "programming_skills": None,
        "project_management": None,
        "communication_skills": None,
        "openness": None,
        "conscientiousness": None,
        "extraversion": None,
        "agreeableness": None,
        "emotional_range": None,
        "conversation": None,
        "openness_change": None,
        "hedonism": None,
        "self_enhancement": None,
        "self_transcendence": None,
    }

    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _upload(client, filename, content_type, content):
    return client.post(
        "/parse-resume",
        files={"file": (filename, content, content_type)},
    )


def test_parse_resume_pdf_returns_200(client):
    client.app.state.resume_parser = StubParser()
    response = _upload(
        client,
        "resume.pdf",
        "application/pdf",
        b"%PDF-1.4 sample resume",
    )
    assert response.status_code == 200
    assert response.json() == StubParser().skills_result.model_dump()


def test_parse_resume_docx_returns_200(client):
    client.app.state.resume_parser = StubParser()
    response = _upload(
        client,
        "resume.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK\x03\x04 sample docx resume",
    )
    assert response.status_code == 200
    assert response.json() == StubParser().skills_result.model_dump()


def test_parse_resume_rejects_oversized_file(client):
    response = _upload(
        client,
        "resume.pdf",
        "application/pdf",
        b"x" * (MAX_RESUME_BYTES + 1),
    )
    assert response.status_code == 413
    assert response.json() == {
        "detail": "File too large. Maximum allowed size is 5 MB.",
    }


def test_parse_resume_rejects_unsupported_file_type(client):
    response = _upload(
        client,
        "resume.txt",
        "text/plain",
        b"plain text resume",
    )
    assert response.status_code == 415
    assert response.json() == {
        "detail": "Unsupported file type. Upload a PDF or DOCX file.",
    }


def test_parse_resume_rejects_empty_file(client):
    client.app.state.resume_parser = StubParser(text_error=ValueError("empty"))
    response = _upload(
        client,
        "resume.pdf",
        "application/pdf",
        b"%PDF-1.4 empty resume",
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": "Resume file is empty or unreadable.",
    }


def test_parse_resume_returns_502_when_gemini_is_unavailable(client):
    client.app.state.resume_parser = StubParser(
        skills_error=GeminiUnavailableError("Gemini API call failed: timeout"),
    )
    response = _upload(
        client,
        "resume.pdf",
        "application/pdf",
        b"%PDF-1.4 sample resume",
    )
    assert response.status_code == 502
    assert response.json() == {
        "detail": "Skill extraction service unavailable. Please try again later.",
    }


def test_extract_skills_clamps_gemini_scores():
    parser = ResumeParser()
    fake_response = SimpleNamespace(
        parsed=FakeExtraction(
            computer_architecture=0.0,
            programming_skills=12.5,
            project_management=5.0,
            communication_skills=10.8,
            openness=1.0,
            conscientiousness=9.9,
            extraversion=11.2,
            agreeableness=-2.0,
            emotional_range=7.5,
            conversation=0.3,
            openness_change=8.4,
            hedonism=15.0,
            self_enhancement=4.0,
            self_transcendence=10.1,
        )
    )
    parser._client = SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **kwargs: fake_response)
    )

    result = parser.extract_skills("resume text")

    assert result.computer_architecture == 1.0
    assert result.programming_skills == 10.0
    assert result.communication_skills == 10.0
    assert result.agreeableness == 1.0
    assert result.hedonism == 10.0
    assert result.self_transcendence == 10.0
    assert all(1.0 <= value <= 10.0 for value in result.model_dump().values())
