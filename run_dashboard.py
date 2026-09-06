"""
Starts the browser dashboard: live video, live stats, and history/reports,
all served locally.

Run with: python run_dashboard.py
Then open: http://127.0.0.1:8001

Do NOT run this at the same time as `python app/main.py` - both try to
exclusively open the webcam, and only one process can hold it at a time.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import uvicorn

import config

if __name__ == "__main__":
    print(f"Starting dashboard at http://{config.WEB_HOST}:{config.WEB_PORT}")
    uvicorn.run("webapp.server:app", host=config.WEB_HOST, port=config.WEB_PORT, log_level="info")
