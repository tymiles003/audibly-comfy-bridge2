from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import uuid

COMFY_BASE_URL = os.getenv("COMFY_BASE_URL", "http://localhost:8188")

app = FastAPI(title="Audibly-Comfy Bridge")

class LipSyncRequest(BaseModel):
    audio_url: str
    video_url: str
    prompt: str | None = None

class LipSyncResponse(BaseModel):
    status: str
    output_video_url: str | None = None
    job_id: str | None = None
    error: str | None = None


async def trigger_comfy_workflow(audio_url: str, video_url: str, prompt: str | None) -> str:
    payload = {
        "workflow": "audibly_lipsync.json",
        "inputs": {
            "audio_url": audio_url,
            "video_url": video_url,
            "prompt": prompt or ""
        }
    }

    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(f"{COMFY_BASE_URL}/api/audibly/run", json=payload)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"ComfyUI error: {r.text}")

        data = r.json()
        output_url = data.get("output_video_url")
        if not output_url:
            raise HTTPException(status_code=500, detail="No output_video_url from ComfyUI")

        return output_url


@app.post("/audibly/comfy/lipsync", response_model=LipSyncResponse)
async def lipsync_endpoint(req: LipSyncRequest):
    job_id = str(uuid.uuid4())

    try:
        output_url = await trigger_comfy_workflow(
            audio_url=req.audio_url,
            video_url=req.video_url,
            prompt=req.prompt,
        )
        return LipSyncResponse(
            status="ok",
            output_video_url=output_url,
            job_id=job_id,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        return LipSyncResponse(
            status="error",
            error=str(e),
            job_id=job_id,
        )
