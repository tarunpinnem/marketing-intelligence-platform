from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.search import Campaign
from app.services.campaign import create_campaign, get_all_campaigns

router = APIRouter()

@router.get("/campaigns")
async def list_campaigns():
    try:
        campaigns = await get_all_campaigns()
        return campaigns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaigns")
async def add_campaign(campaign: Campaign):
    try:
        result = await create_campaign(campaign)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # Process file contents and save to database
        return {"filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))