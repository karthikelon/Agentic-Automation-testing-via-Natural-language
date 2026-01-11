from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import os
import sys
import json
from dotenv import load_dotenv
from browser_service import BrowserService
from agent_core import AgentCore

# Fix for Playwright on Windows with asyncio (Python 3.8+)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load environment variables from the same directory as this file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="NL Automation Tool")

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Backend is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected via WebSocket")
    
    # Initialize services for this persistent session
    browser_service = BrowserService()
    agent_core = AgentCore()
    
    # NEW: Async message receiver to handle concurrent 'stop' signals
    msg_queue = asyncio.Queue()
    async def receiver():
        try:
            while True:
                raw_msg = await websocket.receive_text()
                await msg_queue.put(raw_msg)
        except Exception as e:
            print(f"Receiver Task Ended: {e}")

    receiver_task = asyncio.create_task(receiver())

    try:
        await browser_service.start()
        await websocket.send_json({"type": "log", "message": "Neural Link Established. Browser Ready."})
        
        # OUTER SESSION LOOP: Keep connection open for multiple flows
        session_active = True
        while session_active:
            # Wait for a NEW Goal
            print("Orchestration: Waiting for new goal...")
            init_data = await msg_queue.get()
            
            history = [] # Reset history for each new goal
            try:
                msg_json = json.loads(init_data)
                # Ignore random 'stop' or 'next_step' messages if they arrive while idle
                if msg_json.get("type") in ["stop", "next_step"]:
                    continue
                
                goal = msg_json.get("goal")
                step_by_step = msg_json.get("step_by_step", False)
            except:
                goal = init_data
                step_by_step = False

            if not goal: continue

            await websocket.send_json({"type": "log", "message": f"Orchestrating goal: {goal}"})

            # INNER ACTION LOOP (Sense-Think-Act)
            active = True
            while active:
                # Check for STOP signal
                while not msg_queue.empty():
                    try:
                        msg = msg_queue.get_nowait()
                        data = json.loads(msg)
                        if data.get("type") == "stop":
                            await websocket.send_json({"type": "log", "message": "Execution Interrupted."})
                            active = False
                            break
                    except:
                        pass
                if not active: break

                # PHASE 1: SENSE
                screenshot_b64 = await browser_service.get_screenshot_base64()
                ax_tree = await browser_service.get_accessibility_snapshot()
                events = browser_service.get_and_clear_events()
                
                await websocket.send_json({
                    "type": "state", 
                    "screenshot": screenshot_b64,
                    "url": browser_service.page.url if browser_service.page else "Unknown",
                    "events": events
                })

                if not msg_queue.empty(): continue

                # PHASE 2: THINK
                await websocket.send_json({"type": "log", "message": "Thinking..."})
                use_pro = (len(history) == 0 or (history and history[-1].get("action", {}).get("type") == "fail"))
                
                try:
                    full_decision = await agent_core.analyze_state_and_decide(
                        screenshot_b64, goal, history, ax_tree=ax_tree, events=events, use_pro=use_pro
                    )
                    
                    if full_decision.get("plan"):
                        await websocket.send_json({"type": "log", "message": f"Plan: {full_decision['plan']}"})
                    
                    decision = full_decision.get("action", {})
                    thought = full_decision.get("thought", decision.get("description", "Moving forward..."))

                    await websocket.send_json({
                        "type": "thought", 
                        "thought": f"[{'Gemini Pro' if use_pro else 'Gemini Flash'}] {thought}"
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"AI Error: {str(e)}"})
                    break

                # PHASE 3: ACT
                action_type = decision.get("type")
                if action_type == "finish":
                    await websocket.send_json({"type": "success", "message": "Goal Achieved!"})
                    active = False
                elif action_type == "fail":
                    await websocket.send_json({"type": "error", "message": f"Agent stopped: {decision.get('reason')}"})
                    active = False
                else:
                    desc = decision.get("description", f"Executing {action_type}")
                    await websocket.send_json({"type": "log", "message": f"Executing: {desc}"})
                    try:
                        val = decision.get("value") or decision.get("url") or decision.get("key")
                        node_id = decision.get("nodeId")
                        await browser_service.execute_action(action_type, decision.get("selector"), val, node_id=node_id)
                        
                        history.append(full_decision)
                        
                        # Post-action update
                        screenshot_b64 = await browser_service.get_screenshot_base64()
                        await websocket.send_json({
                            "type": "state", "screenshot": screenshot_b64,
                            "url": browser_service.page.url if browser_service.page else "Unknown",
                            "events": browser_service.get_and_clear_events()
                        })
                        
                        if step_by_step:
                            await websocket.send_json({"type": "pause", "message": "Step-by-Step Approval Needed."})
                            paused = True
                            while paused:
                                msg = await msg_queue.get()
                                try:
                                    msg_json = json.loads(msg)
                                    if msg_json.get("type") == "next_step":
                                        paused = False
                                    elif msg_json.get("type") == "stop":
                                        active = False
                                        paused = False
                                except:
                                    pass
                    except Exception as e:
                        print(f"Execution Error: {e}")
                        await websocket.send_json({"type": "error", "message": f"Action Failed: {str(e)}"})
                        # Error recovery logic (same as before)
                        error_step = {
                            "plan": full_decision.get("plan"),
                            "thought": "Execution failed. Retrying with different strategy.",
                            "action": {"type": "fail_retry", "error": str(e)}
                        }
                        history.append(error_step)
                        await asyncio.sleep(1)
                        continue
                        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Server Error: {e}")
    finally:
        if 'receiver_task' in locals() and receiver_task:
            receiver_task.cancel()
        await browser_service.stop()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
