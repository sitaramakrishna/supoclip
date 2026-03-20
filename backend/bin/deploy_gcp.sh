#!/bin/bash
# Deployment script for SupoClip Backend on Google Cloud Run
# Optimizations: CPU Boost, Concurrency Tuning, and Cloud SQL Sockets
# Security: Secrets are picked up from the environment.

# Ensure required environment variables are set
REQUIRED_VARS=(
  "ANTHROPIC_API_KEY"
  "OPENAI_API_KEY"
  "GOOGLE_API_KEY"
  "ASSEMBLY_AI_API_KEY"
  "PEXELS_API_KEY"
  "APIFY_API_TOKEN"
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Error: Environment variable $var is not set."
    exit 1
  fi
done

# Set your project ID if not already set
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "🚀 Deploying SupoClip Backend to $PROJECT_ID in $REGION..."

# --- INFRASTRUCTURE INFO ---
# NOTE: Update these if you recreate your infrastructure
REDIS_HOST="${REDIS_HOST:-10.31.225.243}"
REDIS_PORT=6379
DB_CONN="${DB_CONN:-supoclip-490723:us-central1:supoclip-db}"
DATABASE_URL="postgresql+asyncpg://postgres:SupoClipPass123!@/supoclip?host=/cloudsql/$DB_CONN"
VPC_CONNECTOR="supoclip-connector"

# 1. Build and push image using Cloud Build
echo "📦 Starting Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# 2. Deploy the API Service
echo "🌐 Deploying API service..."
gcloud run deploy supoclip-api \
  --image gcr.io/$PROJECT_ID/supoclip-backend:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --cpu-boost \
  --add-cloudsql-instances $DB_CONN \
  --vpc-connector $VPC_CONNECTOR \
  --set-env-vars "DATABASE_URL=$DATABASE_URL,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,OPENAI_API_KEY=$OPENAI_API_KEY,GOOGLE_API_KEY=$GOOGLE_API_KEY,ASSEMBLY_AI_API_KEY=$ASSEMBLY_AI_API_KEY,PEXELS_API_KEY=$PEXELS_API_KEY,APIFY_API_TOKEN=$APIFY_API_TOKEN"

# 3. Deploy the Worker Service
echo "👷 Deploying Worker service..."
gcloud run deploy supoclip-worker \
  --image gcr.io/$PROJECT_ID/supoclip-backend:latest \
  --command "/app/.venv/bin/python" \
  --args="-m,src.worker_main" \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --timeout 3600 \
  --concurrency 1 \
  --min-instances 0 \
  --cpu-boost \
  --add-cloudsql-instances $DB_CONN \
  --vpc-connector $VPC_CONNECTOR \
  --set-env-vars "DATABASE_URL=$DATABASE_URL,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,OPENAI_API_KEY=$OPENAI_API_KEY,GOOGLE_API_KEY=$GOOGLE_API_KEY,ASSEMBLY_AI_API_KEY=$ASSEMBLY_AI_API_KEY,PEXELS_API_KEY=$PEXELS_API_KEY,APIFY_API_TOKEN=$APIFY_API_TOKEN"

echo "✅ Deployment complete!"
echo "API URL: $(gcloud run services describe supoclip-api --region $REGION --format='value(status.url)')"
