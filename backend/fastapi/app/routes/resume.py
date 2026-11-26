from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.resume import ParsedResumeResponse
from app.services.rate_limiter import rate_limit_resume
from app.services.resume_parser import ResumeValidationError, extract_and_score_resume

resume_router = APIRouter()


@resume_router.post(
    "/parse-resume",
    response_model=ParsedResumeResponse,
    dependencies=[Depends(rate_limit_resume)],
)
async def parse_resume(request: Request, file: UploadFile = File(...)):
    file_bytes = await file.read()
    parser = request.app.state.resume_parser

    try:
        parsed, _ = extract_and_score_resume(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            parser=parser,
        )
    except ResumeValidationError as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return parsed
