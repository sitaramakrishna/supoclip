# Deploying SupoClip to Google Cloud Run

This guide will help you deploy the SupoClip backend (API and Worker) to Google Cloud Run.

## Prerequisites

1.  **Google Cloud Project**: You need an active Google Cloud project.
2.  **gcloud CLI**: Install and initialize the [gcloud CLI](https://cloud.google.com/sdk/docs/install).
3.  **Services Enabled**: Run the following to enable required APIs:
    ```bash
    gcloud services enable run.googleapis.com \
                           cloudbuild.googleapis.com \
                           artifactregistry.googleapis.com \
                           sqladmin.googleapis.com \
                           redis.googleapis.com
    ```

## Infrastructure Setup

### 1. Database (PostgreSQL)
Create a Cloud SQL instance:
```bash
gcloud sql instances create supoclip-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1
```
Set a password for the `postgres` user and create the `supoclip` database.

### 2. Redis (Memorystore)
Create a Redis instance:
```bash
gcloud redis instances create supoclip-redis \
    --size=1 \
    --region=us-central1 \
    --redis-version=redis_6_x
```
Note the IP address of the Redis instance.

## Deployment

1.  **Configure Environment Variables**:
    You can either set these in your shell before running the deploy script or modify the script directly.
    ```bash
    export DATABASE_URL="postgresql+asyncpg://user:pass@IP_OR_PROXY/supoclip"
    export REDIS_HOST="REDIS_IP"
    export REDIS_PORT=6379
    export OPENAI_API_KEY="your-key"
    # ... other keys
    ```

2.  **Run the Deployment Script**:
    ```bash
    chmod +x bin/deploy_gcp.sh
    ./bin/deploy_gcp.sh
    ```

## Architecture Details

-   **API Service**: Runs the FastAPI application. Scales to zero when not in use.
-   **Worker Service**: Runs the `arq` background worker. Configured with `--min-instances 1` to ensure it's always ready to process video jobs (adjust as needed).
-   **VPC Connector**: If your database/Redis is in a private VPC, you'll need to add a VPC connector to both services.

## Relaunching the Application

If you have shut down the instances to save costs, follow these steps to go live again:

1.  **Restart the Database**:
    ```bash
    gcloud sql instances patch supoclip-db --activation-policy=ALWAYS
    ```

2.  **Recreate Infrastructure**:
    The Redis and VPC Connector need to be recreated (refer to the Infrastructure Setup section above).

3.  **Redeploy Services**:
    Run the deployment script to rebuild and relaunch the API and Worker:
    ```bash
    ./bin/deploy_gcp.sh
    ```
