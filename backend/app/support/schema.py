# app/support/schemas.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any

# --- OCR Schemas ---
class OCRResponseModel(BaseModel):
    pages: List[str]
    message: Optional[str] = None

# --- YouTube Search Schemas ---
class YouTubeVideo(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None
    published_at: Optional[str] = None # Date string e.g., "2023-10-26"
    video_id: str
    url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    views: Optional[str] = None # Kept as str as API might return 'N/A' or formatted numbers
    likes: Optional[str] = None # Kept as str
    duration: Optional[str] = None # ISO 8601 duration format e.g., "PT15M33S"

class YouTubeSearchRequest(BaseModel):
    topics: List[str]
    videos_per_topic: Optional[int] = 3

class YouTubeSearchResponse(BaseModel):
    results: Dict[str, List[YouTubeVideo]]
    message: Optional[str] = None

