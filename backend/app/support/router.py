# app/support/router.py
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Body
from typing import List, Optional

# Assuming your services are now in app.support.models
from .models.mistral_ocr import MistralOCRService
from .models.video_recommend import YouTubeTopicSearcher
from .schema import OCRResponseModel, YouTubeSearchResponse, YouTubeSearchRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/support", tags=["Support Services"])

# Initialize services (or use FastAPI's dependency injection for more complex setups)
# For simplicity here, we instantiate them.
# In a larger app, you might manage these as singletons or via Depends.
ocr_service = MistralOCRService()
youtube_searcher = YouTubeTopicSearcher()

@router.post("/ocr/parse-document", response_model=OCRResponseModel)
async def parse_document_endpoint(
    file: UploadFile = File(..., description="Document file (PDF, PNG, JPG, etc.) to be processed by OCR."),
    model: Optional[str] = Form("mistral-ocr-latest", description="The Mistral OCR model to use."),
    include_images: Optional[bool] = Form(False, description="Whether to include base64 encoded images in the output (not typically used for markdown extraction).")
):
    """
    Upload a document (PDF, image) to extract text content using Mistral OCR.
    Returns a list of markdown strings, one for each page.
    """
    logger.info(f"Received file for OCR: {file.filename}, content type: {file.content_type}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        pages = ocr_service.parse_document_bytes(
            file_bytes=file_bytes,
            filename=file.filename,
            model=model,
            include_images=include_images
        )
        if "Error:" in pages[0] and len(pages) == 1: # Check if service returned an error message
             raise HTTPException(status_code=500, detail=pages[0])
        return OCRResponseModel(pages=pages, message="Document processed successfully.")
    except HTTPException as http_exc: # Re-raise HTTPExceptions
        raise http_exc
    except ValueError as ve: # Catch specific ValueErrors from service init
        logger.error(f"ValueError during OCR processing: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing file {file.filename} for OCR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    finally:
        await file.close()


@router.post("/youtube/search-by-topics", response_model=YouTubeSearchResponse)
async def search_youtube_by_topics_endpoint(
    request: YouTubeSearchRequest = Body(...)
):
    """
    Search YouTube for videos based on a list of topics.
    """
    logger.info(f"Received YouTube search request for topics: {request.topics}")
    if not request.topics:
        raise HTTPException(status_code=400, detail="No topics provided for search.")

    try:
        results = youtube_searcher.search_videos_for_topics(
            topics=request.topics,
            videos_per_topic=request.videos_per_topic
        )
        if not results and any(topic for topic in request.topics): # If topics were given but no results
            return YouTubeSearchResponse(results={}, message="No videos found for the given topics.")
        return YouTubeSearchResponse(results=results, message="YouTube search completed.")
    except ValueError as ve: # Catch specific ValueErrors from service init
        logger.error(f"ValueError during YouTube search: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during YouTube search for topics {request.topics}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search YouTube: {str(e)}")
