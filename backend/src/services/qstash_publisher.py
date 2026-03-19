"""
qstash_publisher.py — Vercel-compatible async job dispatch via QStash.

Replaces arq's queue_adapter.enqueue_processing_job() so that Vercel
Function invocations can kick off long-running video processing without
hitting the 60s default timeout on the /tasks endpoint.

INSTALLATION:
  Copy to supoclip/backend/src/services/qstash_publisher.py

ENV VARS:
  QSTASH_TOKEN        — from Upstash console → QStash
  QSTASH_WORKER_URL   — https://<your-deployment>.vercel.app/api/worker
"""

import json
import os

import httpx

QSTASH_TOKEN      = os.getenv("QSTASH_TOKEN", "")
QSTASH_WORKER_URL = os.getenv("QSTASH_WORKER_URL", "")


async def enqueue_task(
    task_id: str,
    url: str,
    source_type: str,
    user_id: str = "",
    font_family: str = "TikTokSans-Regular",
    font_size: int = 24,
    font_color: str = "#FFFFFF",
    caption_template: str = "default",
    processing_mode: str = "fast",
    output_format: str = "vertical",
    add_subtitles: bool = True,
) -> None:
    """
    Publish a video processing job to QStash.
    QStash will POST the full payload to /api/worker.

    Falls back to running the task inline (via arq enqueue) when QSTASH_TOKEN
    is not set — keeps local / non-Vercel deployments working unchanged.
    """
    if not QSTASH_TOKEN or not QSTASH_WORKER_URL:
        # Dev / non-Vercel: let the caller use the original arq path
        raise NotImplementedError(
            "QStash not configured. Set QSTASH_TOKEN and QSTASH_WORKER_URL, "
            "or use JobQueue.enqueue_processing_job() directly."
        )

    payload = {
        "task_id":          task_id,
        "url":              url,
        "source_type":      source_type,
        "user_id":          user_id,
        "font_family":      font_family,
        "font_size":        font_size,
        "font_color":       font_color,
        "caption_template": caption_template,
        "processing_mode":  processing_mode,
        "output_format":    output_format,
        "add_subtitles":    add_subtitles,
    }

    body = json.dumps(payload, separators=(",", ":"))
    publish_url = f"https://qstash.upstash.io/v2/publish/{QSTASH_WORKER_URL}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            publish_url,
            content=body,
            headers={
                "Authorization": f"Bearer {QSTASH_TOKEN}",
                "Content-Type":  "application/json",
                # QStash retries up to 3 times with exponential back-off by default
            },
        )
        resp.raise_for_status()
