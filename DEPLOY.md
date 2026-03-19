# Deploying SupoClip — Two-Service Architecture

Vercel cannot run video processing (moviepy, FFmpeg, Whisper) — the deps alone
exceed 5 GB, well past the 500 MB Lambda limit.

**Solution: split into two services.**

| Service | Platform | What it does |
|---------|----------|--------------|
| API     | Vercel   | Accepts /tasks, returns task_id, stores state in DB |
| Worker  | Railway  | Does the actual video processing, fires BookFlashReel webhook |

QStash bridges them: API publishes a job → QStash POSTs to Worker → Worker
processes and fires the webhook.

---

## Prerequisites

```bash
npm i -g vercel
vercel login
```

---

## Part 1 — Deploy the API to Vercel

### 1. Clone this repo

```bash
git clone https://github.com/sitaramakrishna/supoclip.git /tmp/supoclip
cd /tmp/supoclip/backend
```

### 2. Deploy

```bash
vercel --prod
```

Vercel will use `requirements.txt` (slim — API deps only, ~50 MB).

### 3. Set env vars in Vercel dashboard

```
ANTHROPIC_API_KEY              sk-ant-...
ASSEMBLY_AI_API_KEY            ...
DATABASE_URL                   postgresql://...
REDIS_URL                      redis://...   (Upstash Redis — free tier)

# QStash (publishes jobs to the Railway worker)
QSTASH_TOKEN                   <from Upstash QStash dashboard>
QSTASH_WORKER_URL              https://<railway-worker>.up.railway.app/api/worker
```

### 4. Note the Vercel URL

```
https://<your-supoclip-api>.vercel.app
```

---

## Part 2 — Deploy the Worker to Railway

### 1. Create a Railway project

- Go to railway.app → New Project → Deploy from GitHub repo
- Select `sitaramakrishna/supoclip`
- Set **Root Directory** to `worker`  (Railway reads `worker/Dockerfile`)

### 2. Set env vars in Railway dashboard

```
DATABASE_URL                   postgresql://...   (same as Vercel)
REDIS_URL                      redis://...        (same Upstash instance)
ANTHROPIC_API_KEY              sk-ant-...
ASSEMBLY_AI_API_KEY            ...
BOOKFLASHREEL_WEBHOOK_URL      https://bookflashreel.com/api/webhooks/processor
BOOKFLASHREEL_WEBHOOK_SECRET   <must match PROCESSOR_WEBHOOK_SECRET in BookFlashReel>

# QStash signature verification
QSTASH_CURRENT_SIGNING_KEY     <from Upstash QStash → Signing Keys>
QSTASH_NEXT_SIGNING_KEY        <from Upstash QStash → Signing Keys>
```

### 3. Note the Railway public URL

Railway gives you a URL like `https://supoclip-worker-production.up.railway.app`.

Go back to the **Vercel** env vars and set:
```
QSTASH_WORKER_URL=https://supoclip-worker-production.up.railway.app/api/worker
```

---

## Part 3 — Update BookFlashReel env vars

In Vercel dashboard for the **BookFlashReel** project:

```
PROCESSOR_API_URL=https://<your-supoclip-api>.vercel.app
PROCESSOR_API_KEY=<BACKEND_AUTH_SECRET from SupoClip>
PROCESSOR_WEBHOOK_SECRET=<same value set above>
```

---

## How it all fits together

```
Customer uploads video
      │
      ▼
POST /api/upload/complete  (BookFlashReel / Vercel)
      │  calls callProcessor(signedVideoUrl)
      ▼
POST https://<supoclip-api>.vercel.app/tasks    ← returns immediately (~100ms)
      │  Creates DB row, publishes job to QStash
      │
      ▼  QStash delivers job
POST https://<railway-worker>/api/worker        ← runs up to Railway timeout
      │  Full video processing pipeline:
      │    1. Downloads video from signed Supabase URL
      │    2. Transcribes via AssemblyAI
      │    3. Scores virality via Claude
      │    4. Renders clips with FFmpeg/MoviePy
      │  QStash retries up to 3× on 5xx
      │
      ▼
POST https://bookflashreel.com/api/webhooks/processor
      │  HMAC-signed: { job_id, status, clips[], scene_markers[] }
      │
      ▼
Webhook handler updates uploads row → status: review
Team notified → Admin reviews at /admin/uploads
```
