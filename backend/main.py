from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from reporting import ReportManager
from orchestrator import Orchestrator
from browser_service import BrowserService

# Fix for Playwright on Windows with asyncio (Python 3.8+)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="NL Automation Tool")

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount reports directory
reports_dir = os.path.join(os.path.dirname(__file__), "reports")
if not os.path.exists(reports_dir):
    os.makedirs(reports_dir)
app.mount("/reports_files", StaticFiles(directory=reports_dir), name="reports_files")

@app.get("/")
def read_root():
    return {"status": "Backend is running"}

@app.get("/reports")
def list_reports():
    rm = ReportManager()
    return rm.get_all_reports()

@app.get("/reports/{session_id}")
def get_report(session_id: str):
    report_path = os.path.join(reports_dir, session_id, "report.json")
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            return json.load(f)
    return {"error": "Report not found"}

# Global Singleton Browser Service
# This ensures we don't spawn 50 chrome windows if the user refreshes the page 50 times.
global_browser_service = BrowserService()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected via WebSocket")
    
    # Inject Global Browser Service
    orchestrator = Orchestrator(websocket, reports_dir, global_browser_service)
    
    try:
        while True:
            # Main WebSocket Loop: Just receives commands and routes them
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg)
                
                # Setup Goal
                if "goal" in msg:
                    goal = msg.get("goal")
                    step_by_step = msg.get("step_by_step", False)
                    # Use create_task to let the loop run independently of the listener
                    asyncio.create_task(orchestrator.start(goal, step_by_step))
                
                # Handle Interactions
                else:
                    await orchestrator.process_message(raw_msg)
                    
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        # We only shutdown the orchestrator loop, NOT the browser.
        # The browser stays alive for the next connection (faster).
        await orchestrator.shutdown()

# Cleanup on Server Shutdown 
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down global browser...")
    await global_browser_service.stop()

if __name__ == "__main__":
    # Reload=False essential for Windows Proactor Loop
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) 
