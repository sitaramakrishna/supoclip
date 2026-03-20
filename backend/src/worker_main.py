"""
Worker process entry point.
Run this to start background job workers.

Usage:
    arq src.workers.tasks.WorkerSettings
"""

import logging
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from arq import run_worker
from .workers.tasks import WorkerSettings
from .config import Config
from .observability import configure_logging

configure_logging()

logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        # Suppress logging for health checks
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", "8080"))
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Health check server starting on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    logger.info("Starting SupoClip worker...")
    logger.info(f"Redis: {Config().redis_host}:{Config().redis_port}")
    
    # Start health check server in a background thread for Cloud Run
    if os.environ.get("PORT"):
        health_thread = threading.Thread(target=run_health_check_server, daemon=True)
        health_thread.start()
    
    run_worker(WorkerSettings)
