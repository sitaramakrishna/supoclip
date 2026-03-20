#!/bin/bash
# Reusable shutdown script for SupoClip GCP resources
# This script deletes compute resources and stops the database to save costs.

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "🛑 Starting shutdown process for project: $PROJECT_ID in $REGION..."

# 1. Delete Cloud Run Services
echo "🗑️  Deleting Cloud Run services..."
gcloud run services delete supoclip-api --region=$REGION --quiet
gcloud run services delete supoclip-worker --region=$REGION --quiet

# 2. Delete Redis Instance
echo "🗑️  Deleting Memorystore Redis instance..."
gcloud redis instances delete supoclip-redis --region=$REGION --quiet

# 3. Delete VPC Connector
echo "🗑️  Deleting VPC Access Connector..."
gcloud compute networks vpc-access connectors delete supoclip-connector --region=$REGION --quiet

# 4. Stop Cloud SQL Instance (Preserves data, stops billing for CPU/RAM)
echo "⏸️  Stopping Cloud SQL instance (supoclip-db)..."
gcloud sql instances patch supoclip-db --activation-policy=NEVER --quiet

echo -e "\n🔍 --- VERIFICATION STATUS ---"

# Verify Cloud Run
API_COUNT=$(gcloud run services list --region=$REGION --filter="metadata.name=supoclip-api" --format="value(name)" | wc -l)
WORKER_COUNT=$(gcloud run services list --region=$REGION --filter="metadata.name=supoclip-worker" --format="value(name)" | wc -l)
if [ "$API_COUNT" -eq "0" ] && [ "$WORKER_COUNT" -eq "0" ]; then
    echo "✅ Cloud Run Services: DELETED"
else
    echo "❌ Cloud Run Services: STILL ACTIVE"
fi

# Verify Redis
REDIS_STATUS=$(gcloud redis instances list --region=$REGION --filter="name:supoclip-redis" --format="value(state)")
if [ -z "$REDIS_STATUS" ]; then
    echo "✅ Redis Instance: DELETED"
else
    echo "❌ Redis Instance: STATUS is $REDIS_STATUS"
fi

# Verify VPC Connector
VPC_STATUS=$(gcloud compute networks vpc-access connectors list --region=$REGION --filter="name:supoclip-connector" --format="value(state)")
if [ -z "$VPC_STATUS" ]; then
    echo "✅ VPC Connector: DELETED"
else
    echo "❌ VPC Connector: STATUS is $VPC_STATUS"
fi

# Verify Cloud SQL
SQL_POLICY=$(gcloud sql instances describe supoclip-db --format="value(settings.activationPolicy)")
if [ "$SQL_POLICY" == "NEVER" ]; then
    echo "✅ Cloud SQL Instance: STOPPED"
else
    echo "❌ Cloud SQL Instance: POLICY is $SQL_POLICY"
fi

echo -e "\n✨ Shutdown process complete. You are now only being billed for minimal Cloud SQL storage."
