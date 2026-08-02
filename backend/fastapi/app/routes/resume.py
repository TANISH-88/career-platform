from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config.constants import MAX_RESUME_BYTES
from app.schemas.resume import ParsedResumeResponse
from app.services.resume_parser import GeminiUnavailableError, UnsupportedMediaTypeError

resume_router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@resume_router.post("/parse-resume", response_model=ParsedResumeResponse)
async def parse_resume(request: Request, file: UploadFile = File(...)):
    # 1. Read all bytes upfront
    file_bytes = await file.read()

    # 2. Size guard — reject before any extraction or Gemini call
    if len(file_bytes) > MAX_RESUME_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "File too large. Maximum allowed size is 5 MB."},
        )

    # 3. Extension + MIME type guard
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIMES:
        return JSONResponse(
            status_code=415,
            content={"detail": "Unsupported file type. Upload a PDF or DOCX file."},
        )

    parser = request.app.state.resume_parser

    # 4. Text extraction
    try:
        text = parser.extract_text(file_bytes, filename)
    except UnsupportedMediaTypeError:
        return JSONResponse(
            status_code=415,
            content={"detail": "Unsupported file type. Upload a PDF or DOCX file."},
        )
    except ValueError:
        return JSONResponse(
            status_code=422,
            content={"detail": "Resume file is empty or unreadable."},
        )

    # 5. Skill extraction via Gemini
    try:
        result = parser.extract_skills(text)
    except GeminiUnavailableError:
        return JSONResponse(
            status_code=502,
            content={"detail": "Skill extraction service unavailable. Please try again later."},
        )

    return result
