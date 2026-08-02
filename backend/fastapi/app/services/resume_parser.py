"""
ResumeParser — Phase 2 service for resume text extraction and Gemini-based skill scoring.
"""

import io
import os

import pdfplumber
import docx
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.config.constants import GEMINI_MODEL
from app.schemas.resume import ParsedResumeResponse, ResumeExtraction


class UnsupportedMediaTypeError(Exception):
    """Raised when a file format other than PDF or DOCX is supplied."""


class GeminiUnavailableError(Exception):
    """Raised when the Gemini API call fails or times out."""


class ResumeParser:
    def __init__(self) -> None:
        load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        # Key value intentionally never logged or included in any message
        self._client = genai.Client(api_key=api_key)

    # ------------------------------------------------------------------
    # Private text-extraction helpers
    # ------------------------------------------------------------------

    def _extract_pdf(self, file_bytes: bytes) -> str:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)

    def _extract_docx(self, file_bytes: bytes) -> str:
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(para.text for para in document.paragraphs)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Dispatch to the appropriate extractor by file extension.

        Raises:
            UnsupportedMediaTypeError: for any extension other than .pdf / .docx
            ValueError: if the extracted text is empty or whitespace-only
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext == "pdf":
            text = self._extract_pdf(file_bytes)
        elif ext == "docx":
            text = self._extract_docx(file_bytes)
        else:
            raise UnsupportedMediaTypeError(
                f"Unsupported file type: .{ext}. Only PDF and DOCX are accepted."
            )
        if not text or not text.strip():
            raise ValueError("Resume file is empty or unreadable")
        return text

    def extract_skills(self, text: str) -> ParsedResumeResponse:
        """
        Call Gemini with a structured response_schema and return 14 clamped scores.

        Raises:
            GeminiUnavailableError: if the Gemini SDK raises any exception
        """
        prompt = (
            "You are a career assessment assistant. "
            "Analyse the following resume text and score the candidate on each skill "
            "from 1.0 (lowest) to 10.0 (highest). "
            "Return only the structured scores.\n\nResume:\n" + text
        )

        try:
            # NOTE: Free-tier Gemini requests may be used by Google for model training
            # and improvement. Do not send confidential, proprietary, or personally
            # identifiable information through this path without first reviewing
            # Google's data usage policies and upgrading to a paid tier if required.
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResumeExtraction,
                ),
            )
        except Exception as exc:
            raise GeminiUnavailableError(
                f"Gemini API call failed: {exc}"
            ) from exc

        extraction: ResumeExtraction = response.parsed

        # Server-side clamp — authoritative enforcement regardless of schema validation.
        # Iterates model_fields so no feature name string is duplicated here.
        clamped = {
            field: max(1.0, min(10.0, getattr(extraction, field)))
            for field in extraction.model_fields
        }
        return ParsedResumeResponse(**clamped)
