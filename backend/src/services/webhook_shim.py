"""
webhook_shim.py — Drop this into SupoClip's src/services/ directory.

SupoClip fires per-clip SSE events and a final "completed" event internally.
BookFlashReel expects a single HMAC-signed POST webhook when all clips are ready.

This shim hooks into TaskService.process_task() completion to fire the webhook.

INSTALLATION:
  1. Copy this file to supoclip/backend/src/services/webhook_shim.py
  2. In src/services/task_service.py, import and call fire_webhook() after
     clips are saved (search for "status = 'completed'" update).

ENV VARS REQUIRED (add to Fly secrets):
  BOOKFLASHREEL_WEBHOOK_URL     https://bookflashreel.com/api/webhooks/processor
  BOOKFLASHREEL_WEBHOOK_SECRET  (matches PROCESSOR_WEBHOOK_SECRET in Vercel)
"""

import hashlib
import hmac
import json
import os
import httpx

WEBHOOK_URL    = os.getenv("BOOKFLASHREEL_WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("BOOKFLASHREEL_WEBHOOK_SECRET", "")


def _sign(body: str) -> str:
    """HMAC-SHA256 signature matching BookFlashReel's verifyHmac()."""
    digest = hmac.new(
        WEBHOOK_SECRET.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


async def fire_webhook(job_id: str, clips: list, scene_markers: list) -> None:
    """
    Call after all clips are saved on a successful task.
    Maps SupoClip clip shape → BookFlashReel ProcessorWebhookPayload.
    """
    if not WEBHOOK_URL or not WEBHOOK_SECRET:
        return  # Webhook not configured; skip silently

    payload = {
        "job_id": job_id,
        "status": "completed",
        "clips": [
            {
                "url":             clip.get("serving_url", clip.get("url", "")),
                "virality_score":  clip.get("virality_score", 0),
                "duration":        clip.get("duration", 0),
                "title":           clip.get("text", "")[:80],  # first 80 chars of transcript
            }
            for clip in clips
        ],
        "scene_markers": [
            {
                "timestamp": str(m.get("start_time", 0)),
                "label":     m.get("hook_type", ""),
            }
            for m in scene_markers
        ],
    }

    body = json.dumps(payload, separators=(",", ":"))
    sig  = _sign(body)

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type":          "application/json",
                    "X-Processor-Signature": sig,
                },
            )
        except Exception as exc:
            # Log but don't crash the worker
            print(f"[webhook_shim] Failed to fire webhook: {exc}")


async def fire_webhook_error(job_id: str, error_message: str) -> None:
    """Call when a task fails so BookFlashReel can update the upload row."""
    if not WEBHOOK_URL or not WEBHOOK_SECRET:
        return

    payload = {
        "job_id":        job_id,
        "status":        "failed",
        "error_message": error_message,
    }

    body = json.dumps(payload, separators=(",", ":"))
    sig  = _sign(body)

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                WEBHOOK_URL,
                content=body,
                headers={
                    "Content-Type":          "application/json",
                    "X-Processor-Signature": sig,
                },
            )
        except Exception as exc:
            print(f"[webhook_shim] Failed to fire error webhook: {exc}")
