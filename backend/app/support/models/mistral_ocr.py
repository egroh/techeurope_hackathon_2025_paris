# app/support/models/mistral_ocr.py
import base64
from pathlib import Path
from typing import List
import logging
import os # Keep os for getenv if you decide to use it later, but not for hardcoded

# Use the original Mistral class if that's what your script used and worked
from mistralai import Mistral # Reverted to original Mistral class
# from mistralai.models.ocr import OCRResponse # This might not be needed if Mistral().ocr.process returns a dict-like object

logger = logging.getLogger(__name__)

# --- WARNING: HARDCODED API KEY - NOT FOR PRODUCTION ---
MISTRAL_API_KEY_HARDCODED = "IhmKJGkJv61EPFwWIuY9wCgnbaFV6Fm1" # Ensure this is replaced for actual use
# --- END WARNING ---

class MistralOCRService:
    def __init__(self):
        self.api_key = MISTRAL_API_KEY_HARDCODED
        # Initialize the client using the original Mistral class
        try:
            # Your original script used Mistral(api_key=api_key) directly
            self.client = Mistral(api_key=self.api_key)
            logger.info("MistralOCRService initialized with Mistral class.")
        except Exception as e:
            logger.error(f"Failed to initialize Mistral (original class) client: {e}", exc_info=True)
            self.client = None # Ensure client is None if initialization fails

    def _encode_base64(self, file_bytes: bytes, mime_type: str) -> str:
        """Encode bytes as base-64 data-URI."""
        b64 = base64.b64encode(file_bytes).decode()
        return f"data:{mime_type};base64,{b64}"

    def parse_document_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        model: str = "mistral-ocr-latest", # Your original script used this default
        include_images: bool = False,
    ) -> List[str]:
        """
        Extract every page of the uploaded file bytes using Mistral OCR,
        preserving the original interaction style.
        """
        if not self.client:
            logger.error("Mistral client not initialized. Cannot parse document.")
            # Return a list with an error message, as the function expects List[str]
            return ["Error: OCR Client not initialized. Check API Key or initialization logs."]

        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            mime_type = "application/pdf"
        elif suffix in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
            mime_type = f"image/{suffix.lstrip('.')}"
        else:
            mime_type = "application/octet-stream"
            logger.warning(f"Unknown file type for {filename}, using generic mime type: {mime_type}")

        logger.info(f"Encoding {filename} ({mime_type}) -> base-64")
        data_uri = self._encode_base64(file_bytes, mime_type)

        logger.info(f"Sending to Mistral OCR ({model}) for file: {filename} using original client.ocr.process")
        try:
            # Using the client.ocr.process method as in your original script
            # The original script had:
            # ocr = client.ocr.process(
            #     model=model,
            #     document={"type": "document_url", "document_url": data_uri},
            #     include_image_base64=include_images,
            # )
            # pages = [page.markdown for page in ocr.pages]

            # Assuming client.ocr.process returns an object that has a .pages attribute,
            # and each item in .pages has a .markdown attribute.
            # If the structure is different (e.g., a direct list of dicts), this needs adjustment.
            ocr_response_object = self.client.ocr.process(
                model=model,
                document={"type": "document_url", "document_url": data_uri},
                include_image_base64=include_images,
            )

            # Check if the response object and .pages attribute exist
            if hasattr(ocr_response_object, 'pages') and ocr_response_object.pages is not None:
                pages = []
                for page_obj in ocr_response_object.pages:
                    if hasattr(page_obj, 'markdown'):
                        pages.append(page_obj.markdown)
                    else:
                        logger.warning(f"Page object for {filename} lacks 'markdown' attribute: {page_obj}")
                        pages.append("[Warning: Page content format unexpected - no markdown field]")
                if not pages and hasattr(ocr_response_object, 'pages') and len(ocr_response_object.pages) > 0:
                    logger.warning(f"Processed pages for {filename} but extracted no markdown content.")
                    # This case might indicate all page objects lacked 'markdown'
            elif isinstance(ocr_response_object, dict) and 'pages' in ocr_response_object:
                # Handle if it's a dictionary (less likely for Pydantic models from SDK but good to check)
                raw_pages = ocr_response_object.get('pages', [])
                pages = [page.get('markdown', "[Warning: Page content format unexpected - no markdown field in dict]") for page in raw_pages if isinstance(page, dict)]
            else:
                logger.error(f"Unexpected OCR response structure for {filename}: {type(ocr_response_object)}")
                return [f"Error: Unexpected OCR response structure - {type(ocr_response_object)}"]


            logger.info(f"Received {len(pages)} pages from Mistral OCR for {filename}")
            if not pages: # If pages list is empty after processing
                 return ["[Info: OCR processed but no pages with markdown content were extracted.]"]
            return pages
        except Exception as e:
            logger.error(f"Mistral OCR API error for {filename}: {e}", exc_info=True)
            return [f"Error during OCR processing: {str(e)}"]

