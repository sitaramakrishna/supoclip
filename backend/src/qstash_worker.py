"""
qstash_worker.py — FastAPI endpoint called by QStash for async video processing.

QStash POSTs the full task payload here. This function runs inside a Vercel
Function with maxDuration: 300 (Pro) or 800 (Enterprise), bypassing the 60s
limit on the /tasks endpoint.

INSTALLATION:
  Copy to supoclip/backend/src/qstash_worker.py
  Ensure vercel.json routes /api/worker to this file.

ENV VARS:
  QSTASH_CURRENT_SIGNING_KEY  — from Upstash console → QStash → Signing Keys
  QSTASH_NEXT_SIGNING_KEY     — from Upstash console → QStash → Signing Keys
"""

import json
import logging
import os

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="SupoClip QStash Worker")

QSTASH_CURRENT_KEY = os.getenv("QSTASH_CURRENT_SIGNING_KEY", "")
QSTASH_NEXT_KEY    = os.getenv("QSTASH_NEXT_SIGNING_KEY", "")


def _verify_qstash_signature(body: bytes, signature: str) -> bool:
    """
    Basic presence check for the QStash upstash-signature header.
    For full JWT verification, install qstash-py and use its Receiver class:

      from qstash import Receiver
      Receiver(
          current_signing_key=QSTASH_CURRENT_KEY,
          next_signing_key=QSTASH_NEXT_KEY,
      ).verify(signature=signature, body=body.decode(), url=<worker_url>)
    """
    if not QSTASH_CURRENT_KEY and not QSTASH_NEXT_KEY:
        return True  # Dev mode: skip verification
    return bool(signature)  # Require header to be present


@app.post("/api/worker")
async def worker(
    request: Request,
    upstash_signature: str = Header(default="", alias="upstash-signature"),
):
    body = await request.body()

    if not _verify_qstash_signature(body, upstash_signature):
        raise HTTPException(status_code=401, detail="Missing QStash signature")

    try:
        data = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    task_id = data.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="Missing task_id")

    url            = data.get("url", "")
    source_type    = data.get("source_type", "")
    font_family    = data.get("font_family", "TikTokSans-Regular")
    font_size      = int(data.get("font_size", 24))
    font_color     = data.get("font_color", "#FFFFFF")
    caption_tmpl   = data.get("caption_template", "default")
    proc_mode      = data.get("processing_mode", "fast")
    output_format  = data.get("output_format", "vertical")
    add_subtitles  = bool(data.get("add_subtitles", True))

    if not url or not source_type:
        raise HTTPException(status_code=400, detail="Missing url or source_type")

    # Import here to avoid circular imports at module load time
    from .database import AsyncSessionLocal
    from .services.task_service import TaskService

    logger.info("QStash worker processing task %s", task_id)

    async with AsyncSessionLocal() as db:
        task_service = TaskService(db)
        await task_service.process_task(
            task_id=task_id,
            url=url,
            source_type=source_type,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color,
            caption_template=caption_tmpl,
            processing_mode=proc_mode,
            output_format=output_format,
            add_subtitles=add_subtitles,
        )

    logger.info("QStash worker finished task %s", task_id)
    return JSONResponse({"ok": True, "task_id": task_id})
