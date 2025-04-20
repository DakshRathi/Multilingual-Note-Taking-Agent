# src/api/endpoints/transcription.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks

from src.schemas.transcription import TranscriptionResponse
from src.services.transcription_service import process_audio_file
from src.core.config import logger

router = APIRouter()

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe Audio File",
    description="Upload an audio file (MP3, WAV, MP4, OGG, WEBM etc.) to transcribe it using AssemblyAI. "
                "Returns the transcript text, detected language, and speaker-separated utterances.",
    tags=["Transcription"]
)
async def transcribe_audio_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The audio file to transcribe.")
):
    """
    Endpoint to receive an audio file and initiate transcription.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_content_types = [
        "audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg", "audio/mov",   
        "audio/flac",  "audio/mp3", "audio/webm", "video/mp4", "video/webm", "video/ogg"
    ]
    if file.content_type not in allowed_content_types:
        logger.warning(f"Received potentially unsupported file type: {file.content_type}")

    logger.info(f"Received file for transcription: {file.filename}, type: {file.content_type}")

    try:
        result = await process_audio_file(file, background_tasks)
        if result.status == 'error':
            # Use 422 if it's a processing error based on input, 500 for internal issues
            raise HTTPException(status_code=422, detail=f"Transcription failed: {result.error}")
        return result
    except HTTPException as http_exc:
        # Re-raise known HTTP exceptions
        raise http_exc
    except Exception as e:
        logger.exception(f"Unhandled exception in /transcribe endpoint for file {file.filename}") # Log stack trace
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

