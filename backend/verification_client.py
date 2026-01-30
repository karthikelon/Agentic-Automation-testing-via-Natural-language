import asyncio
import websockets
import json

async def verify_stop_and_report():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        print(" Connected to Server.")
        
        # 1. Start a long-running task
        goal = "Navigate to google.com and wait for 10 seconds"
        await websocket.send(json.dumps({"goal": goal, "step_by_step": False}))
        print(f" Sent Goal: {goal}")
        
        report_url_received = False
        stopped_received = False
        
        # 2. Wait a bit for it to start 'Thinking' or 'Acting'
        # We want to catch it in the middle of operation
        await asyncio.sleep(4) 
        
        # 3. Send STOP
        print(" Sending STOP signal...")
        await websocket.send(json.dumps({"type": "stop"}))
        
        # 4. Listen for results
        try:
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "report":
                        print(f" SUCCESS: Received Report URL: {data.get('url')}")
                        report_url_received = True
                    
                    if data.get("type") == "log" and "Interrupted" in data.get("message", ""):
                         print(f" SUCCESS: Received Stop Confirmation: {data.get('message')}")
                         stopped_received = True
                         
                    if report_url_received and stopped_received:
                        print(" VERIFICATION PASSED: Both Report and Stop confirmed.")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    print(" Connection Closed by Server.")
                    break
                    
        except asyncio.TimeoutError:
            print(" FAILED: Timed out waiting for Report/Stop confirmation.")
            
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(verify_stop_and_report())
