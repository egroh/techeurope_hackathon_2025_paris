from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from .model import MathstralModel

router = APIRouter()

# Create a Pydantic model for the request
class MathstralRequest(BaseModel):
    prompt: str

# Initialize the model (this might take a while when the server starts)
mathstral_model = MathstralModel()

@router.post("/generate/")
async def generate_response(request: MathstralRequest):
    try:
        # Call the generate method of MathstralModel
        response = mathstral_model.generate(request.prompt)
        return {"generated_text": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))